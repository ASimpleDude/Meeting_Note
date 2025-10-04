from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import AzureOpenAI
from dotenv import load_dotenv
import os

# ==========================
# Load biến môi trường từ .env
# ==========================
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

# ==========================
# FastAPI app
# ==========================
app = FastAPI()

# Cho phép frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# Request model
# ==========================
class ChatRequest(BaseModel):
    message: str

# ==========================
# Lưu hội thoại (RAM)
# ==========================
messages = [
    {"role": "system", "content": "Bạn là một thư kí, nhiệm vụ của bạn là tóm tắt lại meeting notes và cùng ngôn ngữ với prompt được nhập vào. Nếu như câu hỏi không liên quan đến vệc meeting note thì từ chối trả lời nhé"}
]

# ==========================
# API endpoint
# ==========================
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
