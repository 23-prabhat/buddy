from __future__ import annotations

import hashlib
import math
import re
from collections import Counter


_TOKEN = re.compile(r"[a-z0-9_]{2,}")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class HashingEmbedder:
    """Dependency-free bag-of-words hashing embedder."""

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        toks = tokenize(text)
        if not toks:
            return vec
        counts = Counter(toks)
        for tok, cnt in counts.items():
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[idx] += sign * float(cnt)
        # l2 normalize
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=False))
