"""Download Kazakh Wikipedia as plain text, for training a stronger qazfix model.

Run on your own computer (needs internet and `pip install datasets`):

    python scripts/wikipedia_text.py kkwiki.txt
    qazfix build kkwiki.txt data/kk_full.txt -o model.json.gz --russian russian.txt
    qazfix eval ud_test.txt --model model.json.gz

Note: this script was written without being able to run it (Hugging Face was not
reachable from the environment it was written in). If the dataset name or config
has changed, look up "wikimedia/wikipedia" on huggingface.co and pick the newest
Kazakh config ("<date>.kk").
"""

import sys

from datasets import load_dataset

out_path = sys.argv[1] if len(sys.argv) > 1 else "kkwiki.txt"
config = sys.argv[2] if len(sys.argv) > 2 else "20231101.kk"

ds = load_dataset("wikimedia/wikipedia", config, split="train", streaming=True)
n = 0
with open(out_path, "w", encoding="utf-8") as f:
    for row in ds:
        f.write(row["text"].replace("\n\n", "\n") + "\n")
        n += 1
        if n % 10000 == 0:
            print(f"{n} articles...", file=sys.stderr)
print(f"wrote {n} articles to {out_path}", file=sys.stderr)
