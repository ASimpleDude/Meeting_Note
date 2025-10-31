# ============================================================
# 📁 api/services/langchain_client.py
# ============================================================
import os
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from api.config.config import PINECONE_API_KEY, PINECONE_INDEX_NAME
from api.services.embedding_service import local_embedder  # acceptable: langchain_client -> embedding_service

# Pinecone client (SDK v7+)
pc = Pinecone(api_key=PINECONE_API_KEY)

def ensure_index(name: str, dimension: int):
    existing = [i["name"] for i in pc.list_indexes()]
    if name not in existing:
        pc.create_index(
            name=name,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
    return pc.Index(name)

# auto-detect dim from local_embedder
try:
    DIM = getattr(local_embedder, "get_sentence_embedding_dimension", None)
    if callable(DIM):
        DIM = local_embedder.get_sentence_embedding_dimension()
    elif hasattr(local_embedder, "embed_dim"):
        DIM = local_embedder.embed_dim
    else:
        DIM = 384
    print(f"[LangChain Client] Detected embedding dimension: {DIM}")
except Exception:
    DIM = 384
    print(f"[LangChain Client Exception] Detected embedding dimension: {DIM}")

INDEX = ensure_index(PINECONE_INDEX_NAME, 1536)

# ✅ Wrapper class để tương thích với LangChain
class LangChainCompatibleEmbedder:
    def __init__(self, embedder):
        self.embedder = embedder

    def embed_documents(self, texts):
        return [self.embedder.encode(t, convert_to_numpy=True).tolist() for t in texts]

    def embed_query(self, text):
        return self.embedder.encode(text, convert_to_numpy=True).tolist()

def get_vector_store():
    """Return a LangChain-compatible PineconeVectorStore"""
    embedding = LangChainCompatibleEmbedder(local_embedder)
    return PineconeVectorStore(index=INDEX, embedding=embedding, text_key="text")
