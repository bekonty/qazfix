from qazfix import restore


def test_keep_leaves_users_words_alone():
    assert restore("Прога калк мидка", keep={"прога", "калк", "мидка"}) == "Прога калк мидка"


def test_keep_is_case_insensitive_and_only_affects_listed_words():
    out = restore("прога биз бугн келдык", keep=["Прога"])
    assert out.startswith("прога ")
    assert out != "прога биз бугн келдык"  # the other words are still fixed


def test_default_unchanged():
    assert restore("казак тили") == "қазақ тілі"
