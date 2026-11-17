"""Keyboard metrics on held-out text: what a phone keyboard would actually do.

    python scripts/keyboard_eval.py TRAIN_FILES... --test ud_test.txt --russian russian.txt

Reports, for normal typing (і as и) and chat typing (і as ы):
  * top-1 / top-3: is the right spelling first / in the 3-word suggestion bar?
  * auto-correct on space at several confidence thresholds:
      precision  = of the words it replaced, how many it replaced correctly
      coverage   = of the words needing a fix, how many it fixed by itself
  * keystroke savings from word completion (standard keyboard metric):
      share of letters you don't type because the right word appeared in the bar.
"""

import argparse
from pathlib import Path

from qazfix import _TOKEN
from qazfix.cli import _read_counts
from qazfix.evaluate import strip_chat
from qazfix.keyboard import Predictor
from qazfix.letters import AMBIGUOUS, is_cyrillic_word, strip
from qazfix.model import Model

THRESHOLDS = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]


def test_words(lines):
    for line in lines:
        for tok in _TOKEN.findall(line):
            if is_cyrillic_word(tok):
                yield tok.lower()


def correction_metrics(pred: Predictor, words, stripper):
    rows = []
    for gold in words:
        typed = stripper(gold)
        if typed == gold and not any(c in AMBIGUOUS for c in typed):
            continue
        rows.append((typed, gold, pred.candidates(typed, n=3)))
    n = len(rows)
    top1 = sum(c[0].word == g for _, g, c in rows) / n
    top3 = sum(any(s.word == g for s in c) for _, g, c in rows) / n
    needed = sum(t != g for t, g, _ in rows)
    auto = []
    for th in THRESHOLDS:
        replaced = [(t, g, c[0].word) for t, g, c in rows if c[0].word != t and c[0].score >= th]
        right = sum(w == g for _, g, w in replaced)
        auto.append((th, right / max(len(replaced), 1), right / max(needed, 1), len(replaced) - right))
    return n, top1, top3, auto


def keystroke_savings(pred: Predictor, words, stripper):
    typed_chars = saved = 0
    for gold in words:
        typed = stripper(gold)
        typed_chars += len(typed)
        for k in range(2, len(typed)):
            if any(s.word == gold for s in pred.complete(typed[:k], n=3)):
                saved += len(typed) - k - 1  # minus 1 for tapping the suggestion
                break
    return saved / typed_chars


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("train", nargs="+")
    ap.add_argument("--test", required=True)
    ap.add_argument("--russian")
    a = ap.parse_args()
    russian = Path(a.russian).read_text(encoding="utf-8").split() if a.russian else []
    pred = Predictor(Model.train(_read_counts(a.train), russian))
    words = list(test_words(Path(a.test).read_text(encoding="utf-8").splitlines()))

    for label, stripper in [("normal typing (і as и)", strip), ("chat typing (і as ы)", strip_chat)]:
        n, top1, top3, auto = correction_metrics(pred, words, stripper)
        print(f"\n## {label}: {n} words with letters to decide")
        print(f"top-1 {100 * top1:.1f}%   top-3 {100 * top3:.1f}%")
        print("| auto-correct threshold | precision | coverage | wrong replacements |")
        print("|---:|---:|---:|---:|")
        for th, prec, cov, wrong in auto:
            print(f"| {th:.2f} | {100 * prec:.1f}% | {100 * cov:.1f}% | {wrong} |")
        print(f"keystroke savings from completion: {100 * keystroke_savings(pred, words, stripper):.1f}%")


if __name__ == "__main__":
    main()
