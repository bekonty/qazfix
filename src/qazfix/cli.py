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


def cmd_build(args: argparse.Namespace) -> int:
    counts = _read_counts(args.corpus)
    russian = []
    if args.russian:
        russian = [w for w in Path(args.russian).read_text(encoding="utf-8").split()]
    model = Model.train(
        counts, russian, meta={"sources": [Path(p).name for p in args.corpus]}, use_harmony=args.harmony
    )
    model.save(args.output)
    print(f"built {args.output}: {len(model.words)} word forms, {len(model.chars)} contexts, "
          f"{len(model.russian)} Russian guard words")
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    from .evaluate import evaluate, format_report

    model = load_model(args.model)
    lines = Path(args.testfile).read_text(encoding="utf-8").splitlines()
    print(format_report(evaluate(lines, model)))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in ("build", "eval", "fix", "-h", "--help"):
        argv.insert(0, "fix")  # `qazfix "text"` is shorthand for `qazfix fix "text"`
    if not argv:
        argv = ["fix", "-"]
    parser = argparse.ArgumentParser(prog="qazfix", description="Restore Kazakh letters in text typed without them.")
    sub = parser.add_subparsers(dest="command", required=True)

    f = sub.add_parser("fix", help="restore text (default command)")
    f.add_argument("text", nargs="?", help="text to fix, or - to read stdin")
    f.add_argument("--model", help="model file (default: bundled)")
    f.set_defaults(func=cmd_fix)

    b = sub.add_parser("build", help="train a model from Kazakh text or word-frequency files")
    b.add_argument("corpus", nargs="+")
    b.add_argument("-o", "--output", required=True)
    b.add_argument("--russian", help="file of Russian words to leave untouched")
    b.add_argument("--harmony", action="store_true", help="use vowel-harmony context (experimental)")
    b.set_defaults(func=cmd_build)

    e = sub.add_parser("eval", help="strip correct Kazakh text, restore it, report accuracy")
    e.add_argument("testfile", help="correctly written Kazakh text, one sentence per line")
    e.add_argument("--model")
    e.set_defaults(func=cmd_eval)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
