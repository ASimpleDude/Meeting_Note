# ============================================================
# 📁 api/routes/ai_chat.py
# ============================================================
from fastapi import APIRouter, Request
from api.utils.session_manager import create_session_id
from api.utils.conversation_logger import (
    save_message_to_db,
    get_all_sessions,
    get_session_messages,
    delete_chroma_messages,
    delete_session_messages,
)
from api.utils.prompt_loader import load_system_prompt
from api.services.memory_service import (
    save_to_chroma,
    save_to_pinecone,
    search_memory_chroma,
    search_memory_pinecone,
)
from api.services.chat_service import generate_summary
from api.services.chat_tts import generate_tts_audio


# ============================================================
# 🚀 Router setup
# ============================================================
router = APIRouter()
sessions_messages = {}


# ============================================================
# 💬 Chat endpoint
# ============================================================
@router.post("/api/chat")
async def chat_endpoint(request: Request):
    """Xử lý hội thoại từ người dùng (kèm lưu trí nhớ & sinh TTS nếu cần)."""
    data = await request.json()
    user_input = data.get("message", "").strip()
    tts_enabled = data.get("tts", False)
    session_id = data.get("session_id") or create_session_id()

    # 🔹 Tạo session mới nếu chưa có
    if session_id not in sessions_messages:
        system_prompt = load_system_prompt()
        sessions_messages[session_id] = [{"role": "system", "content": system_prompt}]

    # 🔹 Lưu tin nhắn người dùng
    sessions_messages[session_id].append({"role": "user", "content": user_input})
    save_message_to_db(session_id, "user", user_input, "")

    # ============================================================
    # 🧠 Truy xuất trí nhớ từ Pinecone (ưu tiên) hoặc Chroma fallback
    # ============================================================
    memory_context, best_score = search_memory_pinecone(session_id, user_input)

    if best_score >= 0.7:
        # ✅ Nếu câu hỏi đã có trong trí nhớ
        print(f"[🔁] Reuse memory | score={best_score:.3f}")
        reply = memory_context.split("Assistant:")[-1].strip()
    else:
        # 🧩 Nếu chưa có, gọi model để sinh mới
        print(f"[💡] Generate AI reply | score={best_score:.3f}")
        reply = generate_summary(
            messages=sessions_messages[session_id],
            user_input=user_input,
            memory_context=memory_context,
        )

    # ============================================================
    # 🔊 Sinh âm thanh (nếu bật TTS)
    # ============================================================
    audio_path = generate_tts_audio(session_id, reply) if tts_enabled else None

    # ============================================================
    # 💾 Lưu phản hồi và hội thoại vào DB + Pinecone
    # ============================================================
    sessions_messages[session_id].append(
        {"role": "assistant", "content": reply, "audio_path": audio_path}
    )
    save_message_to_db(session_id, "assistant", reply, audio_path or "")
    save_to_pinecone(session_id, user_input, reply)

    return {"session_id": session_id, "reply": reply, "audio_path": audio_path}


# ============================================================
# 📚 Lấy danh sách session
# ============================================================
@router.get("/api/sessions")
def list_sessions():
    """Trả về danh sách các phiên hội thoại."""
    sessions_dict = get_all_sessions()
    return [{"id": sid, "name": name} for sid, name in sessions_dict.items()]


# ============================================================
# 🗂️ Lấy toàn bộ tin nhắn của một session
# ============================================================
@router.get("/api/chat/{session_id}")
def get_chat(session_id: str):
    """Lấy danh sách tin nhắn của một session cụ thể."""
    return get_session_messages(session_id)


# ============================================================
# 🗑️ Xóa toàn bộ tin nhắn của một session
# ============================================================
@router.delete("/api/chat/{session_id}")
def delete_chat(session_id: str):
    """Xóa sạch dữ liệu hội thoại và trí nhớ của một session."""
    delete_chroma_messages(session_id)
    delete_session_messages(session_id)
    sessions_messages.pop(session_id, None)
    return {"status": "ok"}
