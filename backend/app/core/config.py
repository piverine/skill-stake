from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Skill-Stake Learning Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    CLERK_SECRET_KEY: str = os.getenv("CLERK_SECRET_KEY", "")
    CLERK_JWKS_URL: str = os.getenv("CLERK_JWKS_URL", "https://api.clerk.dev/v1/jwks")
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # External APIs
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Blockchain
    ETHEREUM_RPC_URL: str = os.getenv("ETHEREUM_RPC_URL", "https://sepolia.infura.io/v3/your-key")
    CONTRACT_ADDRESS: str = os.getenv("CONTRACT_ADDRESS", "")
    PRIVATE_KEY: str = os.getenv("PRIVATE_KEY", "")
    
    class Config:
        env_file = ".env"

settings = Settings()