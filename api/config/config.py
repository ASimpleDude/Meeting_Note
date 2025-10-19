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

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./db/chroma")
DATABASE_URL = os.getenv("DATABASE_URL", "./db/app_data.db")
SECRET_KEY = os.getenv("SECRET_KEY", "secretdev")
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "../artifacts")
AUDIO_DIR = os.path.abspath(os.path.join(ARTIFACTS_DIR, "audio"))