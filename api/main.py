from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.routes import ai_chat
from api.utils.conversation_logger import init_db
from contextlib import asynccontextmanager
import os

# =========================
# Tạo folder audio nếu chưa có
# =========================
AUDIO_DIR = "artifacts/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# =========================
# Lifespan
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Server starting, checking database...")
    init_db()  # init DB khi startup
    yield

# =========================
# Tạo app
# =========================
app = FastAPI(
    title="Meeting Notes Summarizer API",
    description="API tổng hợp và tóm tắt nội dung các buổi họp.",
    version="1.0.0",
    lifespan=lifespan
)

# =========================
# Middleware
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # cho phép frontend gọi
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Mount static folder audio
# =========================
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

# =========================
# Routes
# =========================
app.include_router(ai_chat.router)

# =========================
# Root endpoint
# =========================
@app.get("/")
def root():
    return {"message": "Meeting Notes Summarizer API is running 🚀"}
