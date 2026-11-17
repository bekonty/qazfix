"""Compare qazfix with simpler baselines and ablations on a held-out test file.

    python scripts/compare.py TRAIN_FILES... --test ud_test.txt --russian russian.txt \
        [--lexicon lexicon.txt --stems stems.txt --suffixes suffixes.txt]
"""

import argparse
import re
from pathlib import Path

from qazfix import _TOKEN
from qazfix.cli import _read_counts
from qazfix.evaluate import evaluate, strip_chat
from qazfix.letters import is_cyrillic_word, strip
from qazfix.model import Model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("train", nargs="+")
    ap.add_argument("--test", required=True)
    ap.add_argument("--russian")
    ap.add_argument("--lexicon")
    ap.add_argument("--stems")
    ap.add_argument("--suffixes")
    ap.add_argument("--wiki", help="extra corpus word counts (e.g. Kazakh Wikipedia) for the last row")
    ap.add_argument("--min-count", type=int, default=20)
    a = ap.parse_args()
    read = lambda f: Path(f).read_text(encoding="utf-8").split() if f else []
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
        ("+ Russian-word guard (corpus only)", evaluate(lines, full)),
        ("+ vowel harmony (experimental --harmony)", evaluate(lines, with_harmony)),
    ]
    models = {"corpus only": full, "corpus only, no Russian guard": no_guard}
    if a.lexicon:
        big = Model.train(counts, russian, lexicon=read(a.lexicon), lexicon_in_table=read(a.stems) or None,
                          suffixes=read(a.suffixes))
        big.prune(0.99)
        rows.append(("+ hunspell & Apertium dictionaries", evaluate(lines, big)))
        models["+ dictionaries"] = big
    if a.wiki:
        wiki_counts = counts + _read_counts([a.wiki])
        top = Model.train(wiki_counts, russian, lexicon=read(a.lexicon), lexicon_in_table=read(a.stems) or None,
                          suffixes=read(a.suffixes), min_table_count=a.min_count)
        top.prune(0.99)
        rows.append(("+ Wikipedia word frequencies = qazfix", evaluate(lines, top)))
        models["qazfix (+ Wikipedia)"] = top
    print(f"| {'method':44} | accuracy | Kazakh letters restored | correct words kept |")
    print(f"|{'-' * 46}|---------:|------------------------:|-------------------:|")
    for name, r in rows:
        print(f"| {name:44} | {100 * r.accuracy:7.1f}% | {100 * r.special_fixed / r.had_special:22.1f}% "
              f"| {100 * r.plain_kept / r.plain:17.1f}% |")
    print(f"\n{rows[0][1].words} test words containing an ambiguous letter")

    print("\nSame test text, typed the chat way (і as ы, e.g. 'быз' for біз):")
    for name, m in models.items():
        r = evaluate(lines, m, stripper=strip_chat)
        print(f"  {name:32} {100 * r.accuracy:5.1f}%  ({r.words} words)")

    # shorthand: the vowel of the last syllable dropped, as in chat (бүгін -> бугн)
    v = "аеиоуыэюяё"
    drop = re.compile(rf"([^{v}]|(?<=[{v}])у)([ыи])([^{v}])$")
    golds = [t.lower() for line in lines for t in _TOKEN.findall(line) if is_cyrillic_word(t)]
    cases = [(drop.sub(r"\1\3", strip(g)), g) for g in golds if drop.search(strip(g))]
    print(f"\nShorthand with a dropped vowel ({len(cases)} words, e.g. бугн for бүгін):")
    for name, m in models.items():
        ok = sum(m.restore_word(t) == g for t, g in cases)
        print(f"  {name:32} {100 * ok / len(cases):5.1f}%")


if __name__ == "__main__":
    main()
