"""Regression tests for problems found by running qazfix on real chat messages."""

import pytest

import qazfix
from qazfix.evaluate import strip_chat


def test_word_already_typed_with_kazakh_letters_is_untouched():
    # Bug found in real chat: "қазір" became "қәзір".
    assert qazfix.restore("қазір") == "қазір"
    assert qazfix.restore("келіп алып кетесінбе") == "келіп алып кетесінбе"


@pytest.mark.parametrize("word", ["Ок", "окок", "ия", "хахаха", "Хахахахах", "ахахах"])
def test_chat_words_and_laughter_untouched(word):
    assert qazfix.restore(word) == word


@pytest.mark.parametrize(
    "typed, expected",
    [("негызы", "негізі"), ("озым", "өзім"), ("кеттым", "кеттім"), ("быреуы", "біреуі")],
)
def test_i_typed_as_y(typed, expected):
    assert qazfix.restore(typed) == expected


def test_real_y_is_not_changed_without_dictionary_evidence():
    assert qazfix.restore("кыз") == "қыз"


def test_strip_chat():
    assert strip_chat("Біз қазақпыз") == "Быз казакпыз"
