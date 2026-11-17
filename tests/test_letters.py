import pytest

from qazfix.letters import AMBIGUOUS, OPTIONS, SPECIAL, harmony, strip


def test_strip_all_special_letters():
    assert strip("әғқңөұүіһ") == "агкноууих"
    assert strip("ӘҒҚҢӨҰҮІҺ") == "АГКНОУУИХ"


def test_strip_leaves_other_text():
    assert strip("Hello, мир! 123") == "Hello, мир! 123"


def test_options_cover_every_special_letter():
    restorable = {o for opts in OPTIONS.values() for o in opts}
    assert {c for c in SPECIAL if c.islower()} <= restorable
    assert OPTIONS["у"] == ("у", "ұ", "ү")
    assert AMBIGUOUS == frozenset("агкноуих")


@pytest.mark.parametrize("word, expected", [("бер", "F"), ("бар", "?"), ("кыз", "B"), ("бейбыт", "?")])
def test_harmony(word, expected):
    assert harmony(word) == expected
