import re
from flask import Blueprint, request, jsonify
from extensions import db
from models import User, RewardBadge
from auth_utils import encode_token, login_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.post("/signup")
def signup():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    ward = (data.get("ward") or "Ward 7").strip()

    if not name:
        return jsonify({"error": "Full name is required"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "A valid email is required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({
            "error": "You have already registered. Please log in.",
            "alreadyRegistered": True,
            "email": email
        }), 409

    user = User(
        name=name,
        email=email,
        ward=ward,
        eco_points=100,  # Welcome bonus
        level="Green Beginner",
        streak_days=1,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    # Add starter welcome badge
    badge = RewardBadge(
        user_id=user.id,
        name="Green Beginner",
        icon="🌱",
        description="Joined the Go Green community"
    )
    db.session.add(badge)
    db.session.commit()

    token = encode_token(user.id)
    return jsonify({
        "message": "Account created successfully! +100 Eco Points welcome bonus awarded.",
        "token": token,
        "user": user.to_dict()
    }), 201


@auth_bp.get("/check-email")
def check_email():
    """Checks if an email is already registered."""
    email = (request.args.get("email") or "").strip().lower()
    if not email:
        return jsonify({"exists": False}), 200
    user = User.query.filter_by(email=email).first()
    return jsonify({
        "exists": user is not None,
        "message": "You have already registered. Please log in." if user else "Email is available."
    }), 200


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = encode_token(user.id)
    return jsonify({
        "message": f"Welcome back, {user.name.split()[0]}!",
        "token": token,
        "user": user.to_dict()
    }), 200


@auth_bp.post("/google")
def google_auth():
    """Authenticates or creates a citizen user via Google Sign-In."""
    from flask import current_app
    from auth_utils import verify_google_token

    data = request.get_json(silent=True) or {}
    credential = data.get("credential")  # Google ID Token
    google_id = data.get("googleId") or data.get("sub")
    email = (data.get("email") or "").strip().lower()
    name = (data.get("name") or "").strip()
    avatar_url = data.get("picture") or data.get("avatarUrl") or ""
    mode = (data.get("mode") or "login").strip().lower()

    # If an ID Token is provided, decode and verify claims
    if credential:
        claims = verify_google_token(credential)
        if claims:
            email = (claims.get("email") or email).strip().lower()
            name = claims.get("name") or name
            avatar_url = claims.get("picture") or avatar_url
            google_id = claims.get("sub") or google_id
        elif not email:
            return jsonify({"error": "Unable to verify Google credentials"}), 401

    if not email:
        return jsonify({"error": "A valid Google account email is required"}), 400

    if not name:
        name = email.split("@")[0].replace(".", " ").replace("_", " ").title()

    # Match user by google_id or email
    user = None
    if google_id:
        user = User.query.filter_by(google_id=google_id).first()
    if not user and email:
        user = User.query.filter_by(email=email).first()

    # If this is a signup attempt and account is already registered, reject with 409
    if mode == "signup" and user:
        return jsonify({
            "error": "You have already registered. Please log in.",
            "alreadyRegistered": True,
            "email": email
        }), 409

    is_new = False
    if not user:
        import uuid
        is_new = True
        user = User(
            name=name,
            email=email,
            password_hash=f"GOOGLE_OAUTH_{uuid.uuid4().hex}",
            google_id=google_id,
            avatar_url=avatar_url,
            auth_provider="google",
            ward="Ward 7",
            eco_points=100,  # Welcome bonus
            level="Green Beginner",
            streak_days=1,
        )
        db.session.add(user)
        db.session.flush()

        # Starter Badge
        badge = RewardBadge(
            user_id=user.id,
            name="Green Beginner",
            icon="🌱",
            description="Joined the Go Green community via Google"
        )
        db.session.add(badge)
    else:
        # Sync google_id and avatar if not present
        if google_id and not user.google_id:
            user.google_id = google_id
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
        if user.auth_provider == "local" and google_id:
            user.auth_provider = "google"

    db.session.commit()

    token = encode_token(user.id)
    return jsonify({
        "message": f"Welcome to Go Green, {user.name.split()[0]}!" if is_new else f"Welcome back, {user.name.split()[0]}!",
        "token": token,
        "isNew": is_new,
        "user": user.to_dict()
    }), 200


@auth_bp.get("/config")
def auth_config():
    """Returns public authentication configuration for GIS, Firebase, and OAuth."""
    from flask import current_app
    return jsonify({
        "googleClientId": current_app.config.get("GOOGLE_CLIENT_ID", ""),
        "firebaseConfig": {
            "apiKey": current_app.config.get("FIREBASE_API_KEY", ""),
            "authDomain": current_app.config.get("FIREBASE_AUTH_DOMAIN", ""),
            "projectId": current_app.config.get("FIREBASE_PROJECT_ID", ""),
            "storageBucket": current_app.config.get("FIREBASE_STORAGE_BUCKET", ""),
            "messagingSenderId": current_app.config.get("FIREBASE_MESSAGING_SENDER_ID", ""),
            "appId": current_app.config.get("FIREBASE_APP_ID", ""),
        },
        "service": "Go Green Authentication",
        "methods": ["password", "google", "firebase"]
    }), 200



@auth_bp.get("/me")
@login_required
def me():
    return jsonify({"user": request.current_user.to_dict()}), 200



@auth_bp.put("/profile")
@login_required
def update_profile():
    user = request.current_user
    data = request.get_json(silent=True) or {}

    name = data.get("name")
    ward = data.get("ward")
    new_password = data.get("newPassword")
    current_password = data.get("currentPassword")

    if name:
        user.name = name.strip()
    if ward:
        user.ward = ward.strip()

    if new_password:
        if not current_password or not user.check_password(current_password):
            return jsonify({"error": "Current password is required to set a new password"}), 400
        if len(new_password) < 6:
            return jsonify({"error": "New password must be at least 6 characters"}), 400
        user.set_password(new_password)

    db.session.commit()
    return jsonify({"message": "Profile updated successfully", "user": user.to_dict()}), 200
