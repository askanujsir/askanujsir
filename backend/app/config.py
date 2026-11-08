from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    DATABASE_URL: str = "sqlite:///./dev.db"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_MAX_TOKENS: int = 8192
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    JWT_SECRET_KEY: str = "dev-secret"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 720
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""
    FRONTEND_URL: str = "http://localhost:5173"
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    AUTO_CREATE_TABLES: bool = True
    STORAGE_PROVIDER: str = "local"
    STORAGE_LOCAL_DIR: str = "./storage"
    S3_ENDPOINT_URL: str = ""
    S3_BUCKET: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_REGION: str = "auto"
settings = Settings()
