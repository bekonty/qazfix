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
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .letters import AMBIGUOUS, OPTIONS, harmony, strip

MAX_WINDOW = 4
FORMAT_VERSION = 1


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

    # ---------- training ----------
    @classmethod
    def train(
        cls,
        word_counts: Counter,
        russian: Iterable[str] = (),
        meta: dict | None = None,
        use_harmony: bool = False,
    ) -> Model:
        words: dict[str, Counter] = defaultdict(Counter)
        chars: dict[str, Counter] = defaultdict(Counter)
        for word, count in word_counts.items():
            w = word.lower()
            s = strip(w)
            words[s][w] += count
            harm = harmony(s) if use_harmony else None
            for i, ch in enumerate(s):
                if ch in AMBIGUOUS:
                    # Count word types, not tokens: generalises better to unseen words.
                    for key in _contexts(s, i, harm):
                        chars[key][w[i]] += 1
        kazakh_known = set(words)
        return cls(
            words={k: dict(v) for k, v in words.items()},
            chars={k: dict(v) for k, v in chars.items() if sum(v.values()) >= 2},
            russian={r for r in (x.lower() for x in russian) if strip(r) == r and r not in kazakh_known},
            meta={**(meta or {}), "harmony": use_harmony},
        )

    # ---------- inference ----------
    def restore_word(self, lower_word: str) -> str:
        """Restore one lowercase word. Letters already special are kept as typed."""
        s = strip(lower_word)
        if not any(c in AMBIGUOUS for c in s):
            return lower_word
        if s in self.words:
            best = max(self.words[s].items(), key=lambda kv: kv[1])[0]
            return _keep_typed_specials(lower_word, best)
        if lower_word in self.russian:
            return lower_word
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
        return _keep_typed_specials(lower_word, "".join(out))

    # ---------- persistence ----------
    def save(self, path: Path | str) -> None:
        data = {
            "format": FORMAT_VERSION,
            "meta": self.meta,
            "words": self.words,
            "chars": self.chars,
            "russian": sorted(self.russian),
        }
        with gzip.open(path, "wt", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def load(cls, path: Path | str) -> Model:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("format") != FORMAT_VERSION:
            raise ValueError(f"unsupported model format {data.get('format')!r}")
        return cls(data["words"], data["chars"], set(data["russian"]), data.get("meta", {}))


def _keep_typed_specials(typed: str, restored: str) -> str:
    """If the user already typed қ somewhere, trust it over the model."""
    return "".join(t if strip(t) != t else r for t, r in zip(typed, restored))
