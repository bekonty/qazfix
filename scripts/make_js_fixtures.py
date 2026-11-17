"""Generate Python answers that qazfix.js must reproduce exactly.

    python scripts/make_js_fixtures.py web/model.json tests/js/fixtures.json
    node tests/js/crosscheck.mjs web/model.json tests/js/fixtures.json

Inputs are built from the model itself so the check needs no extra data, and
they deliberately hit every code path: known words, unseen inflections
(character model), ы typed for і, Russian words, chat words, laughter, case.
"""

import json
import random
import sys
from pathlib import Path

from qazfix import restore
from qazfix.keyboard import Predictor
from qazfix.model import Model

SUFFIXES = ["лар", "дың", "ге", "мен", "дагы", "ымыз", "сыз", "кан", "ынан", "тарына"]
EDGE = [
    "", "Ок", "окок", "ия", "хахаха", "ХАХАХА", "ахах", "бiз", "БIЗ", "Hello мир",
    "қазір", "Қазақстан", "казак-орыс", "2026 жылы!", "e-mail мен", "ертен,встреча",
    "казак тили", "КАЗАК", "Казак", "кАзАк", "ы", "к", "кк", "ң", "¾ казак ²",
]


def main(model_path: str, out_path: str, n: int = 1500, seed: int = 7) -> None:
    rng = random.Random(seed)
    data = json.loads(Path(model_path).read_text(encoding="utf-8"))
    model = Model(data["words"], data["chars"], set(data["russian"]), data["meta"])
    pred = Predictor(model)

    keys = sorted(model.words)
    sample = rng.sample(keys, min(n, len(keys)))
    words = set(sample)
    words |= {k + rng.choice(SUFFIXES) for k in sample}  # mostly unseen: character model
    words |= {k.replace("и", "ы") for k in sample if "и" in k}  # ы typed for і
    words |= set(rng.sample(sorted(model.russian), min(300, len(model.russian))))
    words = sorted(words)
    cased = [w.capitalize() for w in words[::5]] + [w.upper() for w in words[::17]]

    sentences = [" ".join(rng.sample(words, 6)) + rng.choice([".", "?", "!", ","]) for _ in range(300)]
    prefixes = sorted({w[:k] for w in rng.sample(words, 600) for k in range(1, len(w) + 1)})

    fixtures = {
        "restore": [[t, restore(t, model)] for t in EDGE + sentences],
        "candidates": [
            [w, [[s.word, s.score] for s in pred.candidates(w, n=3)], pred.should_autocorrect(w)]
            for w in EDGE + words + cased
        ],
        "complete": [[p, [[s.word, s.score] for s in pred.complete(p, n=3)]] for p in prefixes],
    }
    Path(out_path).write_text(json.dumps(fixtures, ensure_ascii=False), encoding="utf-8")
    print(f"{out_path}: {len(fixtures['restore'])} texts, {len(fixtures['candidates'])} words, "
          f"{len(fixtures['complete'])} prefixes")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
