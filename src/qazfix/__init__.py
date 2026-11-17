"""qazfix: restore Kazakh letters (ә ғ қ ң ө ұ ү і һ) in text typed without them.

>>> import qazfix
>>> qazfix.restore("Казакстан")
'Қазақстан'
"""

from __future__ import annotations

import re
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

from .letters import LATIN_LOOKALIKES, is_cyrillic_word, strip
from .model import Model

__version__ = "0.5.1"
__all__ = ["Model", "load_model", "restore", "strip"]

_TOKEN = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*", re.UNICODE)


@lru_cache(maxsize=4)
def load_model(path: str | None = None) -> Model:
    """Load a model file, or the one bundled with the package."""
    if path is None:
        return Model.load(files("qazfix") / "data" / "model.json.gz")
    return Model.load(Path(path))


def _apply_case(template: str, lower: str) -> str:
    if len(template) == len(lower):  # letters only swapped: copy case letter by letter
        return "".join(r.upper() if t.isupper() else r for t, r in zip(template, lower))
    # a vowel was put back (бугн -> бүгін): copy the word's overall case
    if template.isupper() and len(template) > 1:
        return lower.upper()
    if template[:1].isupper():
        return lower[:1].upper() + lower[1:]
    return lower


def _fix_token(token: str, model: Model, keep=()) -> str:
    if not is_cyrillic_word(token) or token.lower() in keep:
        return token  # English, numbers, Latin-script Kazakh, the user's own words: untouched
    token = "".join(LATIN_LOOKALIKES.get(c, c) for c in token)
    return _apply_case(token, model.restore_word(token.lower()))


def restore(text: str, model: Model | None = None, keep=()) -> str:
    """Restore Kazakh letters in `text`. Spacing, punctuation and case are kept.

    `keep`: lowercase words to leave exactly as typed, such as names and slang
    ("прога", "калк"). This is the personal dictionary a keyboard builds when
    the user undoes a correction.
    """
    m = model or load_model()
    keep = {w.lower() for w in keep}
    return _TOKEN.sub(lambda mt: _fix_token(mt.group(0), m, keep), text)
