from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ESP32_API_KEY: str
    ENVIRONMENT: str = "production"
    SECURE_COOKIES: bool = True
    LOG_DIR: str = "/app/logs"
    DOMAIN: str = "localhost"

    class Config:
        env_file = ".env"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()
