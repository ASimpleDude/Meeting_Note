from openai import OpenAI
import logging
import re
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder
from scipy.spatial.distance import cosine
from api.services.chroma_client import get_chroma_collection
from api.config.config import (
    AZURE_OPENAI_API_KEY
)
# Client OpenAI (sử dụng khi cần embedding từ API)
openai_client = OpenAI(api_key=AZURE_OPENAI_API_KEY)
from api.services.langchain_client import get_vector_store
vector_store = get_vector_store()


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
# 💾 Lưu hội thoại vào Pinecone
# ============================================================
def save_to_pinecone(session_id: str, user_message: str, assistant_reply: str):
    text = f"User: {user_message}\nAssistant: {assistant_reply}"

    vector_store.add_texts(
        texts=[text],
        metadatas=[{"session_id": session_id}],
        ids=[f"{session_id}-{np.random.randint(1_000_000)}"]
    )

# ============================================================
# 🔍 Hàm hỗ trợ tìm kiếm trong trí nhớ
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

def rerank_and_select(query, docs):
    if not docs:
        return ""

    pairs = [[query, doc.page_content] for doc in docs]
    scores = reranker.predict(pairs)

    best_idx = int(np.argmax(scores))
    _, answer = extract_qa_from_doc(docs[best_idx].page_content)
    return answer

def cosine_similarity(vec1, vec2):
    """Tính độ tương đồng cosine giữa hai vector."""
    if vec1 is None or vec2 is None:
        return 0.0
    vec1, vec2 = np.array(vec1), np.array(vec2)
    if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
        return 0.0
    return 1 - cosine(vec1, vec2)


def search_memory_chroma(session_id: str, query: str, top_k: int = 3, threshold: float = 0.7, return_score=False):
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


def search_memory_pinecone(session_id: str, query: str, top_k: int = 3):
    retriever = vector_store.as_retriever(
        search_kwargs={
            "k": top_k,
            "filter": {"session_id": session_id}
        }
    )

    docs = retriever.get_relevant_documents(query)

    return rerank_and_select(query, docs)