Install packages:
pip install python-dotenv
pip install fastapi uvicorn openai



Run app:
uvicorn backend.server:app --reload --port 8000

Tạo file .env theo template sau ở folder gốc Meeting_Note:
AZURE_OPENAI_ENDPOINT=https://aiportalapi.stu-platform.live/jpe
AZURE_OPENAI_API_KEY= tự đút key vào đây
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_DEPLOYMENT=GPT-4o-mini

