"""Score qazfix on REAL typed text against your hand-corrected version.

1. typed.txt  - messages exactly as people typed them, one per line
2. gold.txt   - the same lines, corrected by a native speaker. Rules:
                  * fix only missing Kazakh letters (е.g. казак -> қазақ);
                  * keep every word in place: same number of words per line;
                  * leave slang, Russian words and shorthand as typed.
3. python scripts/pair_eval.py typed.txt gold.txt

Prints word accuracy and lists every mistake. Keep both files out of git:
chat messages are private.
"""

import sys
from collections import Counter
from pathlib import Path

import qazfix
from qazfix import _TOKEN


def main(typed_path: str, gold_path: str) -> None:
    typed = Path(typed_path).read_text(encoding="utf-8").splitlines()
    gold = Path(gold_path).read_text(encoding="utf-8").splitlines()
    if len(typed) != len(gold):
        sys.exit(f"line counts differ: {len(typed)} typed vs {len(gold)} gold")

    total = correct = needed = fixed = harmed = 0
    mistakes = Counter()
    for n, (t, g) in enumerate(zip(typed, gold), start=1):
        out_words = _TOKEN.findall(qazfix.restore(t))
        typed_words, gold_words = _TOKEN.findall(t), _TOKEN.findall(g)
        if not (len(typed_words) == len(gold_words) == len(out_words)):
            print(f"skipping line {n}: word counts differ")
            continue
        for tw, gw, ow in zip(typed_words, gold_words, out_words):
            if tw == gw == ow:
                continue  # nothing to do and nothing done: not counted
            total += 1
            correct += ow == gw
            if tw != gw:
                needed += 1
                fixed += ow == gw
            elif ow != gw:
                harmed += 1
            if ow != gw:
                mistakes[f"{tw} -> {ow}  (should be {gw})"] += 1

    print(f"words that needed or got a change: {total}")
    print(f"word accuracy:                     {100 * correct / max(total, 1):.1f}%")
    print(f"needed Kazakh letters, restored:   {fixed}/{needed}")
    print(f"correct words wrongly changed:     {harmed}")
    print("\nmistakes:")
    for m, c in mistakes.most_common():
        print(f"  {c}x  {m}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
