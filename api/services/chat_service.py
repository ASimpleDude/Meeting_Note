from openai import AzureOpenAI, APIError, RateLimitError, APITimeoutError
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception_type
from api.config.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_DEPLOYMENT,
)
from api.services import chat_tts
from api.services.moderation_service import moderate_input
import logging

logger = logging.getLogger(__name__)

# ============================================================
# 🔧 Khởi tạo client
# ============================================================
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

# ============================================================
# 🧠 Hàm gọi Azure OpenAI có retry
# ============================================================
@retry(
    retry=retry_if_exception_type((RateLimitError, APIError, APITimeoutError)),
    wait=wait_random_exponential(min=1, max=30),
    stop=stop_after_attempt(3)
)
def _call_azure_openai(messages: list, tts: bool = False, id: str = ""):
    """Internal helper — gọi API Azure OpenAI."""
    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=messages,
        temperature=0.2,
        max_tokens=600,
    )

    if tts:
        chat_tts.save_audio_to_file(response.choices[0].message.content, "api/artifacts/audio/" + id + ".wav");
    return response

# ============================================================
# 🧾 Hàm chính
# ============================================================
def generate_summary(messages: list, tts: bool = False, ss_id: str = "") -> str:
    """Gọi Azure OpenAI chat model và trả về raw string."""
    user_message = messages[-1]["content"]

    # # 1️⃣ Kiểm duyệt nội dung (bật lại khi cần)
    # if not moderate_input(user_message):
    #     return "🚫 Nội dung bị từ chối — vui lòng không gửi dữ liệu nhạy cảm."

    try:
        response = _call_azure_openai(messages, tts, ss_id)

        if not response or not response.choices:
            return "⚠️ Không có phản hồi từ mô hình."

        raw_output = response.choices[0].message.content.strip()
        logger.info("✅ Model trả về raw string output")

        return raw_output  # 🔹 Trả thẳng chuỗi text

    except Exception as e:
        logger.exception("❌ Lỗi khi xử lý request: %s", e)
        return "⚠️ Lỗi khi gọi Azure OpenAI."
