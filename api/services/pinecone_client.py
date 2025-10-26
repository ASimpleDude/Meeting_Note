from pinecone import Pinecone, ServerlessSpec
from api.config.config import PINECONE_API_KEY, PINECONE_INDEX_NAME, PINECONE_ENV

pc = Pinecone(api_key=PINECONE_API_KEY)

# Tạo index nếu chưa tồn tại
if PINECONE_INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=384,  # đúng với MiniLM-L6-cos-v1
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

index = pc.Index(PINECONE_INDEX_NAME)

def get_index():
    return index
