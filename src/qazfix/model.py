"""Restoration model: a word table, a character-context model, and a Russian guard.

How a word is restored (see SPEC.md):

1. Seen word: its stripped form is in the word table -> most frequent spelling.
2. Russian word: not Kazakh-known but in the Russian list -> left unchanged.
3. Unseen word: each ambiguous letter is decided from the letters around it
   (and the word's vowel harmony), backing off to smaller windows.

Kazakh is agglutinative (қазақстандықтарымызға...), so step 3 is what handles
the endless inflected forms no dictionary contains.
"""

from __future__ import annotations

import gzip
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from itertools import combinations, product
from pathlib import Path

from .letters import AMBIGUOUS, OPTIONS, SPECIAL, harmony, strip

MAX_WINDOW = 4
MAX_Y_SWAPS = 4
MAX_SHORTHAND_SLOTS = 6
MIN_STEM = 3  # stem + ending checks: shorter stems match too much noise ("че" + "тім")
Y_OVERRIDE = 10  # ы→і beats an exact table hit only when this many times more frequent
VOWELS = frozenset("аеиоуыэюяё")
BACK_VOWELS = frozenset("аоұы")
FRONT_VOWELS = frozenset("әеөүі")

# Found by testing on real chat messages (see README):
# laughter like "хахаха" was turned into "хаһаһа", and chat words like "ок"
# into the real but wrong word "оқ" (bullet).
LAUGHTER = re.compile(r"^(?:х[аеоы]|[аеоы]х)+х?$")
CHAT_WORDS = frozenset({"ок", "окок", "ия"})
FORMAT_VERSION = 1


def _russian_ok(r: str, words: dict, lex: set) -> bool:
    """Keep a Russian word in the guard unless Kazakh spells the same letters differently.

    "список" appears in Kazakh Wikipedia too, spelled the same: still Russian.
    "кон" is also Kazakh "қон": not protected.
    """
    spellings = words.get(r, {})
    if any(w != r for w in spellings):
        return False
    return r not in lex or not spellings


def _contexts(stripped: str, i: int, harm: str | None):
    """Context keys for position i, most specific first.

    harm is the word's vowel-harmony class, or None to ignore harmony. On the
    starter data harmony made accuracy slightly worse (see README), so it is off
    by default; re-test it with a bigger corpus via `--harmony`.
    """
    p = "^" + stripped + "$"
    j = i + 1
    c = stripped[i]
    for k in range(MAX_WINDOW, -1, -1):
        left, right = p[max(0, j - k) : j], p[j + 1 : j + 1 + k]
        if harm is not None:
            yield f"{harm}|{k}|{left}|{c}|{right}"
        yield f"*|{k}|{left}|{c}|{right}"


