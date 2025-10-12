import json
import os
from datetime import datetime

LOG_DIR = "api/artifacts/conversation_log"

def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)

def save_message_to_log(session_id: str, role: str, content: str):
    """Lưu mỗi tin nhắn vào file JSONL"""
    ensure_log_dir()
    log_path = os.path.join(LOG_DIR, f"{session_id}.jsonl")
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "role": role,
        "content": content,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

def load_session_log(session_id: str):
    """Đọc lại log của 1 session"""
    log_path = os.path.join(LOG_DIR, f"{session_id}.jsonl")
    if not os.path.exists(log_path):
        return []
    with open(log_path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]
