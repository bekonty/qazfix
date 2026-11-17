"""End-to-end behaviour of qazfix.restore with the bundled model."""

import pytest

import qazfix
from qazfix.cli import main


@pytest.mark.parametrize(
    "typed, expected",
    [
        ("Казакстан Республикасы", "Қазақстан Республикасы"),
        ("Мен казак тилинде сойлеймин", "Мен қазақ тілінде сөйлеймін"),
        ("Биз ертен Алматыга барамыз", "Біз ертең Алматыға барамыз"),
    ],
)
def test_examples(typed, expected):
    assert qazfix.restore(typed) == expected


def test_case_is_preserved():
    assert qazfix.restore("КАЗАК ТИЛИ") == "ҚАЗАҚ ТІЛІ"
    assert qazfix.restore("Казак") == "Қазақ"


def test_punctuation_spacing_and_numbers_preserved():
    text = "  Биз,  2026 жылы!\nКазак?  "
    out = qazfix.restore(text)
    assert out == "  Біз,  2026 жылы!\nҚазақ?  "


def test_non_cyrillic_untouched():
    assert qazfix.restore("Hello world, qazaq tili") == "Hello world, qazaq tili"


def test_russian_word_in_mixed_sentence_untouched():
    assert "встреча" in qazfix.restore("Ертен встреча бар ма?")


def test_latin_i_lookalike_is_handled():
    # "бiз" typed with a Latin i after switching keyboard layout.
    assert qazfix.restore("бiз") == "біз"


def test_restore_is_idempotent_on_correct_text():
    correct = "Қазақстан Республикасы"
    assert qazfix.restore(correct) == correct


def test_cli_fix(capsys):
    assert main(["Казак тили"]) == 0
    assert capsys.readouterr().out == "Қазақ тілі\n"


def test_cli_build_and_eval(tmp_path, capsys):
    corpus = tmp_path / "kk.txt"
    corpus.write_text("Қазақ тілі бай тіл.\nБіз қазақ тілінде сөйлейміз.\n", encoding="utf-8")
    model = tmp_path / "m.json.gz"
    assert main(["build", str(corpus), "-o", str(model)]) == 0
    assert main(["eval", str(corpus), "--model", str(model)]) == 0
    assert "word accuracy" in capsys.readouterr().out
