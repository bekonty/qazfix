"""Dropped-vowel shorthand (баур -> бауыр) and the guards around it."""

import pytest

import qazfix
from qazfix.keyboard import Predictor


@pytest.mark.parametrize(
    "typed, expected",
    [
        ("баур", "бауыр"),
        ("бугн", "бүгін"),
        ("кеттк", "кеттік"),
        ("жаздн", "жаздың"),
        ("коремз", "көреміз"),
        ("колдаймн", "қолдаймын"),  # ы, not і: the word is back-vowel
        ("бз", "біз"),
        ("Бугн", "Бүгін"),
        ("БУГН", "БҮГІН"),
    ],
)
def test_dropped_vowel_restored(typed, expected):
    assert qazfix.restore(typed) == expected


@pytest.mark.parametrize("word", ["почтт", "стеднба", "сез", "мен", "Ок", "хахаха"])
def test_unknown_or_real_words_untouched(word):
    assert qazfix.restore(word) == word


def test_russian_stem_with_kazakh_ending_kept():
    assert qazfix.restore("Списокта") == "Списокта"


def test_real_y_word_not_swapped_to_i():
    assert qazfix.restore("кыргызды") == "қырғызды"  # қырғыз + ды, not кіргізді
    assert qazfix.restore("мектептын") == "мектептің"  # ы next to е is impossible


def test_chat_sentence():
    assert qazfix.restore("Быз суйттык кыргызды") == "Біз сүйттық қырғызды"


def test_keyboard_autocorrects_shorthand_on_space():
    p = Predictor()
    assert p.should_autocorrect("баур") == "бауыр"
    assert p.candidates("баур")[0].word == "бауыр"
    assert p.should_autocorrect("почтт") is None


@pytest.mark.parametrize(
    "typed, expected",
    [
        ("Казыр ма", "Қазір ма"),  # rare "казыр" in Wikipedia must not beat frequent қазір
        ("Шукыр", "Шүкір"),
        ("тыс", "тыс"),  # real ы-word with a frequent і-twin (тіс): kept
        ("кыз", "қыз"),
        ("Четм", "Четм"),  # Russian slang, not че + тім
    ],
)
def test_frequency_aware_y_and_noise(typed, expected):
    assert qazfix.restore(typed) == expected
