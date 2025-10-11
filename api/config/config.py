import os
from dotenv import load_dotenv

# Load environment variables (đặt đúng đường dẫn tới .env)
load_dotenv()

def get_env_variable(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing environment variable: {name}")
    return value

# Biến cấu hình toàn cục
AZURE_OPENAI_ENDPOINT = get_env_variable("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = get_env_variable("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = get_env_variable("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_DEPLOYMENT = get_env_variable("AZURE_OPENAI_DEPLOYMENT")

PROMPT_PATH = "prompt/prompt-guidelines.md"
LOG_DIR = "api/artifacts/conversation_log"