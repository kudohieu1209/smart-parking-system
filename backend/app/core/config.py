import os
from pydantic import BaseModel

class Settings(BaseModel):
    APP_NAME: str = os.getenv("APP_NAME", "Smart Parking System API")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    PORT: int = int(os.getenv("PORT", 8000))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")
    
    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "*"
    ]
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./parking.db")
    
    # Pricing
    HOURLY_RATE: int = int(os.getenv("HOURLY_RATE", 10000))  # 10,000 VND / hour
    MINIMUM_FEE: int = int(os.getenv("MINIMUM_FEE", 5000))   # 5,000 VND minimum
    
    # Distance threshold for ultrasonic sensor (cm)
    SENSOR_OCCUPIED_DISTANCE_CM: float = 30.0

settings = Settings()
