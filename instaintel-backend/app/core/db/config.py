from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/instaintel"

    JWT_SECRET: str = "CHANGE_THIS_SECRET"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    S3_BUCKET: str = "instaintel-datasets"
    S3_REGION: str = "us-east-1"

    REDIS_URL: str = "redis://localhost:6379/0"


settings = Settings()