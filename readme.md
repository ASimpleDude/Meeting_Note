## `README.md` (quick start)

```markdown
# FastAPI + Azure OpenAI Example

1. Create `.env` with:

```

AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=[https://your-resource.openai.azure.com](https://your-resource.openai.azure.com)
AZURE_OPENAI_DEPLOYMENT=your-deployment-name

````

2. Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirement.txt
````

3. Run:

```bash
uvicorn app.main:app --reload
```

4. Endpoints:

* POST `/chat` body `{ "session_id": "abc", "message": "Hello" }`
* POST `/batch_chat` body `{ "session_id": "abc", "prompts": ["A","B"] }`
* GET `/sessions` - list saved sessions
* GET `/session/{id}` - retrieve session (reads sessions.json on startup)

Notes:

* Rate limiter is in-memory (single-process). For production, use Redis-based limiter (e.g., `slowapi` or `fastapi-limiter`).
* Azure OpenAI client call shape may differ by SDK version; adapt `openai_client.py` to match your installed `openai` or `azure-ai-openai` API.
* Tenacity is already applied for reliable retries.

```