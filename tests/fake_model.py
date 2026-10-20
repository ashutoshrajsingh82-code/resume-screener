"""A tiny deterministic stand-in for SentenceTransformer, so tests need no download."""
import re
import zlib

import numpy as np


class FakeModel:
    """Hashed bag-of-words embeddings: texts sharing words get similar vectors."""

    def __init__(self, dims: int = 256):
        self.dims = dims

    def encode(self, texts, normalize_embeddings=False, batch_size=32, show_progress_bar=False):
        out = np.zeros((len(texts), self.dims))
        for i, text in enumerate(texts):
            for token in re.findall(r"[a-z0-9+#.]+", text.lower()):
                out[i, zlib.crc32(token.encode()) % self.dims] += 1.0
        if normalize_embeddings:
            norms = np.linalg.norm(out, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            out = out / norms
        return out
