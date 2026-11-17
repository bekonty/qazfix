"""Compare qazfix with simpler baselines and ablations on a held-out test file.

    python scripts/compare.py TRAIN_FILES... --test ud_test.txt --russian russian.txt
"""

import argparse
from pathlib import Path

from qazfix.cli import _read_counts
from qazfix.evaluate import evaluate, strip_chat
from qazfix.model import Model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("train", nargs="+")
    ap.add_argument("--test", required=True)
    ap.add_argument("--russian")
    a = ap.parse_args()
    counts = _read_counts(a.train)
    russian = Path(a.russian).read_text(encoding="utf-8").split() if a.russian else []
    lines = Path(a.test).read_text(encoding="utf-8").splitlines()

    full = Model.train(counts, russian)
    dict_only = Model(words=full.words, chars={}, russian=full.russian)
    no_guard = Model.train(counts, [])
    with_harmony = Model.train(counts, russian, use_harmony=True)

    rows = [
        ("do nothing (leave text as typed)", evaluate(lines, None, restore_fn=lambda w: w)),
        ("dictionary only (unseen words unchanged)", evaluate(lines, dict_only)),
        ("dictionary + character context", evaluate(lines, no_guard)),
        ("+ Russian-word guard  = qazfix default", evaluate(lines, full)),
        ("+ vowel harmony (experimental --harmony)", evaluate(lines, with_harmony)),
    ]
    print(f"| {'method':44} | accuracy | Kazakh letters restored | correct words kept |")
    print(f"|{'-' * 46}|---------:|------------------------:|-------------------:|")
    for name, r in rows:
        print(f"| {name:44} | {100 * r.accuracy:7.1f}% | {100 * r.special_fixed / r.had_special:22.1f}% "
              f"| {100 * r.plain_kept / r.plain:17.1f}% |")
    print(f"\n{rows[0][1].words} test words containing an ambiguous letter")

    print("\nSame test text, typed the chat way (і as ы, e.g. 'быз' for біз):")
    for name, m in [("dictionary + character context", no_guard), ("qazfix default", full)]:
        r = evaluate(lines, m, stripper=strip_chat)
        print(f"  {name:32} {100 * r.accuracy:5.1f}%  ({r.words} words)")


if __name__ == "__main__":
    main()
