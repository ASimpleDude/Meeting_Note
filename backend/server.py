# ============================================================
# 📘 Meeting Notes Summarizer - FastAPI + Azure OpenAI
# ============================================================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import AzureOpenAI
from dotenv import load_dotenv
import os

# ============================================================
# 1️⃣ Load environment variables
# ============================================================
load_dotenv()

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_API_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# Initialize Azure OpenAI client
client = AzureOpenAI(
    api_key=api_key,
    api_version=api_version,
    azure_endpoint=endpoint
)

# ============================================================
# 2️⃣ Load system prompt from Markdown file
# ============================================================
def load_system_prompt(md_path: str = "prompt-guidelines.md") -> str:
    """Đọc nội dung từ file Markdown làm system prompt."""
    if os.path.exists(md_path):
        with open(md_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        return "You are a helpful assistant specializing in meeting note summarization."

system_prompt = load_system_prompt()

# ============================================================
# 3️⃣ FastAPI setup
# ============================================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép mọi domain (hoặc giới hạn theo thực tế)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 4️⃣ Data model
# ============================================================
class ChatRequest(BaseModel):
    message: str

# ============================================================
# 5️⃣ In-memory message store
# ============================================================
messages = [
    {
        "role": "system",
        "content": system_prompt
    }
]

# ============================================================
# 6️⃣ Chat endpoint
# ============================================================
@app.post("/chat")
def chat(request: ChatRequest):
    """API chính — nhận input từ người dùng và trả về tóm tắt meeting notes."""
    messages.append({"role": "user", "content": request.message})

    response = client.chat.completions.create(
        model=deployment,
        messages=messages,
    )

    reply = response.choices[0].message.content
    messages.append({"role": "assistant", "content": reply})

    return {"reply": reply}
