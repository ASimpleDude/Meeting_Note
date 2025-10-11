from fastapi import APIRouter, Request
from api.utils.session_manager import create_session_id
from api.utils.conversation_logger import save_message_to_log
from api.services.chat_service import generate_summary
from api.utils.prompt_loader import load_system_prompt

router = APIRouter()

# Lưu toàn bộ message cho mỗi session
sessions_messages = {}

@router.post("/api/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    print(data)
    user_input = data.get("message")
    
    # Lấy session_id từ client, nếu undefined hoặc None thì tạo mới
    session_id = data.get("session_id")
    if not session_id or session_id == "undefined":
        session_id = create_session_id()
    
    # Khởi tạo session nếu chưa có
    if session_id not in sessions_messages:
        system_prompt = load_system_prompt()  # 🔹 load system prompt
        sessions_messages[session_id] = [
            {"role": "system", "content": system_prompt}
        ]

    # Append message user
    sessions_messages[session_id].append({"role": "user", "content": user_input})
    save_message_to_log(session_id, "user", user_input)

    # Gọi model
    reply = generate_summary(sessions_messages[session_id])
    
    # Append message assistant
    sessions_messages[session_id].append({"role": "assistant", "content": reply})
    save_message_to_log(session_id, "assistant", reply)

    # Trả lại session_id cho client để lưu
    return {"session_id": session_id, "reply": reply}

