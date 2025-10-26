from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Pinecone as PineconeStore
from pinecone import Pinecone
from api.config.config import PINECONE_API_KEY
from api.services.pinecone_client import get_index

# Embedding: dùng local của bạn nếu muốn
embed_model = OpenAIEmbeddings(model="text-embedding-3-small")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = get_index()

# Kết nối LangChain với Pinecone index đã có
vector_store = PineconeStore(
    embedding=embed_model,
    index=index,
    text_key="text",
    namespace="chat-memory" # chia namespace, scale tốt hơn filter
)

def get_vector_store():
    return vector_store
