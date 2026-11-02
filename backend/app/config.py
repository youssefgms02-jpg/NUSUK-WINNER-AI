from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./nusuk.db"
    cors_origins: str = "http://localhost:5173"
    ai_api_key: str = ""
    ai_base_url: str = ""
    ai_model: str = "gpt-4o-mini"
    tesseract_cmd: str = ""
    daily_process_limit: int = 100
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
