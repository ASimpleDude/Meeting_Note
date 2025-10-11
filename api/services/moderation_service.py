# ============================================================
# 📘 api/services/moderation_service.py
# ============================================================
from openai import AzureOpenAI
from api.config.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_ENDPOINT,
)
import logging

logger = logging.getLogger(__name__)

# Tạo client kiểm duyệt riêng
moderation_client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

def moderate_input(text: str) -> bool:
    return ""
