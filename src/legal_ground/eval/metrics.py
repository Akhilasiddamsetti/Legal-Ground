"""Document-level retrieval metrics.

All inputs are ordered, de-duplicated doc_id lists.
"""


def hits_at_k(retrieved: list[str], expected: list[str], k: int) -> int:
    top_k = set(retrieved[:k])
    return sum(1 for doc_id in expected if doc_id in top_k)


def recall_at_k(retrieved: list[str], expected: list[str], k: int) -> float:
    if not expected:
        return 1.0
    return hits_at_k(retrieved, expected, k) / len(expected)


def precision_at_k(retrieved: list[str], expected: list[str], k: int) -> float:
    if k <= 0:
        return 0.0
    return hits_at_k(retrieved, expected, k) / k


def reciprocal_rank(retrieved: list[str], expected: list[str]) -> float:
    expected_set = set(expected)
    for index, doc_id in enumerate(retrieved, start=1):
        if doc_id in expected_set:
            return 1.0 / index
    return 0.0
