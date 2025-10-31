Mọi logic đều rõ ràng theo layer:
    embedding_service → xử lý mô hình
    langchain_client → quản lý Pinecone store
    embedding_storage → lưu & tìm kiếm


===============================================================
ai_chat.py
🧩 1️⃣ Tổng quan

Mục tiêu file:
Tạo endpoint /api/chat để:

Nhận input người dùng.

Truy xuất memory (Pinecone → Chroma fallback).

Sinh phản hồi từ AI.

Ghi log + lưu DB + TTS nếu bật.

Cấu trúc này chuẩn clean architecture ✅
– routes → services → utils → DB
Không bị vòng import, dễ test.

===============================================================
