from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str  # no default, must come from environment

    JWT_SECRET: str = "CHANGE_THIS_SECRET"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    S3_BUCKET: str = "instaintel-datasets"
    S3_REGION: str = "us-east-1"

    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
