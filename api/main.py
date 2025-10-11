from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import ai_chat

app = FastAPI(
    title="Meeting Notes Summarizer API",
    description="API tổng hợp và tóm tắt nội dung các buổi họp.",
    version="1.0.0",
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # cho phép frontend gọi
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(ai_chat.router)

@app.get("/")
def root():
    return {"message": "Meeting Notes Summarizer API is running 🚀"}
