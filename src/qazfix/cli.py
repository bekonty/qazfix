"""Command line: `qazfix "казак тили"`, `qazfix build`, `qazfix eval`."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from . import load_model, restore
from .model import Model


def _read_counts(paths: list[str]) -> Counter:
    """Accept plain text, or 'word count' frequency lists (auto-detected per line)."""
    from . import _TOKEN

    counts: Counter = Counter()
    for p in paths:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1].isdigit():
                counts[parts[0].lower()] += int(parts[1])
            else:
                counts.update(t.lower() for t in _TOKEN.findall(line))
    return counts


def cmd_fix(args: argparse.Namespace) -> int:
    model = load_model(args.model)
    text = sys.stdin.read() if args.text in (None, "-") else args.text
    sys.stdout.write(restore(text, model) + ("" if text.endswith("\n") else "\n"))
    return 0


def cmd_suggest(args: argparse.Namespace) -> int:
    from .keyboard import Predictor

    pred = Predictor(load_model(args.model))
    for word in args.words:
        bar = "  |  ".join(f"{s.word} {100 * s.score:.0f}%" for s in pred.candidates(word, n=args.n))
        auto = pred.should_autocorrect(word)
        print(f"{word}:  {bar}" + (f"   (auto-correct → {auto})" if auto else ""))
    return 0


def cmd_complete(args: argparse.Namespace) -> int:
    from .keyboard import Predictor

    pred = Predictor(load_model(args.model))
    print("  |  ".join(s.word for s in pred.complete(args.prefix, n=args.n)) or "(no completions)")
    return 0


def cmd_export_web(args: argparse.Namespace) -> int:
    import json

    m = load_model(args.model)
    data = {
        "format": 1,
        "meta": m.meta,
        "words": m.words,
        "chars": m.chars,
        "russian": sorted(m.russian),
        "suffixes": sorted(m.suffixes),
    }
    Path(args.output).write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {args.output} ({Path(args.output).stat().st_size // 1024} KB)")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    counts = _read_counts(args.corpus)
    russian = []
    if args.russian:
        russian = [w for w in Path(args.russian).read_text(encoding="utf-8").split()]
    lexicon = Path(args.lexicon).read_text(encoding="utf-8").split() if args.lexicon else []
    stems = Path(args.stems).read_text(encoding="utf-8").split() if args.stems else None
    suffixes = Path(args.suffixes).read_text(encoding="utf-8").split() if args.suffixes else []
    sources = [Path(p).name for p in args.corpus] + [Path(p).name for p in (args.lexicon, args.stems) if p]
    model = Model.train(
        counts, russian, meta={"sources": sources}, use_harmony=args.harmony,
        lexicon=lexicon, lexicon_in_table=stems, suffixes=suffixes,
    )
    dropped = model.prune(args.prune) if args.prune else 0
    model.save(args.output)
    print(f"built {args.output}: {len(model.words)} word forms, {len(model.chars)} contexts "
          f"({dropped} pruned), {len(model.russian)} Russian guard words")
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    from .evaluate import evaluate, format_report

    model = load_model(args.model)
    lines = Path(args.testfile).read_text(encoding="utf-8").splitlines()
    print(format_report(evaluate(lines, model)))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in ("build", "eval", "fix", "suggest", "complete", "export-web", "-h", "--help"):
        argv.insert(0, "fix")  # `qazfix "text"` is shorthand for `qazfix fix "text"`
    if not argv:
        argv = ["fix", "-"]
    parser = argparse.ArgumentParser(prog="qazfix", description="Restore Kazakh letters in text typed without them.")
    sub = parser.add_subparsers(dest="command", required=True)

    f = sub.add_parser("fix", help="restore text (default command)")
    f.add_argument("text", nargs="?", help="text to fix, or - to read stdin")
    f.add_argument("--model", help="model file (default: bundled)")
    f.set_defaults(func=cmd_fix)

    sg = sub.add_parser("suggest", help="show the keyboard suggestion bar for typed words")
    sg.add_argument("words", nargs="+")
    sg.add_argument("-n", type=int, default=3)
    sg.add_argument("--model")
    sg.set_defaults(func=cmd_suggest)

    c = sub.add_parser("complete", help="complete a partly typed word")
    c.add_argument("prefix")
    c.add_argument("-n", type=int, default=3)
    c.add_argument("--model")
    c.set_defaults(func=cmd_complete)

    x = sub.add_parser("export-web", help="write the model as plain JSON for qazfix.js")
    x.add_argument("output")
    x.add_argument("--model")
    x.set_defaults(func=cmd_export_web)

    b = sub.add_parser("build", help="train a model from Kazakh text or word-frequency files")
    b.add_argument("corpus", nargs="+")
    b.add_argument("-o", "--output", required=True)
    b.add_argument("--russian", help="file of Russian words to leave untouched")
    b.add_argument("--harmony", action="store_true", help="use vowel-harmony context (experimental)")
    b.add_argument("--lexicon", help="dictionary word list (scripts/build_lexicon.py): valid spellings")
    b.add_argument("--stems", help="subset of the lexicon to put in the word table (keeps the model small)")
    b.add_argument("--suffixes", help="word endings (scripts/build_lexicon.py), for dropped-vowel shorthand")
    b.add_argument("--prune", type=float, default=0.99, help="drop redundant contexts (0 to keep all)")
    b.set_defaults(func=cmd_build)

    e = sub.add_parser("eval", help="strip correct Kazakh text, restore it, report accuracy")
    e.add_argument("testfile", help="correctly written Kazakh text, one sentence per line")
    e.add_argument("--model")
    e.set_defaults(func=cmd_eval)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
