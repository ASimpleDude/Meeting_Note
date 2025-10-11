import os
from api.config.config import PROMPT_PATH

def load_system_prompt(md_path: str = PROMPT_PATH) -> str:
    """Đọc file system prompt từ Markdown."""
    if os.path.exists(md_path):
        with open(md_path, "r", encoding="utf-8") as f:
            return f.read()

    return "You are a helpful assistant specializing in meeting note summarization."
