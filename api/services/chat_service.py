# ============================================================
# 📁 api/services/chat_service.py
# ============================================================
import logging
import numpy as np
import chromadb
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception_type
from openai import AzureOpenAI, OpenAI, APIError, RateLimitError, APITimeoutError
from sentence_transformers import SentenceTransformer, CrossEncoder
from api.services.chroma_client import get_chroma_collection

from api.config.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_ENDPOINT,
)
from api.services.moderation_service import moderate_input

# ============================================================
# ⚙️ Setup Logging
# ============================================================
logger = logging.getLogger(__name__)

# ============================================================
# 🧠 ChromaDB Client
# ============================================================
collection = get_chroma_collection()

# ============================================================
# 🔧 Embedding & Reranker Models
# ============================================================
# Local embedder (miễn phí)
local_embedder = SentenceTransformer("sentence-transformers/multi-qa-MiniLM-L6-cos-v1")

# Reranker (vẫn giữ nguyên)
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# OpenAI embedding client (tùy chọn)
openai_client = OpenAI(api_key=AZURE_OPENAI_API_KEY)

# ============================================================
# 🤖 Azure OpenAI Client
# ============================================================
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

# ============================================================
# 🧩 Embedding Helper
# ============================================================
def safe_get_embedding(query: str):
    query = query.strip()
    if not query:
        return None
    try:
        return get_embedding(query)
    except Exception as e:
        logger.error(f"❌ Embedding failed: {e}")
        return None


def get_embedding(text: str, use_openai: bool = False):
    """
    Sinh vector embedding từ text.
    - Nếu use_openai=True → dùng text-embedding-3-small (OpenAI API)
    - Ngược lại → dùng local model multi-qa-MiniLM-L6-cos-v1
    """
    if use_openai:
        try:
            response = openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            emb = response.data[0].embedding
            return emb
        except Exception as e:
            logger.warning(f"⚠️ Lỗi khi gọi OpenAI embedding API, fallback sang local: {e}")
            return local_embedder.encode(text, convert_to_numpy=True).tolist()
    else:
        return local_embedder.encode(text, convert_to_numpy=True).tolist()

# ============================================================
# 💾 Lưu hội thoại vào ChromaDB
# ============================================================
def save_to_chroma(session_id: str, user_message: str, assistant_reply: str):
    """Lưu 1 lượt hội thoại vào ChromaDB."""
    text = f"[{session_id}] User: {user_message}\nAssistant: {assistant_reply}"
    embedding = get_embedding(text)
    all_ids = collection.get()["ids"]
    next_id = f"{session_id}_{len(all_ids)}"

    collection.add(
        documents=[text],
        embeddings=[embedding],
        metadatas=[{"session_id": session_id}],
        ids=[next_id],
    )
    logger.info(f"💾 Saved conversation to Chroma (ID: {next_id})")

# ============================================================
# 🔍 Tìm kiếm thông tin từ trí nhớ (ChromaDB + Reranker)
# ============================================================
import numpy as np
from collections import defaultdict
from numpy.linalg import norm

def cosine_similarity(v1, v2):
    v1, v2 = np.array(v1), np.array(v2)
    if norm(v1) == 0 or norm(v2) == 0:
        return 0.0
    return np.dot(v1, v2) / (norm(v1) * norm(v2))

def search_memory(session_id: str, query: str, top_k: int = 5, threshold: float = 0.7, return_score=False):
    """
    Search memory with exact question match first.
    1. Check session cache
    2. Check DB for exact question previously asked → return old answer
    3. Embedding search + reranker if no exact match
    4. Return only if score >= threshold
    """
    cache_key = query.strip()

    query_emb = safe_get_embedding(query)
    if not query_emb:
        return ("", 0.0) if return_score else ""

    try:
        results = collection.query(
            query_embeddings=[query_emb],
            n_results=top_k,
            where={"session_id": session_id},
            include=["documents", "embeddings"]  # cần include embeddings nếu có
        )
    except ValueError:
        return ("", 0.0) if return_score else ""

    candidate_docs = results.get("documents", [[]])[0]
    if not candidate_docs:
        return ("", 0.0) if return_score else ""

    # =============================
    # 1️⃣ Nếu embeddings có sẵn → tính cosine similarity
    # =============================
    candidate_embeddings = results.get("embeddings", [[]])[0]
    if candidate_embeddings is not None and len(candidate_embeddings) == len(candidate_docs):
        scores = [cosine_similarity(query_emb, doc_emb) for doc_emb in candidate_embeddings]
    else:
        # Fallback reranker
        pairs = [[query, doc] for doc in candidate_docs]
        raw_scores = reranker.predict(pairs)
        scores = [np.tanh(s) for s in raw_scores]

    # Chọn document tốt nhất
    sorted_indices = np.argsort(scores)[::-1]
    best_doc = candidate_docs[sorted_indices[0]]
    best_score = scores[sorted_indices[0]]

    logger.info(f"🔎 Memory search top score: {best_score:.3f}")

    if best_score >= threshold:
        if return_score:
            return best_doc, best_score
        return best_doc
    else:
        return ("", best_score) if return_score else ""


# ============================================================
# 🔁 Retry Wrapper cho Azure API
# ============================================================
@retry(
    retry=retry_if_exception_type((RateLimitError, APIError, APITimeoutError)),
    wait=wait_random_exponential(min=1, max=30),
    stop=stop_after_attempt(3),
)
def _call_azure_openai(messages: list):
    """Gọi Azure OpenAI ChatCompletion."""
    logger.info("🔄 Gửi request đến Azure OpenAI...")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
        max_tokens=800,
        timeout=30,
    )
    logger.info("✅ Nhận phản hồi thành công từ Azure OpenAI.")
    return response

# ============================================================
# 💬 Hàm chính: Gọi Azure OpenAI, kết hợp với Chroma Memory
# ============================================================
def generate_summary(messages: list, user_input: str = None, memory_context: str = None) -> str:
    """
    Gọi Azure OpenAI để sinh phản hồi.
    Nếu có memory_context thì append vào prompt trước khi gửi.
    """
    try:
        user_message = user_input or messages[-1]["content"]

        # Thêm trí nhớ nếu có
        if memory_context:
            user_message += f"\n\nDưới đây là thông tin liên quan từ các lần trao đổi trước:\n{memory_context}\n"

        temp_messages = messages.copy()
        temp_messages[-1]["content"] = user_message

        # # Bật lại khi cần kiểm duyệt
        # if not moderate_input(user_message):
        #     return "🚫 Nội dung bị từ chối — vui lòng không gửi dữ liệu nhạy cảm."

        response = _call_azure_openai(temp_messages)
        if not response or not response.choices:
            return "⚠️ Không có phản hồi từ mô hình."

        reply = response.choices[0].message.content.strip()
        logger.info("✅ Model trả về phản hồi hợp lệ.")
        return reply

    except Exception as e:
        logger.exception(f"❌ Lỗi khi gọi Azure OpenAI: {e}")
        return "⚠️ Lỗi khi xử lý yêu cầu từ mô hình."