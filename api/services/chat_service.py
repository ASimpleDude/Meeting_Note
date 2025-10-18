# ============================================================
# 📁 api/services/chat_service.py
# ============================================================
import logging
import numpy as np
import chromadb
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception_type
from openai import AzureOpenAI, APIError, RateLimitError, APITimeoutError
from sentence_transformers import SentenceTransformer, CrossEncoder

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
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="chat_memory")

# ============================================================
# 🔧 Embedding & Reranker Models (tải 1 lần, cache lại)
# ============================================================
embedder = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

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
def get_embedding(text: str):
    """Tạo vector embedding từ text bằng SentenceTransformer."""
    return embedder.encode(text, convert_to_numpy=True).tolist()

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
def search_memory(session_id: str, query: str, top_k: int = 5, threshold: float = 0.7):
    """Tìm kiếm nội dung liên quan trong cùng session bằng embedding + reranker."""
    query_emb = get_embedding(query)

    # 1️⃣ Vector Search (lấy sơ bộ)
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k,
        where={"session_id": session_id},
    )

    if not results or not results["documents"] or not results["documents"][0]:
        logger.info("🕳 Không có kết quả trong Chroma.")
        return ""

    candidate_docs = results["documents"][0]

    # 2️⃣ Rerank bằng CrossEncoder
    pairs = [[query, doc] for doc in candidate_docs]
    scores = reranker.predict(pairs)

    sorted_indices = np.argsort(scores)[::-1]
    best_doc = candidate_docs[sorted_indices[0]]
    best_score = scores[sorted_indices[0]]

    logger.info(f"🔎 Reranker top score: {best_score:.3f}")

    if best_score >= threshold:
        logger.info(f"✅ Found relevant memory (score={best_score:.3f})")
        return best_doc
    else:
        logger.info(f"⚠️ No confident match (score={best_score:.3f})")
        return ""

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
