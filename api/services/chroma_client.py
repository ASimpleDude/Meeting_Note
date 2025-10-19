from chromadb import Client
from chromadb.config import Settings

# ⚠️ Khởi tạo 1 lần duy nhất
chroma_client = Client(Settings(
    persist_directory="./chroma_db"
))

def get_chroma_collection(name="chat_collection"):
    try:
        return chroma_client.get_collection(name=name)
    except:
        return chroma_client.create_collection(name=name)
