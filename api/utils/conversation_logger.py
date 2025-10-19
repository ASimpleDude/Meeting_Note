import sqlite3
import os
from api.services.chroma_client import get_chroma_collection

DB_PATH = "conversation.db"

def init_db(db_path=DB_PATH):
    if not os.path.exists(db_path):
        print(f"📂 Database not found, creating {db_path}...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS conversation_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        audio_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

# ✅ Kiểm tra ngay khi import module
init_db()

def save_message_to_db(session_id: str, role: str, content: str, audio_path: str = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversation_history (session_id, role, content, audio_path) VALUES (?, ?, ?, ?)",
        (session_id, role, content, audio_path)
    )
    conn.commit()
    conn.close()

def get_all_sessions():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT session_id, MIN(created_at) as created_at
        FROM conversation_history
        GROUP BY session_id
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def get_session_messages(session_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT role, content, audio_path, created_at
        FROM conversation_history
        WHERE session_id=?
        ORDER BY created_at ASC
    """, (session_id,))
    rows = cur.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1], "audio_path": r[2], "created_at": r[3]} for r in rows]

def delete_session_messages(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM conversation_history WHERE session_id=?", (session_id,))
    conn.commit()
    conn.close()

def delete_chroma_messages(session_id: str):
    """
    Xóa toàn bộ messages của session_id trong ChromaDB
    """
    collection = get_chroma_collection()
    # Xóa tất cả vector liên quan đến session_id
    collection.delete(where={"session_id": session_id})