import json
import os
from datetime import datetime
from api.config.config import LOG_DIR


def log_conversation(role: str, content: str):
    """
    Ghi 1 dòng hội thoại (user hoặc assistant) vào file JSONL.
    File lưu theo ngày để dễ quản lý.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    log_path = os.path.join(LOG_DIR, f"{datetime.now():%Y-%m-%d}.jsonl")

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "role": role,
        "content": content
    }

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")