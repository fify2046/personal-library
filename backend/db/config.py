import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Config:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "ebook_db")
    DB_USER = os.getenv("DB_USER", "ebook")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "asdfgh")
    IMAGES_DIR = os.getenv("IMAGES_DIR", str(BASE_DIR.parent / "images"))
    
    @property
    def DATABASE_URL(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

config = Config()
