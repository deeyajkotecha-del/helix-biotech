"""Application configuration."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / os.getenv("UPLOAD_DIR", "uploads")

# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./helix.db"  # Default to SQLite for local development
)

# Handle Railway's postgres:// vs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# JWT Settings
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours

# File upload settings
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "52428800"))  # 50MB
ALLOWED_EXTENSIONS = {
    "excel": [".xlsx", ".xls", ".csv"],
    "presentation": [".pptx", ".ppt", ".pdf"],
    "article": [".pdf", ".docx", ".doc", ".txt", ".md"],
}

# Ensure upload directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "reports").mkdir(exist_ok=True)
(UPLOAD_DIR / "articles").mkdir(exist_ok=True)
(UPLOAD_DIR / "presentations").mkdir(exist_ok=True)
(UPLOAD_DIR / "sources").mkdir(exist_ok=True)
