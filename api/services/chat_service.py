# ============================================================
# 📁 api/services/chat_service.py
# ============================================================

import logging
import re
from collections import defaultdict

import chromadb
import numpy as np
from numpy.linalg import norm
from scipy.spatial.distance import cosine
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
# ⚙️ Cấu hình logging
# ============================================================
logger = logging.getLogger(__name__)


# ============================================================
# 🧠 Khởi tạo các client và model
# ============================================================
collection = get_chroma_collection()  # Kết nối đến ChromaDB

# Mô hình embedding cục bộ (nhẹ, miễn phí)
local_embedder = SentenceTransformer("sentence-transformers/multi-qa-MiniLM-L6-cos-v1")

# Mô hình reranker dùng cho fallback
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# Client OpenAI (sử dụng khi cần embedding từ API)
openai_client = OpenAI(api_key=AZURE_OPENAI_API_KEY)

# Client Azure OpenAI (dùng để sinh phản hồi hội thoại)
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)


# ============================================================
# 🔧 Hàm tiện ích: Sinh embedding an toàn
# ============================================================
def get_embedding(text: str, use_openai: bool = False):
    """
    Sinh vector embedding từ văn bản.

    - Nếu use_openai=True → sử dụng OpenAI API (text-embedding-3-small)
    - Ngược lại → sử dụng mô hình cục bộ (multi-qa-MiniLM-L6-cos-v1)
    """
    if use_openai:
        try:
            response = openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"Lỗi khi gọi OpenAI embedding API, fallback sang local: {e}")
            return local_embedder.encode(text, convert_to_numpy=True).tolist()
    else:
        return local_embedder.encode(text, convert_to_numpy=True).tolist()


def safe_get_embedding(query: str):
    """Hàm sinh embedding có xử lý ngoại lệ."""
    query = query.strip()
    if not query:
        return None
    try:
        return get_embedding(query)
    except Exception as e:
        logger.error(f"Lỗi khi sinh embedding: {e}")
        return None


# ============================================================
# 💾 Lưu hội thoại vào ChromaDB
# ============================================================
def save_to_chroma(session_id: str, user_message: str, assistant_reply: str):
    """
    Lưu một lượt hội thoại (user + assistant) vào ChromaDB.
    """
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
    logger.info(f"Đã lưu hội thoại vào Chroma (ID: {next_id})")


# ============================================================
# 🔍 Hàm hỗ trợ tìm kiếm trong trí nhớ (ChromaDB)
# ============================================================
def extract_qa_from_doc(doc: str):
    """
    Tách phần câu hỏi (User) và câu trả lời (Assistant) từ nội dung doc.
    Trả về tuple (question, answer).
    """
    user_match = re.search(r"User:\s*(.+?)(?:\n|$)", doc, re.DOTALL)
    assistant_match = re.search(r"Assistant:\s*(.+)", doc, re.DOTALL)

    question = user_match.group(1).strip() if user_match else ""
    answer = assistant_match.group(1).strip() if assistant_match else ""
    return question, answer


def cosine_similarity(vec1, vec2):
    """Tính độ tương đồng cosine giữa hai vector."""
    if vec1 is None or vec2 is None:
        return 0.0
    vec1, vec2 = np.array(vec1), np.array(vec2)
    if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
        return 0.0
    return 1 - cosine(vec1, vec2)


def search_memory(session_id: str, query: str, top_k: int = 3, threshold: float = 0.7, return_score=False):
    """
    Tìm kiếm trong trí nhớ hội thoại (ChromaDB).
    - Chỉ so sánh phần câu hỏi của User.
    - Nếu câu hỏi trùng khớp (score ≥ 0.9), lấy lại câu trả lời cũ của Assistant.
    - Nếu không, so sánh bằng cosine và trả về kết quả tốt nhất.
    """
    query_emb = safe_get_embedding(query)
    if not query_emb:
        return ("", 0.0) if return_score else ""

    try:
        results = collection.query(
            query_embeddings=[query_emb],
            n_results=top_k,
            where={"session_id": session_id},
            include=["documents"]
        )
    except ValueError:
        return ("", 0.0) if return_score else ""

    candidate_docs = results.get("documents", [[]])[0]
    if not candidate_docs:
        return ("", 0.0) if return_score else ""

    best_doc = ""
    best_score = 0.0

    # So sánh từng doc dựa trên câu hỏi của User
    for doc in candidate_docs:
        user_q, ai_ans = extract_qa_from_doc(doc)
        if not user_q or not ai_ans:
            continue

        user_q_emb = safe_get_embedding(user_q)
        if not user_q_emb:
            continue

        sim = cosine_similarity(query_emb, user_q_emb)

        if sim > best_score:
            best_score = sim
            best_doc = ai_ans if sim >= 0.9 else doc  # Nếu trùng cao, chỉ lấy câu trả lời

    if best_score >= threshold:
        return (best_doc, float(best_score)) if return_score else best_doc
    else:
        return ("", float(best_score)) if return_score else ""


# ============================================================
# 🔁 Hàm gọi Azure OpenAI (có retry tự động)
# ============================================================
@retry(
    retry=retry_if_exception_type((RateLimitError, APIError, APITimeoutError)),
    wait=wait_random_exponential(min=1, max=30),
    stop=stop_after_attempt(3),
)
def _call_azure_openai(messages: list):
    """
    Gửi yêu cầu đến Azure OpenAI để sinh phản hồi hội thoại.
    Có cơ chế retry khi bị lỗi tạm thời (RateLimit, Timeout, APIError).
    """
    logger.info("Gửi request đến Azure OpenAI...")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
        max_tokens=800,
        timeout=30,
    )
    logger.info("Nhận phản hồi thành công từ Azure OpenAI.")
    return response


# ============================================================
# 💬 Hàm chính: Sinh phản hồi hội thoại (kết hợp memory)
# ============================================================
def generate_summary(messages: list, user_input: str = None, memory_context: str = None) -> str:
    """
    Sinh phản hồi hội thoại từ Azure OpenAI.
    Nếu có 'memory_context' thì nối thêm vào prompt để cung cấp ngữ cảnh.
    """
    try:
        user_message = user_input or messages[-1]["content"]

        # Thêm phần trí nhớ trước đó nếu có
        if memory_context:
            user_message += f"\n\nThông tin liên quan từ các lần trao đổi trước:\n{memory_context}\n"

        temp_messages = messages.copy()
        temp_messages[-1]["content"] = user_message

        # (Tuỳ chọn) Kiểm duyệt nội dung người dùng
        # if not moderate_input(user_message):
        #     return "Nội dung bị từ chối — vui lòng không gửi dữ liệu nhạy cảm."

        response = _call_azure_openai(temp_messages)
        if not response or not response.choices:
            return "Không có phản hồi từ mô hình."

        reply = response.choices[0].message.content.strip()
        logger.info("Model trả về phản hồi hợp lệ.")
        return reply

    except Exception as e:
        logger.exception(f"Lỗi khi gọi Azure OpenAI: {e}")
        return "Đã xảy ra lỗi khi xử lý yêu cầu từ mô hình."
