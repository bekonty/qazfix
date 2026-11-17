"""Turn a big Kazakh text file into compact word counts for `qazfix build`.

    python scripts/wikipedia_text.py kkwiki.txt          # ~238k articles
    python scripts/word_counts.py kkwiki.txt kkwiki_words.txt

Writes "word count" lines (words seen at least twice), most frequent first.
"""

import re
import sys
from collections import Counter

TOKEN = re.compile(r"[^\W\d_]+")


def main(src: str, out: str) -> None:
    counts: Counter = Counter()
    with open(src, encoding="utf-8") as f:
        for line in f:
            counts.update(t.lower() for t in TOKEN.findall(line))
    with open(out, "w", encoding="utf-8") as f:
        f.writelines(f"{w} {c}\n" for w, c in counts.most_common() if c >= 2)
    print(f"{len(counts):,} distinct words, {sum(counts.values()):,} tokens -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
