import numpy as np

from learning_curve.retrieval.embeddings import SentenceTransformerEmbedder, cosine_scores


def test_cosine_scores_ranks_parallel_vector_highest():
    matrix = np.array([[1.0, 0.0], [0.0, 1.0], [0.7071, 0.7071]], dtype=np.float32)
    query = np.array([1.0, 0.0], dtype=np.float32)
    scores = cosine_scores(query, matrix)
    assert int(np.argmax(scores)) == 0
    assert scores[2] > scores[1]


def test_embedder_shape_and_norm():
    embedder = SentenceTransformerEmbedder()
    vectors = embedder.embed_texts(["failed inspection report", "shipment release approval"])
    assert vectors.shape[0] == 2
    norms = np.linalg.norm(vectors, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-3)
