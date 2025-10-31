# ============================================================
# 📁 api/services/memory_service.py
# ============================================================
import logging
import numpy as np
import re

from api.services.embedding_service import safe_get_embedding, cosine_similarity, reranker
from api.services.langchain_client import get_vector_store

logger = logging.getLogger(__name__)

# Pinecone vector_store (LangChain wrapper)
vector_store = get_vector_store()


# -------------------------
# Helpers for QA format
# -------------------------
def _make_qa_text(session_id: str, user: str, assistant: str):
    return f"[{session_id}] User: {user}\nAssistant: {assistant}"


def extract_qa_from_doc(doc: str):
    user_match = re.search(r"User:\s*(.+?)(?:\n|$)", doc, re.DOTALL)
    assistant_match = re.search(r"Assistant:\s*(.+)", doc, re.DOTALL)
    question = user_match.group(1).strip() if user_match else ""
    answer = assistant_match.group(1).strip() if assistant_match else ""
    return question, answer

# ============================================================
# Save to Pinecone (via LangChain vector_store)
# ============================================================
def save_to_pinecone(session_id: str, user_message: str, assistant_reply: str):
    text = f"User: {user_message}\nAssistant: {assistant_reply}"
    try:
        vector_store.add_texts(
            texts=[text],
            metadatas=[{"session_id": session_id}],
            ids=[f"{session_id}-{np.random.randint(1_000_000)}"],
        )
        logger.info("Saved to Pinecone via LangChain vector_store.")
        return True
    except Exception as e:
        logger.error(f"Failed to save to Pinecone: {e}")
        return False

# ============================================================
# Search in Pinecone
# ============================================================
def rerank_and_select(query, docs):
    """
    Dùng reranker để chọn đoạn tốt nhất (docs là list of Document)
    """
    if not docs:
        return ""
    try:
        pairs = [[query, d.page_content] for d in docs]
        scores = reranker.predict(pairs)
        best_idx = int(np.argmax(scores))
        _, answer = extract_qa_from_doc(docs[best_idx].page_content)
        return answer
    except Exception as e:
        logger.warning(f"Rerank failed: {e}")
        # fallback: trả doc đầu
        try:
            _, answer = extract_qa_from_doc(docs[0].page_content)
            return answer
        except Exception:
            return ""


def search_memory_pinecone(session_id: str, query: str, top_k: int = 3):
    """
    Tìm trong Pinecone qua LangChain retriever.
    Trả về (memory_text, score) ? hiện trả (memory_text, score) tương thích ai_chat usage.
    """
    try:
        retriever = vector_store.as_retriever(
            search_kwargs={"k": top_k, "filter": {"session_id": session_id}}
        )
        docs = retriever.invoke(query)
    except Exception as e:
        logger.error(f"Pinecone search failed: {e}")
        return ("", 0.0)

    # Nếu không có docs
    if not docs:
        return ("", 0.0)

    # optional: compute rough scores using embedding cosine between query and doc-question
    # but here we trust retriever order; we'll compute a coarse similarity using embeddings
    query_emb = safe_get_embedding(query, True)
    best_score = 0.0
    best_doc_text = ""

    for d in docs:
        # try to extract user question from doc
        doc_text = d.page_content
        user_q, ai_ans = extract_qa_from_doc(doc_text)
        if user_q:
            user_q_emb = safe_get_embedding(user_q, True)
            sim = cosine_similarity(query_emb, user_q_emb) if user_q_emb is not None else 0.0
        else:
            sim = 0.0

        if sim > best_score:
            best_score = sim
            best_doc_text = doc_text

    # If best_score is very low, still attempt rerank fallback
    if best_score < 0.1:
        selected_answer = rerank_and_select(query, docs)
        # try to approximate a fallback score
        return (selected_answer, float(best_score))
    else:
        return (best_doc_text, float(best_score))
