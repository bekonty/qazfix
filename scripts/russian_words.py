"""Write the most common Russian words, used so qazfix leaves Russian words alone.

Needs `pip install wordfreq` (build time only, not a runtime dependency).

    python scripts/russian_words.py 30000 > russian.txt
"""

import sys

from wordfreq import top_n_list

n = int(sys.argv[1]) if len(sys.argv) > 1 else 30000
print("\n".join(top_n_list("ru", n)))
