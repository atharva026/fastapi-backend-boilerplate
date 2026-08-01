import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, Field
from typing import Optional

def get_env_file() -> str:
    env = os.getenv("ENVIRONMENT", "dev")   # default dev
    return f".env.{env}"

class DBConfig(BaseModel):
    db_name: str = Field(alias="DB_NAME")
    db_user: str = Field(alias="DB_USER")
    db_password: str = Field(alias="DB_PASSWORD")
    db_host: str = Field(alias="DB_HOST")
    db_port: int = Field(alias="DB_PORT")
    db_schema: Optional[str] = Field(default=None, alias="DB_SCHEMA")

    pool_size: int = Field(default=10, alias="POOL_SIZE")
    max_overflow: int = Field(default=4, alias="MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, alias="POOL_TIMEOUT")

    @property
    def db_url(self):
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def sync_db_url(self):
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

class EmailConfig(BaseModel):
    email_host: str = Field(alias="EMAIL_HOST")
    email_port: int = Field(alias="EMAIL_PORT")
    email_username: str = Field(alias="EMAIL_USERNAME")
    email_password: str = Field(alias="EMAIL_PASSWORD")
    email_from: str = Field(alias="EMAIL_FROM")

class RedisConfig(BaseModel):
    redis_host: str = Field(alias="REDIS_HOST")
    redis_port: int = Field(alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    
    redis_username: Optional[str] = Field(default=None, alias="REDIS_USERNAME")
    redis_password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")

    @property
    def redis_url(self):
        if self.redis_username and self.redis_password:
            return f"redis://{self.redis_username}:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        elif self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

class Settings(BaseSettings):
    """Application configuration settings."""
    
    ENVIRONMENT: str
    
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Logger
    DEBUG: bool
    LOG_TO_FILE: bool
    
    # Database
    DB_CONFIG: DBConfig

    # JWT & Token
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080 # 7 days
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    TOKEN_SERIALIZER_SECRET_KEY: str
    PASSWORD_RESET_SALT: str
    EMAIL_VERIFICATION_SALT: str
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 15
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 2
    
    # Email
    EMAIL_CONFIG: EmailConfig

    # Redis
    REDIS_CONFIG: RedisConfig

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"
    
    # CORS
    ALLOWED_ORIGINS: list = [
        "http://localhost",
        "http://localhost:3000",
    ]
    
    model_config = SettingsConfigDict(
        env_file=get_env_file(),
        env_nested_delimiter="__",
        case_sensitive=True,
    )
        
@lru_cache
def get_settings() -> Settings:
    return Settings()

config = get_settings()