@dataclass
class Model:
    words: dict[str, dict[str, int]] = field(default_factory=dict)  # stripped -> {spelling: count}
    chars: dict[str, dict[str, int]] = field(default_factory=dict)  # context -> {letter: count}
    russian: set[str] = field(default_factory=set)
    meta: dict = field(default_factory=dict)
    suffixes: set[str] = field(default_factory=set)  # stripped endings, for dropped-vowel shorthand

    # ---------- training ----------
    @classmethod
    def train(
        cls,
        word_counts: Counter,
        russian: Iterable[str] = (),
        meta: dict | None = None,
        use_harmony: bool = False,
        lexicon: Iterable[str] = (),
        lexicon_in_table: Iterable[str] | None = None,
        min_context: int = 2,
        suffixes: Iterable[str] = (),
        min_table_count: int = 1,
    ) -> Model:
        """Train from corpus word counts plus an optional dictionary word list.

        lexicon: valid spellings (e.g. hunspell + Apertium). They teach the
            character model, and where a stripped key has dictionary spellings,
            only those are kept (so noisy corpus spellings like "кәзір" lose to
            "қазір").
        lexicon_in_table: which dictionary words get their own word-table entry
            (default: all of `lexicon`). Passing just the stems keeps the model small;
            the character model still knows every inflected form.
        min_table_count: corpus words seen fewer times stay out of the word table
            (they still teach the character model). Keeps a Wikipedia-sized model small.
        """
        words: dict[str, Counter] = defaultdict(Counter)
        chars: dict[str, Counter] = defaultdict(Counter)
        lex = {w.lower() for w in lexicon}
        in_table = lex if lexicon_in_table is None else {w.lower() for w in lexicon_in_table}

        types = set()
        for word, count in word_counts.items():
            w = word.lower()
            types.add(w)
            if count >= min_table_count:  # rarer words still teach the character model
                words[strip(w)][w] += count
        types |= lex

        # Dictionary words fill gaps, they don't dilute corpus frequencies:
        #  * key unknown to the corpus     -> add the dictionary spellings (count 1)
        #  * corpus has a valid spelling   -> keep only the valid ones (кәзір loses to қазір)
        #  * corpus has only invalid ones  -> replace them with the dictionary spellings
        lex_by_key: dict[str, set[str]] = defaultdict(set)
        for w in in_table:
            lex_by_key[strip(w)].add(w)
        for key, spellings in lex_by_key.items():
            if key not in words:
                words[key] = Counter(dict.fromkeys(sorted(spellings), 1))

        for w in types:
            s = strip(w)
            harm = harmony(s) if use_harmony else None
            for i, ch in enumerate(s):
                if ch in AMBIGUOUS:
                    # Count word types, not tokens: generalises better to unseen words.
                    for key in _contexts(s, i, harm):
                        chars[key][w[i]] += 1

        if lex:
            for key, spellings in words.items():
                valid = {w: c for w, c in spellings.items() if w in lex}
                if valid and len(valid) < len(spellings):
                    words[key] = Counter(valid)
                elif not valid and key in lex_by_key:
                    words[key] = Counter(dict.fromkeys(sorted(lex_by_key[key]), 1))
        return cls(
            words={k: dict(v) for k, v in words.items()},
            chars={k: dict(v) for k, v in chars.items() if sum(v.values()) >= min_context},
            russian={r for r in (x.lower() for x in russian) if strip(r) == r and _russian_ok(r, words, lex)},
            meta={**(meta or {}), "harmony": use_harmony},
            suffixes={strip(x.lower()) for x in suffixes if x},
        )

    # ---------- size ----------
    def prune(self, min_share: float = 0.99) -> int:
        """Drop character contexts that add nothing over the shorter context the
        model would fall back to (same best letter, chosen at least `min_share`
        of the time). Returns how many were dropped.

        Measured on the held-out test: 550k -> 39k contexts at 0.99, with no change
        in accuracy (see README).
        """
        def parent(key: str) -> str | None:
            h, k, left, c, right = key.split("|")
            k = int(k)
            if k == 0:
                return None
            return f"{h}|{k - 1}|{left[1:] if len(left) >= k else left}|{c}|{right[:-1] if len(right) >= k else right}"

        def best(d: dict[str, int]) -> str:
            return max(d.items(), key=lambda kv: kv[1])[0]

        kept: dict[str, dict[str, int]] = {}
        for key in sorted(self.chars, key=lambda x: int(x.split("|")[1])):  # short windows first
            d = self.chars[key]
            anc = parent(key)
            while anc is not None and anc not in kept:
                anc = parent(anc)
            if anc is not None and best(kept[anc]) == best(d) and max(d.values()) / sum(d.values()) >= min_share:
                continue
            kept[key] = d
        dropped = len(self.chars) - len(kept)
        self.chars = kept
        return dropped

    # ---------- inference ----------
    def restore_word(self, lower_word: str) -> str:
        """Restore one lowercase word."""
        if any(c in SPECIAL for c in lower_word):
            return lower_word  # already typed with Kazakh letters: trust the writer
        s = lower_word
        if s in CHAT_WORDS or LAUGHTER.match(s):
            return s
        if s in self.words:
            swapped = self._y_as_i(s)
            if swapped and self._y_count(swapped) >= Y_OVERRIDE * self._count(s):
                return swapped  # "казыр" (20, noise) vs "қазір" (4071): the typist meant і
            return self._best(s)
        swapped = None if self._keeps_y(s) else self._y_as_i(s)
        if swapped:
            return swapped
        if s in self.russian:
            return s
        russian_stem = self._russian_stem(s)
        if russian_stem:  # списокта = список + та: keep the Russian part as typed
            return s[:russian_stem] + self._char_restore(s)[russian_stem:]
        expanded = self.expand_shorthand(s)  # before the next check: "бз" has no ambiguous letter
        if expanded:
            return self.restore_word(expanded)
        if not any(c in AMBIGUOUS for c in s):
            return s
        return self._char_restore(s)

    def _char_restore(self, s: str) -> str:
        harm = harmony(s) if self.meta.get("harmony") else None
        out = list(s)
        for i, ch in enumerate(s):
            if ch not in AMBIGUOUS:
                continue
            for key in _contexts(s, i, harm):
                counts = self.chars.get(key)
                if counts:
                    out[i] = max(OPTIONS[ch], key=lambda o: counts.get(o, 0))
                    break
        return "".join(out)

    # ---------- dropped-vowel shorthand: баур -> бауыр, бугн -> бүгін ----------
    def _is_valid(self, s: str) -> bool:
        """A known word, or a known stem + a known ending (тілдерін = тіл + дерін)."""
        if s in self.words:
            return True
        for k in range(MIN_STEM, len(s)):
            stem, end = s[:k], s[k:]
            if stem in self.words and end in self.suffixes:
                # a one-letter consonant ending (-м, -н, -ң: possessive) only follows a vowel: бала-м
                if len(end) == 1 and end not in VOWELS and stem[-1] not in VOWELS:
                    continue
                return True
        return False

    def _is_inflected(self, s: str) -> bool:
        """A known stem (3+ letters) + a known ending (2+ letters): қырғыз + ды.

        Such a word is real as typed, so the ы→і guess is not applied to it.
        """
        return any(
            s[:k] in self.words and s[k:] in self.suffixes for k in range(3, len(s) - 1)
        )

    def _keeps_y(self, s: str) -> bool:
        """True when ы is probably meant: a real stem + ending (қырғыз + ды) and no
        front vowel е in the word (ы and е don't mix: мектептын must be мектептің)."""
        return "ы" in s and not any(c in "еэ" for c in s) and self._is_inflected(s)

    def _russian_stem(self, s: str) -> int:
        """Length of a Russian word that `s` starts with before a Kazakh ending, else 0.

        списокта = список + та, этажга = этаж + га. Only the ending is restored.
        """
        for k in range(len(s) - 1, 3, -1):
            stem = s[:k]
            if stem in self.russian and s[k:] in self.suffixes and self._best_or_self(stem) == stem:
                return k
        return 0

    def shorthand_options(self, s: str) -> list[tuple[str, int]]:
        """Spellings with one or two dropped ы/і put back, as (stripped word, score).

        Score: word-table count for whole known words; 0 for stem+ending matches.
        Empty when the word already looks real or nothing fits.
        """
        if len(s) < 2 or self._is_valid(s):
            return []
        slots = [
            i for i in range(1, len(s))
            if s[i] not in VOWELS and (s[i - 1] not in VOWELS or (s[i - 1] in "уй" and i >= 2 and s[i - 2] in VOWELS))
        ][-MAX_SHORTHAND_SLOTS:]  # vowels drop near the end of a word: check the last slots
        for n in (1, 2):  # prefer the fewest added vowels
            found: dict[str, int] = {}
            for spots in combinations(slots, n):
                for vowels in product("ыи", repeat=n):
                    chars = list(s)
                    for pos, v in sorted(zip(spots, vowels), reverse=True):
                        chars.insert(pos, v)
                    cand = "".join(chars)
                    if cand in self.words:
                        found[cand] = sum(self.words[cand].values())
                    elif self._is_valid(cand):
                        found.setdefault(cand, 0)
            if found:
                # Same evidence? Prefer the vowel that fits the word's harmony:
                # ы in back-vowel words (қолдаймын), і in front-vowel words (бүгін).
                return sorted(found.items(), key=lambda kv: (-kv[1], self._disharmony(kv[0]), kv[0]))
        return []

    def _disharmony(self, stripped: str) -> int:
        """1 if the restored word mixes back (а о ұ ы) and front (ә е ө ү і) vowels."""
        w = self._best(stripped) if stripped in self.words else self._char_restore(stripped)
        return int(any(c in BACK_VOWELS for c in w) and any(c in FRONT_VOWELS for c in w))

    def expand_shorthand(self, s: str) -> str | None:
        options = self.shorthand_options(s)
        return options[0][0] if options else None

    def _best_or_self(self, key: str) -> str:
        return self._best(key) if key in self.words else key

    def _count(self, key: str) -> int:
        total = 0
        for c in self.words.get(key, {}).values():
            total += c
        return total

    def _y_count(self, spelling: str) -> int:
        return self.words.get(strip(spelling), {}).get(spelling, 0)

    def _best(self, stripped: str) -> str:
        return max(self.words[stripped].items(), key=lambda kv: kv[1])[0]

    def _y_as_i(self, s: str) -> str | None:
        """Many people type і as ы ("быз" for біз). Try ы→і swaps against the word table.

        Only dictionary hits are accepted, so a real ы is never changed on a guess.
        """
        spots = [i for i, c in enumerate(s) if c == "ы"]
        if not spots or len(spots) > MAX_Y_SWAPS:
            return None
        best, best_count = None, 0
        for r in range(1, len(spots) + 1):
            for chosen in combinations(spots, r):
                cand = "".join("и" if i in chosen else c for i, c in enumerate(s))
                if cand in self.words:
                    spelling = self._best(cand)
                    count = self.words[cand][spelling]
                    if count > best_count:
                        best, best_count = spelling, count
        return best

    # ---------- persistence ----------
    def save(self, path: Path | str) -> None:
        data = {
            "format": FORMAT_VERSION,
            "meta": self.meta,
            "words": self.words,
            "chars": self.chars,
            "russian": sorted(self.russian),
            "suffixes": sorted(self.suffixes),
        }
        with gzip.open(path, "wt", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def load(cls, path: Path | str) -> Model:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("format") != FORMAT_VERSION:
            raise ValueError(f"unsupported model format {data.get('format')!r}")
        return cls(
            data["words"], data["chars"], set(data["russian"]), data.get("meta", {}), set(data.get("suffixes", []))
        )

