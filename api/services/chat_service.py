from sentence_transformers import SentenceTransformer
from openai import AzureOpenAI, APIError, RateLimitError, APITimeoutError
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception_type
from api.config.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_ENDPOINT,
)
from api.services import chat_tts
from api.services.moderation_service import moderate_input
import chromadb
import logging

logger = logging.getLogger(__name__)

# ============================================================
# 🔧 Khởi tạo client Azure OpenAI
# ============================================================
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

# ============================================================
# 🧠 Khởi tạo model embedding (local)
# ============================================================
logger.info("🧠 Loading local embedding model (all-MiniLM-L6-v2)...")
embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
logger.info("✅ Embedding model loaded successfully.")

# ============================================================
# 💾 Kết nối ChromaDB
# ============================================================
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="chat_memory")

# ============================================================
# 🔹 Tạo embedding vector
# ============================================================
def get_embedding(text: str):
    """Sinh embedding vector từ text."""
    return embedding_model.encode([text])[0].tolist()

# ============================================================
# 💾 Lưu hội thoại vào ChromaDB
# ============================================================
def save_to_chroma(session_id: str, user_message: str, assistant_reply: str):
    """
    Lưu hội thoại (user + assistant) vào ChromaDB để tạo trí nhớ dài hạn.
    """
    try:
        text = f"[{session_id}] User: {user_message}\nAssistant: {assistant_reply}"
        embedding = get_embedding(text)

        collection.add(
            documents=[text],
            embeddings=[embedding],
            ids=[f"{session_id}_{len(collection.get()['ids'])}"]
        )
        logger.info(f"🧠 Đã lưu hội thoại của session {session_id} vào ChromaDB.")
    except Exception as e:
        logger.error(f"❌ Lỗi khi lưu vào ChromaDB: {e}")

# ============================================================
# 🔍 Truy vấn trí nhớ liên quan
# ============================================================
def search_memory(session_id: str, query: str, top_k: int = 3):
    """
    Tìm các đoạn hội thoại tương tự nhất trong ChromaDB.
    """
    try:
        query_emb = get_embedding(query)
        results = collection.query(
            query_embeddings=[query_emb],
            n_results=top_k,
        )
        if results.get("documents"):
            docs = [doc for docs in results["documents"] for doc in docs]
            return "\n".join(docs)
        return ""
    except Exception as e:
        logger.error(f"❌ Lỗi khi truy vấn ChromaDB: {e}")
        return ""

# ============================================================
# ⚙️ Gọi Azure OpenAI (có retry)
# ============================================================
@retry(
    retry=retry_if_exception_type((RateLimitError, APIError, APITimeoutError)),
    wait=wait_random_exponential(min=1, max=30),
    stop=stop_after_attempt(3)
)
def _call_azure_openai(messages: list, tts: bool = False, id: str = ""):
    """Internal helper — gọi API Azure OpenAI."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
        max_tokens=800,
        timeout=30,
    )

    if tts:
        chat_tts.save_audio_to_file(response.choices[0].message.content, "api/artifacts/audio/" + id + ".wav");

    return response

# ============================================================
# 🧾 Hàm chính: Gọi GPT + sử dụng Chroma memory
# ============================================================

def generate_summary(messages: list, user_input: str = None, memory_context: str = None, tts: bool = False, ss_id: str = "") -> str:
    """
    Gọi Azure OpenAI và trả về chuỗi text.
    Ghép thêm phần memory_context nếu có.
    """
    try:
        user_message = user_input or messages[-1]["content"]

        if memory_context:
            user_message += f"\n\nDưới đây là thông tin liên quan từ trí nhớ trước đó:\n{memory_context}\n"

        temp_messages = messages.copy()
        temp_messages[-1]["content"] = user_message

        # if not moderate_input(user_message):
        #     return "🚫 Nội dung bị từ chối — vui lòng không gửi dữ liệu nhạy cảm."

        response = _call_azure_openai(messages, tts, ss_id)

        if not response or not response.choices:
            return "⚠️ Không có phản hồi từ mô hình."

        raw_output = response.choices[0].message.content.strip()
        logger.info("✅ Model trả về output.")
        return raw_output

    except Exception as e:
        logger.exception("❌ Lỗi khi gọi Azure OpenAI: %s", e)
        return "⚠️ Lỗi khi gọi Azure OpenAI."