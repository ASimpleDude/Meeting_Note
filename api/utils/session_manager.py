import uuid
from datetime import datetime

def create_session_id() -> str:
    """Sinh session_id duy nhất cho mỗi cuộc hội thoại"""
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    return f"{timestamp}_session-{uuid.uuid4().hex[:6]}"
