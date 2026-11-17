"""Honest evaluation: strip correct text, restore it, compare word by word."""

from __future__ import annotations

from dataclasses import dataclass

from .letters import AMBIGUOUS, is_cyrillic_word, strip
from .model import Model


@dataclass
class Report:
    words: int = 0  # Cyrillic words with at least one ambiguous letter after stripping
    correct: int = 0
    had_special: int = 0  # ...of which originally contained ә ғ қ ң ө ұ ү і һ
    special_fixed: int = 0
    plain: int = 0  # ...of which were correct already (must stay unchanged)
    plain_kept: int = 0

    @property
    def accuracy(self) -> float:
        return self.correct / self.words if self.words else 0.0


def strip_chat(text: str) -> str:
    """Strip like a chat user who types і as ы instead of и ("быз" for біз)."""
    return strip(text.replace("і", "ы").replace("І", "Ы"))


def evaluate(lines, model: Model | None, restore_fn=None, stripper=strip) -> Report:
    """`restore_fn(lower_word) -> lower_word`; defaults to the model's restore_word.

    `stripper` simulates how people type: `strip` (і→и) or `strip_chat` (і→ы).
    """
    from . import _TOKEN

    fn = restore_fn or model.restore_word
    r = Report()
    for line in lines:
        for tok in _TOKEN.findall(line):
            if not is_cyrillic_word(tok):
                continue
            gold = tok.lower()
            stripped = stripper(gold)
            if stripped == gold and not any(c in AMBIGUOUS for c in stripped):
                continue
            r.words += 1
            ok = fn(stripped) == gold
            r.correct += ok
            if stripped != gold:
                r.had_special += 1
                r.special_fixed += ok
            else:
                r.plain += 1
                r.plain_kept += ok
    return r


def format_report(r: Report) -> str:
    pct = lambda a, b: f"{100 * a / b:5.1f}%" if b else "  n/a"
    return "\n".join([
        f"words checked           {r.words}",
        f"word accuracy           {pct(r.correct, r.words)}",
        f"  needed a Kazakh letter {pct(r.special_fixed, r.had_special)}  ({r.special_fixed}/{r.had_special} restored)",
        f"  were already correct   {pct(r.plain_kept, r.plain)}  ({r.plain_kept}/{r.plain} left alone)",
    ])
