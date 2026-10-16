import sys
import os
import webbrowser
import threading

# Ensure backend directory is in Python path regardless of working directory
BACKEND_DIR = os.path.abspath(os.path.dirname(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from config import Config
from extensions import db

# Path to the frontend directory
FRONTEND_DIR = os.path.abspath(os.path.join(BACKEND_DIR, "..", "frontend"))


def create_app(config_class=Config):
    app = Flask(
        __name__,
        static_folder=FRONTEND_DIR,
        static_url_path=""
    )
    app.config.from_object(config_class)

    # Ensure upload folder exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Configure CORS
    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    )

    # Import and register blueprints
    from routes.auth import auth_bp
    from routes.reports import reports_bp
    from routes.schedule_routes import schedule_bp
    from routes.dashboard import dashboard_bp
    from routes.recycling import recycling_bp
    from routes.rewards import rewards_bp
    from routes.notifications import notifications_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(recycling_bp)
    app.register_blueprint(rewards_bp)
    app.register_blueprint(notifications_bp)

    # --- Serve Frontend Website Directly ---
    @app.get("/")
    @app.get("/index.html")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/login")
    @app.get("/login.html")
    def login_page():
        return send_from_directory(FRONTEND_DIR, "login.html")

    @app.get("/signup")
    @app.get("/signup.html")
    def signup_page():
        return send_from_directory(FRONTEND_DIR, "signup.html")

    @app.get("/dashboard")
    @app.get("/dashboard.html")
    def dashboard_page():
        return send_from_directory(FRONTEND_DIR, "dashboard.html")

    @app.get("/report")
    @app.get("/report.html")
    def report_page():
        return send_from_directory(FRONTEND_DIR, "report.html")

    @app.get("/track")
    @app.get("/track.html")
    def track_page():
        return send_from_directory(FRONTEND_DIR, "track.html")

    @app.get("/admin")
    @app.get("/admin.html")
    def admin_page():
        return send_from_directory(FRONTEND_DIR, "admin.html")

    # --- API Info & Health Check ---
    @app.get("/api")
    def api_info():
        return jsonify({
            "service": "Go Green Waste Management API",
            "version": "1.1.0",
            "status": "online",
            "features": ["Smart Garbage Reporting", "Live Camera", "GPS Geolocation", "Municipal Routing", "AI Vision"],
            "endpoints": {
                "health": "/api/health",
                "auth": ["/api/auth/signup", "/api/auth/login", "/api/auth/me", "/api/auth/profile", "/api/auth/check-email"],
                "reports": [
                    "/api/reports (GET, POST)",
                    "/api/reports/<id_or_complaint_id> (GET)",
                    "/api/reports/<id>/status (PATCH)",
                    "/api/reports/<id>/forward (POST)",
                    "/api/reports/<id>/resolve (POST)",
                    "/api/reports/analyze-image (POST)",
                    "/api/reports/stats (GET)",
                    "/api/reports/municipal-config (GET)"
                ],
                "schedule": ["/api/schedule", "/api/schedule/<id>", "/api/schedule/ref/<ref>"],
                "dashboard": ["/api/dashboard/stats", "/api/dashboard/activity", "/api/dashboard/rewards", "/api/dashboard/bins", "/api/dashboard/overview"],
                "recycling": ["/api/recycling/categories", "/api/recycling/centers"]
            }
        }), 200

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "Go Green API", "database": "connected"}), 200

    @app.errorhandler(400)
    def bad_request(err):
        return jsonify({"error": str(err.description or "Bad request")}), 400

    @app.errorhandler(404)
    def not_found(_err):
        # Fallback to index.html if user navigates to frontend client route
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.errorhandler(413)
    def too_large(_err):
        return jsonify({"error": "File size exceeds limit (max 10MB)"}), 413

    @app.errorhandler(500)
    def internal_error(_err):
        return jsonify({"error": "Internal server error"}), 500

    with app.app_context():
        db.create_all()
        # Auto-migrate columns for existing SQLite database
        try:
            from sqlalchemy import text
            with db.engine.connect() as conn:
                # 1. Users migration
                res_users = conn.execute(text("PRAGMA table_info(users)")).fetchall()
                cols = [r[1] for r in res_users]
                if cols and "google_id" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN google_id VARCHAR(120)"))
                if cols and "avatar_url" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500)"))

                # 2. Sensor bins migration
                res_bins = conn.execute(text("PRAGMA table_info(sensor_bins)")).fetchall()
                bin_cols = [r[1] for r in res_bins]
                if bin_cols and "sensor_code" not in bin_cols:
                    conn.execute(text("ALTER TABLE sensor_bins ADD COLUMN sensor_code VARCHAR(30) DEFAULT 'IOT-BIN-01'"))
                if bin_cols and "temperature" not in bin_cols:
                    conn.execute(text("ALTER TABLE sensor_bins ADD COLUMN temperature FLOAT DEFAULT 26.5"))
                if bin_cols and "battery_level" not in bin_cols:
                    conn.execute(text("ALTER TABLE sensor_bins ADD COLUMN battery_level INTEGER DEFAULT 95"))
                if bin_cols and "is_dispatched" not in bin_cols:
                    conn.execute(text("ALTER TABLE sensor_bins ADD COLUMN is_dispatched BOOLEAN DEFAULT 0"))

                # 3. Waste reports migration for Smart Garbage Reporting System
                res_reports = conn.execute(text("PRAGMA table_info(waste_reports)")).fetchall()
                rep_cols = [r[1] for r in res_reports]
                if rep_cols:
                    if "complaint_id" not in rep_cols:
                        conn.execute(text("ALTER TABLE waste_reports ADD COLUMN complaint_id VARCHAR(40)"))
                    if "waste_category" not in rep_cols:
                        conn.execute(text("ALTER TABLE waste_reports ADD COLUMN waste_category VARCHAR(80)"))
                    if "address" not in rep_cols:
                        conn.execute(text("ALTER TABLE waste_reports ADD COLUMN address VARCHAR(255)"))
                    if "latitude" not in rep_cols:
                        conn.execute(text("ALTER TABLE waste_reports ADD COLUMN latitude FLOAT"))
                    if "longitude" not in rep_cols:
                        conn.execute(text("ALTER TABLE waste_reports ADD COLUMN longitude FLOAT"))
                    if "location_accuracy" not in rep_cols:
                        conn.execute(text("ALTER TABLE waste_reports ADD COLUMN location_accuracy FLOAT"))
                    if "severity" not in rep_cols:
                        conn.execute(text("ALTER TABLE waste_reports ADD COLUMN severity VARCHAR(20) DEFAULT 'Medium'"))
                    if "assigned_department" not in rep_cols:
                        conn.execute(text("ALTER TABLE waste_reports ADD COLUMN assigned_department VARCHAR(120)"))
                    if "assigned_team" not in rep_cols:
                        conn.execute(text("ALTER TABLE waste_reports ADD COLUMN assigned_team VARCHAR(120)"))
                    if "official_reference_id" not in rep_cols:
                        conn.execute(text("ALTER TABLE waste_reports ADD COLUMN official_reference_id VARCHAR(80)"))
                    if "resolution_image_filename" not in rep_cols:
                        conn.execute(text("ALTER TABLE waste_reports ADD COLUMN resolution_image_filename VARCHAR(255)"))
                    if "resolution_notes" not in rep_cols:
                        conn.execute(text("ALTER TABLE waste_reports ADD COLUMN resolution_notes TEXT"))
                    if "updated_at" not in rep_cols:
                        conn.execute(text("ALTER TABLE waste_reports ADD COLUMN updated_at DATETIME"))

                    # Backfill complaint_id for existing rows that have NULL
                    conn.execute(text(
                        "UPDATE waste_reports SET complaint_id = 'GG-GRB-2026-' || printf('%04d', id) "
                        "WHERE complaint_id IS NULL OR complaint_id = ''"
                    ))
                    # Sync waste_category from waste_type if missing
                    conn.execute(text(
                        "UPDATE waste_reports SET waste_category = waste_type "
                        "WHERE waste_category IS NULL OR waste_category = ''"
                    ))
                    # Default department for existing reports
                    conn.execute(text(
                        "UPDATE waste_reports SET assigned_department = 'Solid Waste Management Department (SWMD)' "
                        "WHERE assigned_department IS NULL OR assigned_department = ''"
                    ))

                conn.commit()
        except Exception as e:
            app.logger.warning(f"Migration note: {e}")

        try:
            from seed import seed_database
            seed_database()
        except Exception as e:
            app.logger.warning(f"Seed note: {e}")

    return app


def open_real_browser(url):
    """Opens the URL directly in the user's primary Google Chrome profile with their real logged-in Google accounts."""
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in chrome_paths:
        if os.path.exists(path):
            try:
                import subprocess
                subprocess.Popen([path, url])
                return
            except Exception:
                pass
    webbrowser.open(url)


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    print("==================================================")
    print("  [Go Green] Flask Backend & Web App is running!")
    print(f"  * Open in Browser:   http://127.0.0.1:{port}")
    print("==================================================")
    
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Timer(1.5, lambda: open_real_browser(f"http://127.0.0.1:{port}")).start()
        
    app.run(debug=True, host=host, port=port)
