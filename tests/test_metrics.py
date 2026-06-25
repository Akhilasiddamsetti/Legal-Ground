from learning_curve.eval.metrics import hits_at_k, precision_at_k, recall_at_k, reciprocal_rank


def test_hits_at_k_counts_only_top_k():
    retrieved = ["a", "b", "c", "d"]
    assert hits_at_k(retrieved, expected=["b", "d"], k=2) == 1
    assert hits_at_k(retrieved, expected=["b", "d"], k=4) == 2


def test_recall_at_k():
    retrieved = ["a", "b", "c"]
    assert recall_at_k(retrieved, expected=["b", "x"], k=3) == 0.5


def test_precision_at_k():
    retrieved = ["a", "b", "c"]
    assert precision_at_k(retrieved, expected=["b"], k=2) == 0.5


def test_reciprocal_rank_uses_first_relevant():
    retrieved = ["a", "b", "c"]
    assert reciprocal_rank(retrieved, expected=["c"]) == 1 / 3
    assert reciprocal_rank(retrieved, expected=["z"]) == 0.0


def test_empty_expected_is_perfect_recall():
    assert recall_at_k(["a"], expected=[], k=1) == 1.0
