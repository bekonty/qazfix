from collections import Counter

import pytest

from qazfix.model import Model

CORPUS = Counter({
    "қазақ": 50, "казак": 2,          # Kazakh vs Cossack: frequency decides
    "тілі": 30, "тілінде": 10, "тіліміз": 5,
    "біз": 40, "бізге": 10, "бізде": 8,
    "ертең": 20, "ертеңгі": 5,
    "мектепке": 6, "үйге": 6, "үйде": 6,
    "мен": 60, "сен": 30,
})


@pytest.fixture(scope="module")
def model():
    return Model.train(CORPUS, russian=["встреча", "конкурс"])


def test_seen_word_takes_most_frequent_spelling(model):
    assert model.restore_word("казак") == "қазақ"
    assert model.restore_word("тили") == "тілі"


def test_unseen_inflection_uses_character_context(model):
    # "тілдері" never appears in CORPUS, but its letters' contexts do.
    assert model.restore_word("тилимизде").startswith("тіліміз")


def test_word_without_ambiguous_letters_untouched(model):
    assert model.restore_word("сез") == "сез"


def test_russian_guard(model):
    assert model.restore_word("встреча") == "встреча"


def test_already_typed_special_letters_are_kept(model):
    # The user typed ң themselves; never overwrite their choice.
    assert model.restore_word("ертең") == "ертең"
    assert model.restore_word("кәзак")[1] == "ә"


def test_save_load_roundtrip(model, tmp_path):
    path = tmp_path / "m.json.gz"
    model.save(path)
    again = Model.load(path)
    for w in ["казак", "тилимизде", "встреча", "биз"]:
        assert again.restore_word(w) == model.restore_word(w)


def test_load_rejects_unknown_format(tmp_path):
    import gzip
    import json

    path = tmp_path / "bad.json.gz"
    with gzip.open(path, "wt") as f:
        json.dump({"format": 999}, f)
    with pytest.raises(ValueError):
        Model.load(path)
