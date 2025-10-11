import asyncio
from typing import List, Dict, Any
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from openai import OpenAI, OpenAIError
from .config import settings

# Create a shared OpenAI client configured for Azure
client = OpenAI(
    api_key=settings.AZURE_OPENAI_API_KEY,
    base_url=settings.AZURE_OPENAI_ENDPOINT,
    # api_type="azure",
    # api_version=settings.AZURE_OPENAI_API_VERSION,
)

# Retry config: exponential backoff, stop after 5 attempts
def retry_on_openai_error(e: Exception) -> bool:
    return isinstance(e, OpenAIError) or isinstance(e, asyncio.TimeoutError)

@retry(
    reraise=True,
    wait=wait_exponential(min=1, max=10),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type((OpenAIError, asyncio.TimeoutError)),
)
async def call_chat_completion(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Call Azure OpenAI chat completion with retries. Returns result dict."""

    messages = [{"role": m["role"], "content": m["content"]} for m in messages]
    # The v1-compatible openai client exposes an async method like client.chat.completions.create
    # Implementation depends on `openai` lib version. We attempt an async call; adjust if necessary.
    resp = await client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        messages=messages,
        max_tokens=512,
    )
    # The response shape may vary; adapt as needed
    return resp

async def call_batch(prompts: List[str], system_prompt: str = "You are a helpful assistant", concurrency: int = 4):
    sem = asyncio.Semaphore(concurrency)

    async def _worker(prompt: str):
        async with sem:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
            try:
                result = await call_chat_completion(messages)
                # extract text safely
                text = None
                try:
                    text = result.choices[0].message.content
                except Exception:
                    text = str(result)
                return {"prompt": prompt, "response": text}
            except Exception as e:
                return {"prompt": prompt, "error": str(e)}

    tasks = [asyncio.create_task(_worker(p)) for p in prompts]
    return await asyncio.gather(*tasks)