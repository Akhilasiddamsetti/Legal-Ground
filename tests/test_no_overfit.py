from learning_curve.retrieval import ChunkSearchEngine, normalize_token


def test_legally_distinct_terms_are_not_collapsed():
    assert normalize_token("approval") != normalize_token("release")
    assert normalize_token("deposition") != normalize_token("witness")


def test_no_heuristic_boosts_method():
    assert not hasattr(ChunkSearchEngine, "_heuristic_boosts")
