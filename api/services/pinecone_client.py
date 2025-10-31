# ============================================================
# 📁 api/services/pinecone_client.py
# ============================================================

from pinecone import ServerlessSpec

def get_index(pc, index_name: str):
    """Trả về Pinecone index, tạo mới nếu chưa có."""
    indexes = [i["name"] for i in pc.list_indexes()]
    if index_name not in indexes:
        pc.create_index(
            name=index_name,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
    return pc.Index(index_name)
