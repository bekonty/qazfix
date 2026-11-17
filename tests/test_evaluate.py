from collections import Counter

from qazfix.evaluate import evaluate
from qazfix.model import Model


def test_do_nothing_baseline_counts():
    lines = ["Қазақ тілі мен ана тілі."]
    r = evaluate(lines, None, restore_fn=lambda w: w)
    # Words with an ambiguous letter after stripping: қазақ тілі мен ана тілі
    assert r.words == 5
    assert r.had_special == 3 and r.special_fixed == 0
    assert r.plain == 2 and r.plain_kept == 2


def test_perfect_model_scores_100():
    lines = ["Қазақ тілі мен ана тілі."]
    m = Model.train(Counter({"қазақ": 1, "тілі": 1, "мен": 1, "ана": 1}))
    assert evaluate(lines, m).accuracy == 1.0
