# from fastapi import APIRouter
# from pydantic import BaseModel
# from api.services.chat_service import generate_summary
# from api.utils.session_manager import create_session_id
# from api.utils.conversation_logger import save_message_to_db
# from api.utils.prompt_loader import load_system_prompt

# router = APIRouter()

# # Lưu toàn bộ message cho mỗi session
# sessions_messages = {}

# # ✅ Khai báo Request body model để Swagger hiển thị
# class BatchRequest(BaseModel):
#     messages: list[str]
#     session_id: str | None = None


# @router.post("/api/chat/batch")
# async def chat_batch_endpoint(request: BatchRequest):
#     """
#     Xử lý nhiều message trong 1 request.
#     Dạng input ví dụ:
#     {
#         "messages": ["Xin chào", "Tóm tắt giúp tôi nội dung meeting", "Viết lại ngắn gọn"],
#         "session_id": null
#     }
#     """
#     session_id = request.session_id or create_session_id()

#     # Nếu session chưa tồn tại → tạo mới
#     if session_id not in sessions_messages:
#         system_prompt = load_system_prompt()
#         sessions_messages[session_id] = [{"role": "system", "content": system_prompt}]

#     replies = []
#     for msg in request.messages:
#         sessions_messages[session_id].append({"role": "user", "content": msg})
#         save_message_to_log(session_id, "user", msg)
#         reply = generate_summary(sessions_messages[session_id])
#         sessions_messages[session_id].append({"role": "assistant", "content": reply})
#         save_message_to_log(session_id, "assistant", reply)
#         replies.append(reply)

#     return {"session_id": session_id, "replies": replies, "message_count": len(replies)}
