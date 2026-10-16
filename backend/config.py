import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # --- Core ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "go-green-dev-secret-key-2026")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "go-green-jwt-dev-secret-key-2026")
    JWT_EXPIRES = timedelta(days=7)

    # --- Database (SQLite file, zero setup) ---
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'gogreen.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Uploads (report photos) ---
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB, matches frontend copy
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

    # --- CORS ---
    # Allow all local and browser origins in development
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

    # --- Rewards ---
    POINTS_PER_REPORT = 25
    POINTS_PER_SCHEDULE = 15

    # --- Google OAuth & Firebase ---
    # Google OAuth Web Client ID for Go Green
    GOOGLE_CLIENT_ID = os.environ.get(
        "GOOGLE_CLIENT_ID",
        "852086315506-6jg9dg6cimca2k8schtio570indb3m8d.apps.googleusercontent.com"
    )
    FIREBASE_API_KEY = os.environ.get(
        "FIREBASE_API_KEY",
        "AIzaSyBf_anVktii3PIbmk8RcDpTSHuOxXVrdX0"
    )
    FIREBASE_AUTH_DOMAIN = os.environ.get(
        "FIREBASE_AUTH_DOMAIN",
        "go-green-bc487.firebaseapp.com"
    )
    FIREBASE_PROJECT_ID = os.environ.get(
        "FIREBASE_PROJECT_ID",
        "go-green-bc487"
    )
    FIREBASE_STORAGE_BUCKET = os.environ.get(
        "FIREBASE_STORAGE_BUCKET",
        "go-green-bc487.firebasestorage.app"
    )
    FIREBASE_MESSAGING_SENDER_ID = os.environ.get(
        "FIREBASE_MESSAGING_SENDER_ID",
        "852086315506"
    )
    FIREBASE_APP_ID = os.environ.get(
        "FIREBASE_APP_ID",
        "1:852086315506:web:09e321eb5041cfbb70b36b"
    )

    # --- Municipal Authority Integration ---
    MUNICIPAL_NAME = os.environ.get("MUNICIPAL_NAME", "City Municipal Corporation — Urban Cleansing Authority")
    MUNICIPAL_API_URL = os.environ.get("MUNICIPAL_API_URL", "")
    MUNICIPAL_API_KEY = os.environ.get("MUNICIPAL_API_KEY", "")
    MUNICIPAL_FORWARDING_AUTO = os.environ.get("MUNICIPAL_FORWARDING_AUTO", "false").lower() in ("true", "1")


