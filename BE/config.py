from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    AZURE_OPENAI_API_KEY: str = "sk--RAeTDO4G2iEB3j3svvqPg"
    AZURE_OPENAI_ENDPOINT: str = "https://aiportalapi.stu-platform.live/jpe"
    AZURE_OPENAI_DEPLOYMENT: str = "GPT-4o-mini"
    AZURE_OPENAI_API_VERSION: str = "2024-08-01-preview"


    # session file
    SESSIONS_FILE: str = "sessions.json"


    # Batch concurrency
    BATCH_CONCURRENCY: int = 4


    # Rate limiter config
    RATE_LIMIT_TOKENS: int = 10
    RATE_LIMIT_REFILL_SECONDS: int = 60


    class Config:
        env_file = ".env"


settings = Settings()