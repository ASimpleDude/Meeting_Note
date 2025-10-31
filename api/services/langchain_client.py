# api/services/langchain_client.py
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
        pc.create_index(name=name, dimension=dimension, metric="cosine",
                        spec=ServerlessSpec(cloud="aws", region="us-east-1"))
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
except Exception:
    DIM = 384

INDEX = ensure_index(PINECONE_INDEX_NAME, DIM)
# simple wrapper embed function for langchain_pinecone
def _embed_fn(texts):
    return [local_embedder.encode(t, convert_to_numpy=True).tolist() for t in texts]

def get_vector_store():
    """Return a LangChain-compatible PineconeVectorStore"""
    return PineconeVectorStore(index=INDEX, embedding=_embed_fn, text_key="text")
