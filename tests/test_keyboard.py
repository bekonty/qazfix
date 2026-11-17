from collections import Counter

import pytest

import qazfix
from qazfix.cli import main
from qazfix.keyboard import Predictor
from qazfix.model import Model


@pytest.fixture(scope="module")
def pred():
    return Predictor()


@pytest.mark.parametrize("word", ["казак", "тилинде", "сойлеймин", "негызы", "встреча", "Ок", "кыргызды"])
def test_first_suggestion_matches_restore(pred, word):
    assert pred.candidates(word)[0].word == qazfix.restore(word)


def test_scores_are_sorted_probabilities(pred):
    cands = pred.candidates("калайсын", n=3)
    scores = [c.score for c in cands]
    assert scores == sorted(scores, reverse=True)
    assert 0 < sum(scores) <= 1.0001


def test_suggestion_bar_contains_alternative(pred):
    # The ы→і guess is not trusted blindly: the real word is offered too.
    words = [c.word for c in pred.candidates("кыргызды")]
    assert "қырғызды" in words


def test_case_preserved(pred):
    assert pred.candidates("Казак")[0].word == "Қазақ"
    assert pred.candidates("КАЗАК")[0].word == "ҚАЗАҚ"
    assert pred.candidates("Ок")[0].word == "Ок"


def test_autocorrect_only_when_confident(pred):
    assert pred.should_autocorrect("казак") == "қазақ"
    assert pred.should_autocorrect("бугн") is None  # shorthand: unsure, leave it
    assert pred.should_autocorrect("Ок") is None
    assert pred.should_autocorrect("қазақ") is None


def test_completion(pred):
    words = [s.word for s in pred.complete("казакс")]
    assert "қазақстан" in words
    assert pred.complete("к") == []  # too short to be useful


def test_completion_respects_typed_kazakh_letters():
    m = Model.train(Counter({"қазақ": 5, "казарма": 9}))
    p = Predictor(m)
    assert [s.word for s in p.complete("қаз")] == ["қазақ"]
    assert {s.word for s in p.complete("каз")} == {"казарма", "қазақ"}


def test_cli_suggest_and_complete(capsys):
    assert main(["suggest", "казак"]) == 0
    assert "қазақ" in capsys.readouterr().out
    assert main(["complete", "казакс"]) == 0
    assert "қазақстан" in capsys.readouterr().out
