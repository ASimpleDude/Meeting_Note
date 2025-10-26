from fastapi import APIRouter, Request
from api.utils.session_manager import create_session_id
from api.utils.conversation_logger import save_message_to_db, get_all_sessions, get_session_messages, delete_chroma_messages, delete_session_messages
from api.utils.prompt_loader import load_system_prompt
from api.services.embedding_service import (
    save_to_chroma,
    search_memory_chroma,
    search_memory_pinecone, save_to_pinecone
)
from api.services.chat_service import (
    generate_summary
)
from api.services.chat_tts import generate_tts_audio
# =========================
# FastAPI router
# =========================
router = APIRouter()
sessions_messages = {}

@router.post("/api/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    user_input = data.get("message")
    tts = data.get("tts", False)
    session_id = data.get("session_id")

    # Tạo session mới nếu chưa có
    if not session_id or session_id == "undefined":
        session_id = create_session_id()

    # Thêm system prompt nếu session mới
    if session_id not in sessions_messages:
        system_prompt = load_system_prompt()
        sessions_messages[session_id] = [{"role": "system", "content": system_prompt}]

    # Lưu tin nhắn user
    sessions_messages[session_id].append({"role": "user", "content": user_input})
    save_message_to_db(session_id, "user", user_input, "")

    # Tìm trong ChromaDB
    # memory_context, best_score = search_memory_chroma(session_id, user_input, return_score=True)
    # Tìm trong Pinecone
    memory_context, best_score = search_memory_pinecone(session_id, user_input)


    if best_score >= 0.7:
        # Trùng → dùng lại câu trả lời cũ
        print("Use DB:")
        print(f"Best score: {best_score:.3f}")
        reply = memory_context.split("Assistant:")[-1].strip()
    else:
        # Không trùng → gọi model
        print("User AI:")
        print(f"Best score: {best_score:.3f}")
        reply = generate_summary(
            messages=sessions_messages[session_id],
            user_input=user_input,
            memory_context=memory_context
        )
    audio_path = generate_tts_audio(session_id, reply) if tts else None    

    # Lưu phản hồi
    sessions_messages[session_id].append({
        "role": "assistant",
        "content": reply,
        "audio_path": audio_path
    })
    save_message_to_db(session_id, "assistant", reply, audio_path or "")

    # Lưu vào ChromaDB
    # save_to_chroma(session_id, user_input, reply)
    # Lưu vào Pinecone
    save_to_pinecone(session_id, user_input, reply)

    return {"session_id": session_id, "reply": reply, "audio_path": audio_path}


# =========================
# Lấy danh sách session
# =========================
@router.get("/api/sessions")
def list_sessions():
    sessions_dict = get_all_sessions()  # {session_id: created_at}
    sessions = [{"id": k, "name": v} for k, v in sessions_dict.items()]
    return sessions


# =========================
# Lấy messages của 1 session
# =========================
@router.get("/api/chat/{session_id}")
async def get_chat(session_id: str):
    messages = get_session_messages(session_id)
    return messages


# =========================
# Xóa toàn bộ messages của 1 session
# =========================
@router.delete("/api/chat/{session_id}")
async def delete_chat(session_id: str):
    delete_chroma_messages(session_id)
    delete_session_messages(session_id)
    if session_id in sessions_messages:
        del sessions_messages[session_id]
    return {"status": "ok"}
