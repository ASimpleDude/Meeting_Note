from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import AzureOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_API_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

client = AzureOpenAI(
    api_key=api_key,
    api_version=api_version,
    azure_endpoint=endpoint
)

app = FastAPI()

# Cho phép frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

prompt = (
    "Bạn là một thư ký họp. Nhiệm vụ của bạn là tóm tắt lại meeting notes một cách ngắn gọn, "
    "xúc tích, và **phải ghi rõ nhiệm vụ hoặc hành động cụ thể của từng người tham dự nếu có**.\n\n"
    "Giữ nguyên ngôn ngữ đầu vào (nếu meeting note là tiếng Anh, trả lời bằng tiếng Anh; "
    "nếu là tiếng Việt, trả lời bằng tiếng Việt).\n\n"
    "Chỉ trả lời khi nội dung người dùng nhập là meeting notes.\n\n"
    "Nếu người dùng nhập câu hỏi hoặc nội dung không liên quan đến meeting notes, hãy từ chối trả lời và nói: "
    "“Xin lỗi, tôi chỉ có thể xử lý nội dung meeting notes.”"
)

messages = [
    {"role": "system", "content": prompt}
]

@app.post("/chat")
def chat(request: ChatRequest):
    messages.append({"role": "user", "content": request.message})

    response = client.chat.completions.create(
        model=deployment,
        messages=messages,
    )

    reply = response.choices[0].message.content
    messages.append({"role": "assistant", "content": reply})

    return {"reply": reply}
