# ============================================================
# 📁 api/services/embedding_service.py
# ============================================================
import logging
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder
from openai import OpenAI
from api.config.config import AZURE_OPENAI_API_KEY

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# 🧠 Embedding models
# ------------------------------------------------------------

# ✅ Local embedding model (384D)
LOCAL_MODEL_NAME = "sentence-transformers/multi-qa-MiniLM-L6-cos-v1"
local_embedder = SentenceTransformer(LOCAL_MODEL_NAME)

# ✅ Optional reranker (semantic relevance)
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# ✅ OpenAI client for cloud embeddings (1536D)
openai_client = OpenAI(api_key=AZURE_OPENAI_API_KEY)


# ------------------------------------------------------------
# ⚙️ Embedding utilities
# ------------------------------------------------------------
def get_embedding(text: str, use_openai: bool = False):
    """
    Trả về embedding vector của text.
    - Nếu use_openai=True → dùng OpenAI (1536 chiều)
    - Ngược lại → dùng local MiniLM (384 chiều)
    """
    text = (text or "").strip()
    if not text:
        return None

    print(f"[Embedding Service] Getting embedding | use_openai={use_openai}")
    if use_openai:
        try:
            resp = openai_client.embeddings.create(
                model="text-embedding-3-small",  # 1536D
                input=text
            )
            return resp.data[0].embedding
        except Exception as e:
            logger.warning(f"OpenAI embedding failed, fallback to local. Error: {e}")

    try:
        return local_embedder.encode(text, convert_to_numpy=True).tolist()
    except Exception as e:
        logger.error(f"Local embedding failed: {e}")
        return None


def safe_get_embedding(text: str, use_openai: bool = False):
    """
    Giống get_embedding nhưng có try/catch an toàn.
    """
    try:
        return get_embedding(text, use_openai=use_openai)
    except Exception as e:
        logger.error(f"safe_get_embedding error: {e}")
        return None


def cosine_similarity(vec1, vec2):
    """
    Tính cosine similarity giữa 2 vector numpy.
    """
    if vec1 is None or vec2 is None:
        return 0.0
    a = np.array(vec1)
    b = np.array(vec2)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)
