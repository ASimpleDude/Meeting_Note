# Import các thư viện cần thiết
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import AzureOpenAI
from dotenv import load_dotenv
import os

# --------------------------------------------------------
# 1. Load biến môi trường từ file .env
# --------------------------------------------------------
# File .env chứa các thông tin nhạy cảm như API Key, Endpoint
# Ví dụ:
# AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
# AZURE_OPENAI_API_KEY=abc123
# AZURE_OPENAI_API_VERSION=2024-08-01-preview
# AZURE_OPENAI_DEPLOYMENT=GPT-4o-mini
load_dotenv()

# Lấy các biến môi trường đã load ra
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_API_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# --------------------------------------------------------
# 2. Khởi tạo client Azure OpenAI
# --------------------------------------------------------
# Client này dùng để gửi request tới Azure OpenAI
client = AzureOpenAI(
    api_key=api_key,              # API key từ Azure
    api_version=api_version,      # version API bạn dùng
    azure_endpoint=endpoint       # endpoint từ Azure Portal
)

# --------------------------------------------------------
# 3. Khởi tạo ứng dụng FastAPI
# --------------------------------------------------------
app = FastAPI()

# Thêm middleware CORS để cho phép Frontend (FE) gọi API
# Nếu không có, khi FE chạy từ localhost:3000 hoặc domain khác
# sẽ bị lỗi CORS policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Cho phép tất cả domain gọi (có thể giới hạn theo domain thực tế)
    allow_credentials=True,
    allow_methods=["*"],        # Cho phép mọi HTTP method: GET, POST, PUT, DELETE...
    allow_headers=["*"],        # Cho phép tất cả loại header
)

# --------------------------------------------------------
# 4. Định nghĩa schema dữ liệu request bằng Pydantic
# --------------------------------------------------------
# Khi người dùng gửi dữ liệu tới API (qua JSON),
# nó sẽ được parse thành object ChatRequest
class ChatRequest(BaseModel):
    message: str   # Client chỉ cần gửi 1 chuỗi message

# --------------------------------------------------------
# 5. API Endpoint chính
# --------------------------------------------------------
# Khi FE gọi POST /chat với body {"message": "Hello"},
# hàm chat() sẽ chạy, gọi Azure OpenAI và trả kết quả lại.
@app.post("/chat")
def chat(request: ChatRequest):
    # Gửi request tới Azure OpenAI, sử dụng mô hình bạn đã deploy
    response = client.chat.completions.create(
        model=deployment,  # ⚠️ Quan trọng: phải dùng deployment name đã tạo trong Azure
        messages=[
            {"role": "system", "content": "Bạn là chatbot AI thân thiện."},  # Lời nhắc hệ thống
            {"role": "user", "content": request.message}                      # Nội dung người dùng nhập
        ],
        max_tokens=200  # Giới hạn số token trả về để tránh trả quá dài
    )
    
    # Trả về JSON cho FE, chỉ lấy phần text của chatbot
    return {"reply": response.choices[0].message.content}
