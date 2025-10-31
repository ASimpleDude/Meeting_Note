# ============================================================
# 📁 api/services/memory_service.py
# ============================================================
import logging
import numpy as np
import re

from api.services.embedding_service import get_embedding, safe_get_embedding, cosine_similarity, reranker
from api.services.chroma_client import get_chroma_collection
from api.services.langchain_client import get_vector_store

logger = logging.getLogger(__name__)

# Chroma collection (local)
collection = get_chroma_collection()

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
# Save to Chroma
# ============================================================
def save_to_chroma(session_id: str, user_message: str, assistant_reply: str):
    """
    Thêm 1 document vào Chroma collection (document chứa user+assistant).
    """
    text = _make_qa_text(session_id, user_message, assistant_reply)
    embedding = get_embedding(text)
    if embedding is None:
        logger.warning("Embedding is None, skip saving to Chroma.")
        return

    all_ids = collection.get().get("ids", [])
    next_id = f"{session_id}_{len(all_ids)}"
    collection.add(
        documents=[text],
        embeddings=[embedding],
        metadatas=[{"session_id": session_id}],
        ids=[next_id],
    )
    logger.info(f"Saved to Chroma id={next_id}")


# ============================================================
# Save to Pinecone (via LangChain vector_store)
# ============================================================
def save_to_pinecone(session_id: str, user_message: str, assistant_reply: str):
    """
    Dùng vector_store.add_texts(...) của LangChain Pinecone adapter.
    Nó sẽ dùng embedding wrapper đã config trong langchain_client.
    """
    text = f"User: {user_message}\nAssistant: {assistant_reply}"
    try:
        vector_store.add_texts(
            texts=[text],
            metadatas=[{"session_id": session_id}],
            ids=[f"{session_id}-{np.random.randint(1_000_000)}"],
        )
        logger.info("Saved to Pinecone via LangChain vector_store.")
    except Exception as e:
        logger.error(f"Failed to save to Pinecone: {e}")


# ============================================================
# Search in Chroma
# ============================================================
def search_memory_chroma(session_id: str, query: str, top_k: int = 3, threshold: float = 0.7, return_score=False):
    """
    Tìm trong Chroma:
    - trả về answer nếu tương tự >= threshold (so sánh query->user_question)
    - ngược lại trả "" hoặc ("" ,score)
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
    except Exception as e:
        logger.warning(f"Chroma query failed: {e}")
        return ("", 0.0) if return_score else ""

    candidate_docs = results.get("documents", [[]])[0]
    if not candidate_docs:
        return ("", 0.0) if return_score else ""

    best_doc = ""
    best_score = 0.0

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
            best_doc = ai_ans if sim >= 0.9 else doc

    if best_score >= threshold:
        return (best_doc, float(best_score)) if return_score else best_doc
    return ("", float(best_score)) if return_score else ""


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
        docs = retriever.get_relevant_documents(query)
    except Exception as e:
        logger.error(f"Pinecone search failed: {e}")
        return ("", 0.0)

    # Nếu không có docs
    if not docs:
        return ("", 0.0)

    # optional: compute rough scores using embedding cosine between query and doc-question
    # but here we trust retriever order; we'll compute a coarse similarity using embeddings
    query_emb = safe_get_embedding(query)
    best_score = 0.0
    best_doc_text = ""

    for d in docs:
        # try to extract user question from doc
        doc_text = d.page_content
        user_q, ai_ans = extract_qa_from_doc(doc_text)
        if user_q:
            user_q_emb = safe_get_embedding(user_q)
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
