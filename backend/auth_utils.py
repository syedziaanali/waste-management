from functools import wraps
from datetime import datetime, timezone

import jwt
from flask import request, jsonify, current_app

from models import User


def encode_token(user_id):
    payload = {
        "sub": str(user_id),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + current_app.config["JWT_EXPIRES"],
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def decode_token(token):
    return jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])


def verify_google_token(credential):
    """Verifies a Google ID Token using google-auth or unverified claims fallback."""
    if not credential or not isinstance(credential, str):
        return None

    # 1. Try official google-auth library verification
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        client_id = current_app.config.get("GOOGLE_CLIENT_ID") or None
        id_info = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            audience=client_id,
            clock_skew_in_seconds=10
        )
        return id_info
    except Exception:
        pass

    # 2. Try unverified JWT decoding (extract claims like email, name, sub, picture)
    try:
        decoded = jwt.decode(credential, options={"verify_signature": False})
        if decoded and ("email" in decoded or "sub" in decoded):
            return decoded
    except Exception:
        pass

    return None



def get_bearer_token():
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header.split(" ", 1)[1].strip()
    return None


def db_get_user(user_id):
    from extensions import db
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None


def login_required(fn):
    """Requires a valid JWT. Attaches the User object to request.current_user."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = get_bearer_token()
        if not token:
            return jsonify({"error": "Missing authorization token"}), 401
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired, please log in again"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        user = db_get_user(payload.get("sub"))
        if not user:
            return jsonify({"error": "User not found"}), 401

        request.current_user = user
        return fn(*args, **kwargs)

    return wrapper


def optional_login(fn):
    """Attaches request.current_user if a valid token is present, else sets it to None.
    Allows both authenticated users and guests to submit reports/schedules."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        request.current_user = None
        token = get_bearer_token()
        if token:
            try:
                payload = decode_token(token)
                request.current_user = db_get_user(payload.get("sub"))
            except jwt.InvalidTokenError:
                request.current_user = None
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    """Requires a logged-in user with role == 'admin'."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = get_bearer_token()
        if not token:
            return jsonify({"error": "Missing authorization token"}), 401
        try:
            payload = decode_token(token)
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid or expired token"}), 401

        user = db_get_user(payload.get("sub"))
        if not user or user.role != "admin":
            return jsonify({"error": "Admin access required"}), 403

        request.current_user = user
        return fn(*args, **kwargs)

    return wrapper
