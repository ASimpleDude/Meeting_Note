# ============================================================
# 📁 api/services/chat_service.py
# ============================================================

import logging
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception_type
from openai import AzureOpenAI, APIError, RateLimitError, APITimeoutError
from api.config.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_ENDPOINT,
)


# ============================================================
# ⚙️ Cấu hình logging
# ============================================================
logger = logging.getLogger(__name__)


# ============================================================
# 🧠 Khởi tạo các client và model
# ============================================================
# Client Azure OpenAI (dùng để sinh phản hồi hội thoại)
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

# ============================================================
# 🔁 Hàm gọi Azure OpenAI (có retry tự động)
# ============================================================
@retry(
    retry=retry_if_exception_type((RateLimitError, APIError, APITimeoutError)),
    wait=wait_random_exponential(min=1, max=30),
    stop=stop_after_attempt(3),
)
def _call_azure_openai(messages: list):
    """
    Gửi yêu cầu đến Azure OpenAI để sinh phản hồi hội thoại.
    Có cơ chế retry khi bị lỗi tạm thời (RateLimit, Timeout, APIError).
    """
    logger.info("Gửi request đến Azure OpenAI...")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
        max_tokens=800,
        timeout=30,
    )
    logger.info("Nhận phản hồi thành công từ Azure OpenAI.")
    return response


# ============================================================
# 💬 Hàm chính: Sinh phản hồi hội thoại (kết hợp memory)
# ============================================================
def generate_summary(messages: list, user_input: str = None, memory_context: str = None) -> str:
    """
    Sinh phản hồi hội thoại từ Azure OpenAI.
    Nếu có 'memory_context' thì nối thêm vào prompt để cung cấp ngữ cảnh.
    """
    try:
        # ✅ Fallback an toàn nếu messages rỗng
        if not messages:
            messages = [{"role": "user", "content": user_input or ""}]

        user_message = user_input or messages[-1].get("content", "")

        # ✅ Bảo vệ memory_context kiểu dữ liệu
        if memory_context and isinstance(memory_context, str):
            user_message += f"\n\nThông tin liên quan từ các lần trao đổi trước:\n{memory_context.strip()}\n"

        temp_messages = messages.copy()
        temp_messages[-1]["content"] = user_message.strip()

        response = _call_azure_openai(temp_messages)

        if not response or not hasattr(response, "choices") or not response.choices:
            return "Không có phản hồi từ mô hình."

        reply = getattr(response.choices[0].message, "content", "").strip()
        if not reply:
            return "Mô hình không trả về nội dung hợp lệ."

        logger.info("✅ Model trả về phản hồi hợp lệ.")
        return reply

    except Exception as e:
        logger.exception(f"🔥 Lỗi khi gọi Azure OpenAI: {e}")
        return "Đã xảy ra lỗi khi xử lý yêu cầu từ mô hình."

