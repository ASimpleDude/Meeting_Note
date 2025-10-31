# api/services/embedding_service.py
import logging
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder
from openai import OpenAI
from api.config.config import AZURE_OPENAI_API_KEY

logger = logging.getLogger(__name__)

# Local embedding model (dim = 384)
local_embedder = SentenceTransformer("sentence-transformers/multi-qa-MiniLM-L6-cos-v1")

# Optional reranker
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# Optional OpenAI client for fallback (if you use it)
openai_client = OpenAI(api_key=AZURE_OPENAI_API_KEY)


def get_embedding(text: str, use_openai: bool = False):
    text = (text or "").strip()
    if not text:
        return None
    try:
        if use_openai:
            resp = openai_client.embeddings.create(model="text-embedding-3-small", input=text)
            return resp.data[0].embedding
    except Exception as e:
        logger.warning(f"OpenAI embedding failed, fallback to local. Error: {e}")

    try:
        return local_embedder.encode(text, convert_to_numpy=True).tolist()
    except Exception as e:
        logger.error(f"Local embedding failed: {e}")
        return None


def safe_get_embedding(text: str):
    try:
        return get_embedding(text)
    except Exception as e:
        logger.error(f"safe_get_embedding error: {e}")
        return None


def cosine_similarity(vec1, vec2):
    if vec1 is None or vec2 is None:
        return 0.0
    a = np.array(vec1)
    b = np.array(vec2)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)
