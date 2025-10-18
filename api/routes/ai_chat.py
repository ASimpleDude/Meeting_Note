from fastapi import APIRouter, Request
from api.utils.session_manager import create_session_id
from api.utils.conversation_logger import save_message_to_log
from api.services.chat_service import generate_summary
from api.utils.prompt_loader import load_system_prompt
from api.services.chat_service import (
    generate_summary,
    get_embedding,
    save_to_chroma,
    search_memory,
)

router = APIRouter()

# Lưu toàn bộ message cho mỗi session
sessions_messages = {}

@router.post("/api/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    user_input = data.get("message")
    tts = data.get("tts", False)

    # Lấy session_id từ client, nếu undefined hoặc None thì tạo mới
    session_id = data.get("session_id")

    # ✅ Tạo session mới nếu chưa có
    if not session_id or session_id == "undefined":
        session_id = create_session_id()

    # ✅ Nếu session chưa có thì thêm system prompt
    if session_id not in sessions_messages:
        system_prompt = load_system_prompt()  # 🔹 load system prompt
        sessions_messages[session_id] = [
            {"role": "system", "content": system_prompt}
        ]

    # ✅ Lưu tin nhắn user
    sessions_messages[session_id].append({"role": "user", "content": user_input})
    save_message_to_log(session_id, "user", user_input)

    # 🔍 Tìm trí nhớ liên quan từ Chroma
    memory_context = search_memory(session_id, user_input)

    # Nếu trí nhớ có nội dung đủ rõ thì trả lời trực tiếp
    if memory_context and len(memory_context.strip()) > 5:  # >100 ký tự là gợi ý, bạn có thể điều chỉnh
        reply = f"Dựa trên thông tin trước đó, có vẻ như:\n{memory_context}"
        print("🧠 Trả lời dựa trên trí nhớ liên quan từ ChromaDB.")
    else:
        # 🔮 Nếu không đủ dữ kiện, mới gọi Azure OpenAI
        print("🤖 Gọi Azure OpenAI để sinh phản hồi...")
        reply = generate_summary(
            messages=sessions_messages[session_id],
            user_input=user_input,
            memory_context=memory_context,
            tts = tts,
            ss_id = session_id
        )

    # Lưu tin nhắn assistant
    sessions_messages[session_id].append({"role": "assistant", "content": reply})
    save_message_to_log(session_id, "assistant", reply)

    # Lưu hội thoại vào ChromaDB
    save_to_chroma(session_id, user_input, reply)

    return {"session_id": session_id, "reply": reply}

