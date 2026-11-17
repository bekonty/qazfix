"""The Kazakh-specific letters and how people type them on keyboards without them."""

from __future__ import annotations

# Kazakh-specific letter -> what people type instead (Russian-layout habit).
# ұ and ү both collapse to у, which is why restoration needs context.
STRIP = {
    "ә": "а",
    "ғ": "г",
    "қ": "к",
    "ң": "н",
    "ө": "о",
    "ұ": "у",
    "ү": "у",
    "і": "и",
    "һ": "х",
}
STRIP.update({k.upper(): v.upper() for k, v in STRIP.items()})

SPECIAL = frozenset(STRIP)  # letters that only Kazakh uses (vs Russian)

# Plain letter -> every letter it might really be (itself first).
OPTIONS: dict[str, tuple[str, ...]] = {}
for _special, _plain in STRIP.items():
    if _plain.islower():
        OPTIONS.setdefault(_plain, (_plain,))
        OPTIONS[_plain] = OPTIONS[_plain] + (_special,)

AMBIGUOUS = frozenset(OPTIONS)  # а г к н о у и х

# Latin look-alikes typed by switching layouts mid-word ("бiз" with a Latin i).
LATIN_LOOKALIKES = {"i": "і", "I": "І"}

CYRILLIC = frozenset(
    "абвгғдеёжзийкқлмнңоөпрстуұүфхһцчшщъыіьэюя"
    "АБВГҒДЕЁЖЗИЙКҚЛМНҢОӨПРСТУҰҮФХҺЦЧШЩЪЫІЬЭЮЯ"
)

FRONT_MARKERS = frozenset("еэ")  # front vowels that survive stripping
BACK_MARKERS = frozenset("ы")  # back vowels that survive stripping


def strip(text: str) -> str:
    """Remove Kazakh-specific letters the way a Russian keyboard user would."""
    return "".join(STRIP.get(ch, ch) for ch in text)


def harmony(stripped_word: str) -> str:
    """Vowel-harmony class of a stripped word: F(ront), B(ack) or ? (unknown).

    Kazakh words are usually all-front or all-back. After stripping, 'е' still
    signals front and 'ы' still signals back, which hints whether а should be ә,
    о should be ө, у should be ү, and so on.
    """
    lw = stripped_word.lower()
    front = any(c in FRONT_MARKERS for c in lw)
    back = any(c in BACK_MARKERS for c in lw)
    if front and not back:
        return "F"
    if back and not front:
        return "B"
    return "?"


def is_cyrillic_word(token: str) -> bool:
    return any(c in CYRILLIC for c in token)
