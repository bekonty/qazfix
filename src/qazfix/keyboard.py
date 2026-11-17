"""Keyboard features: ranked suggestions, auto-correct confidence, word completion.

    >>> from qazfix.keyboard import Predictor
    >>> p = Predictor()
    >>> p.candidates("казак")          # suggestion bar after a word is typed
    [Suggestion(word='қазақ', score=0.9...), ...]
    >>> p.complete("казакст")          # suggestion bar while typing
    [Suggestion(word='қазақстан', score=...), ...]

A keyboard should auto-replace on space only when `should_autocorrect()` says so;
otherwise it just shows the suggestions. See README "Keyboard mode" for the
measured trade-off.
"""

from __future__ import annotations

import heapq
from bisect import bisect_left
from dataclasses import dataclass
from itertools import combinations

from .letters import AMBIGUOUS, OPTIONS, SPECIAL, harmony, strip
from .model import CHAT_WORDS, LAUGHTER, MAX_Y_SWAPS, Model, _contexts

SMOOTHING = 0.5  # add-α smoothing for character-context probabilities
TYPED_PRIOR = 0.6  # when no context was ever seen, assume the typed letter is right
BEAM = 12
AUTOCORRECT_THRESHOLD = 0.8  # chosen from the measurements in README
DICT_WEIGHT = 0.9  # trust in the word table for a known word
Y_WEIGHT = 0.6  # trust in an ы→і word-table match (a guess about the typist's habit)


@dataclass(frozen=True)
class Suggestion:
    word: str
    score: float  # 0..1; scores of one call's suggestions sum to at most 1


class Predictor:
    def __init__(self, model: Model | None = None):
        if model is None:
            from . import load_model

            model = load_model()
        self.model = model
        self._keys = sorted(model.words)
        self._harmony = bool(model.meta.get("harmony"))

    # ------------------------------------------------------------ corrections
    def candidates(self, typed: str, n: int = 3) -> list[Suggestion]:
        """Ranked spellings for a typed word. The first one is what `restore()` picks."""
        s = typed.lower()
        if any(c in SPECIAL for c in s) or s in CHAT_WORDS or LAUGHTER.match(s):
            return [Suggestion(typed, 1.0)]
        if not any(c in AMBIGUOUS or c == "ы" for c in s):
            return [Suggestion(typed, 1.0)]

        char_p = self._char_distribution(s)
        dict_p = self._share(s)
        y_p = self._y_share(s) if not dict_p else {}
        if dict_p:
            scores = _mix(dict_p, DICT_WEIGHT, char_p)
        elif y_p:
            scores = _mix(y_p, Y_WEIGHT, char_p)
        elif s in self.model.russian:
            scores = _mix({s: 1.0}, 0.7, char_p)
        else:
            scores = char_p

        ranked = sorted(scores.items(), key=lambda kv: -kv[1])
        top = self.model.restore_word(s)
        if ranked and ranked[0][0] != top:  # keep suggestions consistent with restore()
            top_score = dict(ranked).get(top, 0.0)
            ranked = [(top, ranked[0][1])] + [
                (w, top_score if i == 0 else p) for i, (w, p) in enumerate(ranked) if w != top
            ]
            ranked.sort(key=lambda kv: -kv[1] if kv[0] != top else -2.0)
        return [Suggestion(_match_case(typed, w), round(p, 4)) for w, p in ranked[:n]]

    def should_autocorrect(self, typed: str, threshold: float = AUTOCORRECT_THRESHOLD) -> str | None:
        """The word to replace `typed` with on space, or None to leave it as typed."""
        best = self.candidates(typed, n=1)[0]
        if best.word != typed and best.score >= threshold:
            return best.word
        return None

    # ------------------------------------------------------------ completion
    def complete(self, prefix: str, n: int = 3, scan_limit: int = 200_000) -> list[Suggestion]:
        """Most frequent known words that start with `prefix` (typed with or without Kazakh letters)."""
        p = prefix.lower()
        if len(p) < 2:
            return []
        sp = strip(p)
        fixed = [(i, c) for i, c in enumerate(p) if c in SPECIAL]
        found: list[tuple[int, str]] = []
        total = 0
        i = bisect_left(self._keys, sp)
        scanned = 0
        while i < len(self._keys) and self._keys[i].startswith(sp) and scanned < scan_limit:
            for spelling, count in self.model.words[self._keys[i]].items():
                if all(spelling[j] == c for j, c in fixed):
                    found.append((count, spelling))
                    total += count
            i += 1
            scanned += 1
        best = heapq.nlargest(n, found)
        return [Suggestion(_match_case(prefix, w), round(c / total, 4)) for c, w in best]

    # ------------------------------------------------------------ internals
    def _share(self, key: str) -> dict[str, float]:
        spellings = self.model.words.get(key)
        if not spellings:
            return {}
        total = sum(spellings.values())
        return {w: c / total for w, c in spellings.items()}

    def _y_share(self, s: str) -> dict[str, float]:
        spots = [i for i, c in enumerate(s) if c == "ы"]
        if not spots or len(spots) > MAX_Y_SWAPS:
            return {}
        counts: dict[str, int] = {}
        for r in range(1, len(spots) + 1):
            for chosen in combinations(spots, r):
                key = "".join("и" if i in chosen else c for i, c in enumerate(s))
                for w, c in self.model.words.get(key, {}).items():
                    counts[w] = counts.get(w, 0) + c
        total = sum(counts.values())
        return {w: c / total for w, c in counts.items()} if total else {}

    def _letter_probs(self, s: str, i: int) -> dict[str, float]:
        opts = OPTIONS[s[i]]
        harm = harmony(s) if self._harmony else None
        for key in _contexts(s, i, harm):
            counts = self.model.chars.get(key)
            if counts:
                total = sum(counts.get(o, 0) for o in opts) + SMOOTHING * len(opts)
                return {o: (counts.get(o, 0) + SMOOTHING) / total for o in opts}
        rest = (1 - TYPED_PRIOR) / (len(opts) - 1)
        return {o: TYPED_PRIOR if o == s[i] else rest for o in opts}

    def _char_distribution(self, s: str) -> dict[str, float]:
        """Beam search over the ambiguous letters; letters are scored independently."""
        beam: list[tuple[float, str]] = [(1.0, "")]
        for i, ch in enumerate(s):
            if ch not in AMBIGUOUS:
                beam = [(p, w + ch) for p, w in beam]
                continue
            probs = self._letter_probs(s, i)
            beam = heapq.nlargest(BEAM, ((p * q, w + o) for p, w in beam for o, q in probs.items()))
        # A plain loop on purpose: Python 3.12+ sum() uses compensated float
        # addition, which would make results differ across Python versions and
        # from qazfix.js.
        total = 0.0
        for p, _ in beam:
            total += p
        return {w: p / total for p, w in beam}


def _mix(primary: dict[str, float], weight: float, secondary: dict[str, float]) -> dict[str, float]:
    out = {w: weight * p for w, p in primary.items()}
    for w, p in secondary.items():
        out[w] = out.get(w, 0.0) + (1 - weight) * p
    return out


def _match_case(template: str, word: str) -> str:
    if template.isupper() and len(template) > 1:
        return word.upper()
    if template[:1].isupper():
        return word[:1].upper() + word[1:]
    return word
