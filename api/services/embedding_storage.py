# ============================================================
# 📁 api/services/embedding_storage.py
# ============================================================
import numpy as np
import re
import logging
from api.services.embedding_service import get_embedding, cosine_similarity, local_embedder, reranker
from api.services.chroma_client import get_chroma_collection
from api.services.langchain_client import get_vector_store

logger = logging.getLogger(__name__)

collection = get_chroma_collection()
vector_store = get_vector_store()


# ============================================================
# 💾 Lưu vào Chroma
# ============================================================
def save_to_chroma(session_id: str, user_message: str, assistant_reply: str):
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
# 💾 Lưu vào Pinecone
# ============================================================
def save_to_pinecone(session_id: str, user_message: str, assistant_reply: str):
    text = f"User: {user_message}\nAssistant: {assistant_reply}"

    vector_store.add_texts(
        texts=[text],
        metadatas=[{"session_id": session_id}],
        ids=[f"{session_id}-{np.random.randint(1_000_000)}"]
    )


# ============================================================
# 🔍 Tìm kiếm
# ============================================================
def extract_qa_from_doc(doc: str):
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


def search_memory_chroma(session_id: str, query: str, top_k: int = 3, threshold: float = 0.7, return_score=False):
    query_emb = get_embedding(query)
    if not query_emb:
        return ("", 0.0) if return_score else ""

    results = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k,
        where={"session_id": session_id},
        include=["documents"]
    )

    candidate_docs = results.get("documents", [[]])[0]
    if not candidate_docs:
        return ("", 0.0) if return_score else ""

    best_doc = ""
    best_score = 0.0

    for doc in candidate_docs:
        user_q, ai_ans = extract_qa_from_doc(doc)
        if not user_q or not ai_ans:
            continue

        user_q_emb = get_embedding(user_q)
        sim = cosine_similarity(query_emb, user_q_emb)

        if sim > best_score:
            best_score = sim
            best_doc = ai_ans if sim >= 0.9 else doc

    if best_score >= threshold:
        return (best_doc, best_score) if return_score else best_doc
    return ("", best_score) if return_score else ""


def search_memory_pinecone(session_id: str, query: str, top_k: int = 3):
    retriever = vector_store.as_retriever(
        search_kwargs={"k": top_k, "filter": {"session_id": session_id}}
    )
    docs = retriever.get_relevant_documents(query)
    return rerank_and_select(query, docs)
