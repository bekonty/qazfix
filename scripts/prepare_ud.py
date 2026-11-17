"""Split the UD Kazakh-KTB treebank into train/test text files by source document.

Splitting by document (not by sentence) keeps near-duplicate sentences from the
same article out of the test set, so the accuracy we report is honest.

    python scripts/prepare_ud.py path/to/UD_Kazakh-KTB out_dir
"""

import hashlib
import sys
from pathlib import Path

# Test documents that may also be in Kazakh Wikipedia. When Wikipedia word counts are used
# for training, report accuracy on ud_test_clean.txt (test without these) to avoid leakage.
MAYBE_IN_WIKIPEDIA = {"Шымкент.tagged.txt", "Elizabeth-II.tagged.txt", "wikipedia-news.tagged.txt"}


def sentences(conllu: Path):
    doc = text = None
    for line in conllu.read_text(encoding="utf-8").splitlines():
        if line.startswith("# sent_id = "):
            doc = line.split("= ", 1)[1].split(":", 1)[0]
        elif line.startswith("# text = "):
            text = line.split("= ", 1)[1]
        elif not line.strip() and text:
            yield doc, text
            doc = text = None


def main(ud_dir: str, out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    train, test, clean = [], [], []
    for f in sorted(Path(ud_dir).glob("*.conllu")):
        for doc, text in sentences(f):
            bucket = int(hashlib.sha256(doc.encode()).hexdigest(), 16) % 2
            (test if bucket else train).append(text)
            if bucket and doc not in MAYBE_IN_WIKIPEDIA:
                clean.append(text)
    (out / "ud_train.txt").write_text("\n".join(train) + "\n", encoding="utf-8")
    (out / "ud_test.txt").write_text("\n".join(test) + "\n", encoding="utf-8")
    (out / "ud_test_clean.txt").write_text("\n".join(clean) + "\n", encoding="utf-8")
    print(f"train {len(train)} sentences, test {len(test)} sentences ({len(clean)} not from Wikipedia)")


if __name__ == "__main__":
    main(*sys.argv[1:3])
