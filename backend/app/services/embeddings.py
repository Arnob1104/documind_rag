from functools import lru_cache
from fastembed import TextEmbedding

@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    return TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")

def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return [v.tolist() for v in _model().embed(texts)]

def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
