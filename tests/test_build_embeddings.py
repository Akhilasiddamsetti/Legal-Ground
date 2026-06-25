import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
NPZ = ROOT / "sample-docs" / "embeddings.npz"
CHUNKS = json.loads((ROOT / "sample-docs" / "chunks.json").read_text())


def test_embeddings_file_aligns_with_chunks():
    assert NPZ.exists(), "run: venv\\Scripts\\python.exe scripts\\build_embeddings.py"
    data = np.load(NPZ, allow_pickle=True)
    ids = list(data["ids"])
    vectors = data["vectors"]
    chunk_ids = [chunk["chunk_id"] for chunk in CHUNKS["chunks"]]
    assert ids == chunk_ids
    assert vectors.shape[0] == len(chunk_ids)
    assert vectors.shape[1] >= 128
