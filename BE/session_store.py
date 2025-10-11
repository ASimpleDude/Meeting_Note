import json
import asyncio
from typing import Dict, Any
from pathlib import Path
from .config import settings

_lock = asyncio.Lock()
_sessions: Dict[str, Dict[str, Any]] = {}

SESSIONS_PATH = Path(settings.SESSIONS_FILE)

async def load_sessions_from_disk():
    global _sessions
    if SESSIONS_PATH.exists():
        try:
            data = json.loads(SESSIONS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                _sessions = data
        except Exception:
            # if corrupted, ignore
            _sessions = {}

async def save_sessions_to_disk():
    async with _lock:
        SESSIONS_PATH.write_text(json.dumps(_sessions, ensure_ascii=False, indent=2), encoding="utf-8")

async def get_session(session_id: str) -> Dict[str, Any]:
    # returns a session dict (create if missing)
    async with _lock:
        if session_id not in _sessions:
            _sessions[session_id] = {"messages": []}
            await save_sessions_to_disk()
        return _sessions[session_id]

async def update_session(session_id: str, session_data: Dict[str, Any]):
    async with _lock:
        _sessions[session_id] = session_data
        await save_sessions_to_disk()

async def list_sessions():
    async with _lock:
        return list(_sessions.keys())

# On import we don't block the loop; caller should call load_sessions_from_disk() on startup.