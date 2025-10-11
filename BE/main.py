import app
import uvicorn
import fastapi
import fastapi.responses
from fastapi import FastAPI,HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import logging
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from BE.config import settings
from BE.openai_client import call_chat_completion, call_batch
from BE.rate_limiter import check_rate_limit_dependency
from BE.session_store import get_session, update_session, list_sessions

# Create the FastAPI app instance
app = FastAPI()
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain like ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods including OPTIONS, POST, GET, etc.
    allow_headers=["*"],  # Allows all headers
)
class ChatRequest(BaseModel):
    session_id: str
    message: str


class BatchRequest(BaseModel):
    session_id: str
    prompts: List[str]


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return fastapi.responses.JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # avoid leaking internal details
    return fastapi.responses.JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Dependency to rate limit by session id or client ip
async def rate_limit_dep(request: Request):
    key = request.headers.get("X-Session-Id") or request.client.host
    await check_rate_limit_dependency(key)


@app.post("/chat")
async def chat(req: ChatRequest, _: None = Depends(rate_limit_dep)):
    logger.info(f"Received chat request: session_id={req.session_id}, message={req.message}")

    try:
        # load session
        logger.info(f"Loading session: {req.session_id}")
        session = await get_session(req.session_id)
        messages = session.get("messages", [])
        logger.info(f"Loaded {len(messages)} existing messages")

        # append user message
        messages.append({"role": "user", "content": req.message})
        logger.info(f"Calling OpenAI with {len(messages)} messages")

        # call
        resp = await call_chat_completion(messages)
        logger.info(f"Received response from OpenAI: {resp}")

        # try extract assistant text
        try:
            assistant_text = resp.choices[0].message.content
        except Exception as e:
            logger.error(f"Error extracting assistant text: {e}")
            assistant_text = str(resp)

        logger.info(f"Assistant reply: {assistant_text}")

        # append assistant message and persist
        messages.append({"role": "assistant", "content": assistant_text})
        session["messages"] = messages
        await update_session(req.session_id, session)

        return {"reply": assistant_text}

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch_chat")
async def batch_chat(req: BatchRequest, _: None = Depends(rate_limit_dep)):
    # for batch calls we keep context but generally use system prompt + user prompts
    results = await call_batch(req.prompts, concurrency=settings.BATCH_CONCURRENCY)

    # Optionally append each prompt+response to session
    session = await get_session(req.session_id)
    for r in results:
        if "response" in r:
            session.setdefault("messages", []).append(
                {"role": "user", "content": r["prompt"]}
            )
            session.setdefault("messages", []).append(
                {"role": "assistant", "content": r["response"]}
            )
        else:
            session.setdefault("messages", []).append(
                {"role": "user", "content": r["prompt"]}
            )
            session.setdefault("messages", []).append(
                {
                    "role": "assistant",
                    "content": "<error> " + r.get("error", "unknown"),
                }
            )

    await update_session(req.session_id, session)

    return {"results": results}


@app.get("/sessions")
async def sessions_list():
    return {"sessions": await list_sessions()}


@app.get("/session/{session_id}")
async def get_session_api(session_id: str):
    return await get_session(session_id)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
