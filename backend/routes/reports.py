import os
import uuid
import re
import base64
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
from sqlalchemy import or_, func

from extensions import db
from models import WasteReport, RewardBadge, ComplaintStatusLog, Notification
from auth_utils import optional_login, login_required, admin_required
from municipal_service import (
    determine_department,
    get_default_cleanup_team,
    generate_complaint_id,
    generate_official_reference,
    submit_to_municipal_api,
)
from vision_service import analyze_waste_image

reports_bp = Blueprint("reports", __name__, url_prefix="/api")

VALID_STATUSES = {
    "Draft",
    "Submitted to GoGreen",
    "Pending Municipal Submission",
    "Forwarded to Authority",
    "Acknowledged",
    "Cleanup in Progress",
    "Resolved",
    "Rejected",
    "Pending",       # legacy compatibility
    "In Progress",   # legacy compatibility
}


def _allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def _extract_ward(location_str, default="Ward 7"):
    if not location_str:
        return default
    match = re.search(r"ward\s*(\d+)", location_str, re.IGNORECASE)
    if match:
        return f"Ward {match.group(1)}"
    return default


def _save_base64_image(data_url_or_base64):
    """Decodes a base64 string or data URL and saves to UPLOAD_FOLDER."""
    if not data_url_or_base64:
        return None
    try:
        if "," in data_url_or_base64:
            header, encoded = data_url_or_base64.split(",", 1)
            ext = "jpg"
            if "image/png" in header:
                ext = "png"
            elif "image/webp" in header:
                ext = "webp"
        else:
            encoded = data_url_or_base64
            ext = "jpg"

        image_data = base64.b64decode(encoded)
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        with open(filepath, "wb") as f:
            f.write(image_data)
        return filename
    except Exception as e:
        current_app.logger.warning(f"Error saving base64 image: {e}")
        return None


def _find_report(identifier):
    """Finds a WasteReport by primary key integer or string complaint_id."""
    if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
        rep = db.session.get(WasteReport, int(identifier))
        if rep:
            return rep
    # Try complaint_id lookup
    return WasteReport.query.filter(
        or_(
            WasteReport.complaint_id == identifier,
            WasteReport.complaint_id.ilike(f"%{identifier}%")
        )
    ).first()


# ============================================================================
# 1. CREATE COMPLAINT / REPORT GARBAGE
# ============================================================================
@reports_bp.post("/reports")
@optional_login
def create_report():
    image_filename = None

    if request.is_json:
        data = request.get_json() or {}
        name = (data.get("name") or data.get("repName") or "").strip()
        email = (data.get("email") or data.get("repEmail") or "").strip()
        waste_category = (data.get("category") or data.get("wasteCategory") or data.get("wasteType") or data.get("repType") or "").strip()
        location = (data.get("location") or data.get("address") or data.get("repLocation") or "").strip()
        address = (data.get("address") or location).strip()
        description = (data.get("description") or data.get("repDesc") or "").strip()
        severity = (data.get("severity") or data.get("priority") or "Medium").strip()
        ward = (data.get("ward") or "").strip()

        # GPS Coordinates
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        location_accuracy = data.get("locationAccuracy") or data.get("accuracy")

        # Base64 image payload (e.g. from live camera capture)
        b64_image = data.get("imageBase64") or data.get("image") or data.get("photo")
        if b64_image and isinstance(b64_image, str) and (b64_image.startswith("data:image") or len(b64_image) > 100):
            image_filename = _save_base64_image(b64_image)

    else:
        form = request.form
        name = (form.get("name") or form.get("repName") or "").strip()
        email = (form.get("email") or form.get("repEmail") or "").strip()
        waste_category = (form.get("category") or form.get("wasteCategory") or form.get("wasteType") or form.get("repType") or "").strip()
        location = (form.get("location") or form.get("address") or form.get("repLocation") or "").strip()
        address = (form.get("address") or location).strip()
        description = (form.get("description") or form.get("repDesc") or "").strip()
        severity = (form.get("severity") or form.get("priority") or "Medium").strip()
        ward = (form.get("ward") or "").strip()

        latitude = form.get("latitude")
        longitude = form.get("longitude")
        location_accuracy = form.get("locationAccuracy") or form.get("accuracy")

        # Check for uploaded file
        file = (
            request.files.get("image")
            or request.files.get("repImage")
            or request.files.get("fileInput")
            or request.files.get("photo")
        )
        if file and file.filename:
            if not _allowed_file(file.filename):
                return jsonify({"error": "Only PNG, JPG, JPEG, WEBP or GIF images are allowed"}), 400
            ext = file.filename.rsplit(".", 1)[-1].lower()
            image_filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], secure_filename(image_filename)))
        elif form.get("imageBase64"):
            image_filename = _save_base64_image(form.get("imageBase64"))

    # Convert numeric coords if provided
    try:
        latitude = float(latitude) if latitude is not None and str(latitude).strip() != "" else None
        longitude = float(longitude) if longitude is not None and str(longitude).strip() != "" else None
        location_accuracy = float(location_accuracy) if location_accuracy is not None and str(location_accuracy).strip() != "" else None
    except (ValueError, TypeError):
        latitude = None
        longitude = None
        location_accuracy = None

    # Pre-fill citizen contact if authenticated
    if request.current_user:
        if not name:
            name = request.current_user.name
        if not email:
            email = request.current_user.email
        if not ward:
            ward = getattr(request.current_user, "ward", "Ward 7")

    # If no address given but coordinates are available, generate a coordinates label
    if not location and latitude and longitude:
        location = f"Lat: {latitude:.5f}, Lon: {longitude:.5f}"
        if not address:
            address = location

    # Validation
    missing = []
    if not name: missing.append("name")
    if not email: missing.append("email")
    if not waste_category: missing.append("wasteCategory")
    if not (location or address or (latitude and longitude)): missing.append("location")
    if not description: missing.append("description")

    if missing:
        return jsonify({"error": "Missing required fields", "fields": missing}), 400

    if not ward:
        ward = _extract_ward(address or location, "Ward 7")

    # Severity normalization
    if severity not in {"Low", "Medium", "High", "Critical"}:
        severity = "Medium"

    # Generate unique complaint ID: GG-GRB-YYYYMMDD-XXXX
    complaint_id = generate_complaint_id()

    # Determine assigned municipal department
    assigned_dept = determine_department(waste_category)
    default_team = get_default_cleanup_team(ward)

    # Initial status
    initial_status = "Submitted to GoGreen"

    report = WasteReport(
        complaint_id=complaint_id,
        user_id=request.current_user.id if request.current_user else None,
        name=name,
        email=email,
        waste_type=waste_category,
        waste_category=waste_category,
        location=location or address,
        address=address or location,
        latitude=latitude,
        longitude=longitude,
        location_accuracy=location_accuracy,
        ward=ward,
        description=description,
        image_filename=image_filename,
        status=initial_status,
        priority=severity,
        severity=severity,
        assigned_department=assigned_dept,
        assigned_team=default_team,
    )
    db.session.add(report)
    db.session.flush()

    # Create initial audit log entry
    initial_log = ComplaintStatusLog(
        report_id=report.id,
        from_status=None,
        to_status=initial_status,
        action="Complaint Submitted",
        notes=f"Citizen {name} submitted garbage report with GPS verification. Assigned to {assigned_dept}.",
        updated_by=name,
    )
    db.session.add(initial_log)

    # Check official municipal API integration
    muni_result = submit_to_municipal_api(report)
    if muni_result.get("submitted"):
        report.status = muni_result.get("status", "Forwarded to Authority")
        report.official_reference_id = muni_result.get("officialReference")
        db.session.add(ComplaintStatusLog(
            report_id=report.id,
            from_status=initial_status,
            to_status=report.status,
            action="Forwarded to Municipal Authority",
            notes=muni_result.get("message"),
            official_reference=report.official_reference_id,
            updated_by="Municipal API Gateway",
        ))

    # Reward points for authenticated citizens
    points_earned = 0
    if request.current_user:
        points_earned = current_app.config["POINTS_PER_REPORT"]
        request.current_user.add_points(points_earned)

        # Notify user in-app
        db.session.add(Notification(
            user_id=request.current_user.id,
            title=f"🗑️ Complaint #{complaint_id} Logged",
            message=f"Your garbage report for {report.address[:40]} has been submitted. +{points_earned} Eco-Points added!",
            type="report"
        ))

        # Check Recycling Hero badge
        if request.current_user.eco_points >= 500:
            existing = RewardBadge.query.filter_by(user_id=request.current_user.id, name="Recycling Hero").first()
            if not existing:
                db.session.add(RewardBadge(
                    user_id=request.current_user.id,
                    name="Recycling Hero",
                    icon="♻️",
                    description="Earned 500+ Eco Points by actively reporting and recycling"
                ))

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Complaint #{complaint_id} successfully recorded in GoGreen Municipal Registry.",
        "complaintId": complaint_id,
        "report": report.to_dict(),
        "municipalSubmission": muni_result,
        "pointsEarned": points_earned,
        "totalPoints": request.current_user.eco_points if request.current_user else None
    }), 201


# ============================================================================
# 2. COMPUTER VISION AI IMAGE ANALYSIS
# ============================================================================
@reports_bp.post("/reports/analyze-image")
def analyze_image_route():
    """
    Analyzes an uploaded image or base64 frame with OpenCV Computer Vision.
    Detects litter regions, suggests waste category, and highlights bounding boxes.
    """
    temp_filename = None
    file = (
        request.files.get("image")
        or request.files.get("repImage")
        or request.files.get("photo")
    )

    if file and file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
        temp_filename = f"temp_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], temp_filename)
        file.save(filepath)
    else:
        data = request.get_json(silent=True) or {}
        b64 = data.get("imageBase64") or data.get("image") or request.form.get("imageBase64")
        if b64:
            temp_filename = _save_base64_image(b64)
            filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], temp_filename) if temp_filename else None
        else:
            return jsonify({"error": "No image provided for visual analysis."}), 400

    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "Failed to store image for inspection."}), 400

    # Run OpenCV analysis
    analysis_result = analyze_waste_image(filepath)

    # Attach preview URL
    analysis_result["tempImageUrl"] = f"/api/uploads/{temp_filename}" if temp_filename else None

    return jsonify(analysis_result), 200


# ============================================================================
# 3. LIST ALL COMPLAINTS / SEARCH & FILTER
# ============================================================================
@reports_bp.get("/reports")
@optional_login
def list_reports():
    status_filter = request.args.get("status")
    severity_filter = request.args.get("severity") or request.args.get("priority")
    category_filter = request.args.get("category") or request.args.get("wasteType")
    ward_filter = request.args.get("ward")
    search_query = request.args.get("search", "").strip()
    mine_only = request.args.get("mine", "false").lower() in {"true", "1", "yes"}

    query = WasteReport.query.order_by(WasteReport.created_at.desc())

    # User scoping: citizens only see their own when mine=true, admins see all
    if request.current_user and mine_only:
        query = query.filter_by(user_id=request.current_user.id)

    if status_filter and status_filter.lower() != "all":
        # Handle status mappings
        if status_filter in {"Pending", "Submitted to GoGreen"}:
            query = query.filter(or_(WasteReport.status == "Submitted to GoGreen", WasteReport.status == "Pending"))
        elif status_filter in {"In Progress", "Cleanup in Progress"}:
            query = query.filter(or_(WasteReport.status == "Cleanup in Progress", WasteReport.status == "In Progress"))
        else:
            query = query.filter(WasteReport.status == status_filter)

    if severity_filter and severity_filter.lower() != "all":
        query = query.filter(or_(WasteReport.severity == severity_filter, WasteReport.priority == severity_filter))

    if category_filter and category_filter.lower() != "all":
        query = query.filter(or_(
            WasteReport.waste_category.ilike(f"%{category_filter}%"),
            WasteReport.waste_type.ilike(f"%{category_filter}%")
        ))

    if ward_filter and ward_filter.lower() != "all":
        query = query.filter(WasteReport.ward == ward_filter)

    if search_query:
        like_term = f"%{search_query}%"
        query = query.filter(
            or_(
                WasteReport.complaint_id.ilike(like_term),
                WasteReport.description.ilike(like_term),
                WasteReport.location.ilike(like_term),
                WasteReport.address.ilike(like_term),
                WasteReport.name.ilike(like_term),
                WasteReport.official_reference_id.ilike(like_term),
            )
        )

    limit = min(int(request.args.get("limit", 100)), 200)
    offset = int(request.args.get("offset", 0))

    total_count = query.count()
    reports = query.offset(offset).limit(limit).all()

    return jsonify({
        "reports": [r.to_dict() for r in reports],
        "count": len(reports),
        "total": total_count,
        "offset": offset,
        "limit": limit
    }), 200


# ============================================================================
# 4. GET SINGLE COMPLAINT (BY ID OR COMPLAINT_ID)
# ============================================================================
@reports_bp.get("/reports/<path:identifier>")
def get_report(identifier):
    report = _find_report(identifier)
    if not report:
        return jsonify({"error": f"Complaint '{identifier}' not found."}), 404
    return jsonify({
        "success": True,
        "report": report.to_dict(include_history=True)
    }), 200


# ============================================================================
# 5. UPDATE COMPLAINT STATUS (ADMIN / DISPATCH WORKFLOW)
# ============================================================================
@reports_bp.patch("/reports/<path:identifier>/status")
@optional_login
def update_report_status(identifier):
    report = _find_report(identifier)
    if not report:
        return jsonify({"error": "Report not found"}), 404

    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    notes = data.get("notes") or data.get("remarks") or ""
    assigned_team = data.get("assignedTeam")
    assigned_dept = data.get("assignedDepartment")
    official_ref = data.get("officialReference")

    if new_status not in VALID_STATUSES:
        return jsonify({"error": f"Invalid status. Allowed: {', '.join(sorted(VALID_STATUSES))}"}), 400

    from_status = report.status
    report.status = new_status
    report.updated_at = datetime.now(timezone.utc)

    if assigned_team:
        report.assigned_team = assigned_team
    if assigned_dept:
        report.assigned_department = assigned_dept
    if official_ref:
        report.official_reference_id = official_ref

    if new_status == "Resolved":
        report.resolved_at = datetime.now(timezone.utc)
        if data.get("resolutionNotes"):
            report.resolution_notes = data.get("resolutionNotes")

    # Add audit log
    actor_name = getattr(request.current_user, "name", "Municipal Admin")
    log_entry = ComplaintStatusLog(
        report_id=report.id,
        from_status=from_status,
        to_status=new_status,
        action=f"Status changed to {new_status}",
        notes=notes or f"Updated by {actor_name}",
        official_reference=report.official_reference_id,
        updated_by=actor_name,
    )
    db.session.add(log_entry)

    # Notify reporting user if they have an account
    if report.user_id:
        db.session.add(Notification(
            user_id=report.user_id,
            title=f"📢 Complaint #{report.complaint_id} Update",
            message=f"Status changed to '{new_status}'. {notes}",
            type="report"
        ))

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Complaint #{report.complaint_id} status updated to {new_status}",
        "report": report.to_dict(include_history=True)
    }), 200


# ============================================================================
# 6. FORWARD COMPLAINT TO MUNICIPAL AUTHORITY (ADMIN WORKFLOW)
# ============================================================================
@reports_bp.post("/reports/<path:identifier>/forward")
@login_required
def forward_complaint(identifier):
    report = _find_report(identifier)
    if not report:
        return jsonify({"error": "Report not found"}), 404

    data = request.get_json(silent=True) or {}
    notes = data.get("notes") or f"Transmitted to municipal authority by {request.current_user.name}"
    team = data.get("assignedTeam") or get_default_cleanup_team(report.ward)
    dept = data.get("assignedDepartment") or report.assigned_department or determine_department(report.waste_category)

    # Generate official work order reference
    official_ref = generate_official_reference(report.ward, report.id)

    from_status = report.status
    report.status = "Forwarded to Authority"
    report.assigned_department = dept
    report.assigned_team = team
    report.official_reference_id = official_ref
    report.updated_at = datetime.now(timezone.utc)

    # Audit log
    db.session.add(ComplaintStatusLog(
        report_id=report.id,
        from_status=from_status,
        to_status="Forwarded to Authority",
        action="Forwarded to Municipal Authority",
        notes=notes,
        official_reference=official_ref,
        updated_by=f"Admin: {request.current_user.name}",
    ))

    # Notify reporting citizen
    if report.user_id:
        db.session.add(Notification(
            user_id=report.user_id,
            title=f"🏛️ Transmitted to Municipal Authority",
            message=f"Complaint #{report.complaint_id} has been transmitted to {dept}. Official Ref: {official_ref}",
            type="report"
        ))

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Complaint #{report.complaint_id} officially forwarded. Reference #{official_ref} issued.",
        "officialReference": official_ref,
        "report": report.to_dict(include_history=True)
    }), 200


# ============================================================================
# 7. RESOLVE COMPLAINT WITH PROOF-OF-CLEANUP PHOTOGRAPH (ADMIN WORKFLOW)
# ============================================================================
@reports_bp.post("/reports/<path:identifier>/resolve")
@login_required
def resolve_complaint(identifier):
    report = _find_report(identifier)
    if not report:
        return jsonify({"error": "Report not found"}), 404

    res_image_filename = None
    notes = ""

    if request.is_json:
        data = request.get_json() or {}
        notes = (data.get("notes") or data.get("resolutionNotes") or "").strip()
        b64_image = data.get("resolutionImage") or data.get("image")
        if b64_image:
            res_image_filename = _save_base64_image(b64_image)
    else:
        form = request.form
        notes = (form.get("notes") or form.get("resolutionNotes") or "").strip()
        file = request.files.get("resolutionImage") or request.files.get("image")
        if file and file.filename:
            if not _allowed_file(file.filename):
                return jsonify({"error": "Only PNG, JPG, JPEG, WEBP or GIF images allowed"}), 400
            ext = file.filename.rsplit(".", 1)[-1].lower()
            res_image_filename = f"res_{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], secure_filename(res_image_filename)))
        elif form.get("resolutionImage"):
            res_image_filename = _save_base64_image(form.get("resolutionImage"))

    from_status = report.status
    report.status = "Resolved"
    report.resolved_at = datetime.now(timezone.utc)
    report.updated_at = datetime.now(timezone.utc)
    if res_image_filename:
        report.resolution_image_filename = res_image_filename
    if notes:
        report.resolution_notes = notes

    # Audit log
    db.session.add(ComplaintStatusLog(
        report_id=report.id,
        from_status=from_status,
        to_status="Resolved",
        action="Cleanup Verified & Resolved",
        notes=notes or "Cleanup verified with photographic evidence by municipal supervisor.",
        official_reference=report.official_reference_id,
        updated_by=f"Admin: {request.current_user.name}",
    ))

    # Notify reporting citizen
    if report.user_id:
        db.session.add(Notification(
            user_id=report.user_id,
            title="✨ Garbage Cleanup Completed!",
            message=f"Complaint #{report.complaint_id} has been marked Resolved. Thank you for keeping your city clean!",
            type="report"
        ))

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Complaint #{report.complaint_id} marked as Resolved with verification proof.",
        "report": report.to_dict(include_history=True)
    }), 200


# ============================================================================
# 8. MUNICIPAL COMPLAINT STATS (FOR ADMIN / DASHBOARD)
# ============================================================================
@reports_bp.get("/reports/stats")
def get_complaint_stats():
    total = db.session.query(func.count(WasteReport.id)).scalar() or 0
    resolved = db.session.query(func.count(WasteReport.id)).filter(WasteReport.status == "Resolved").scalar() or 0
    in_progress = db.session.query(func.count(WasteReport.id)).filter(
        or_(WasteReport.status == "Cleanup in Progress", WasteReport.status == "In Progress")
    ).scalar() or 0
    pending = db.session.query(func.count(WasteReport.id)).filter(
        or_(
            WasteReport.status == "Submitted to GoGreen",
            WasteReport.status == "Pending Municipal Submission",
            WasteReport.status == "Pending",
            WasteReport.status == "Forwarded to Authority",
            WasteReport.status == "Acknowledged",
        )
    ).scalar() or 0
    critical = db.session.query(func.count(WasteReport.id)).filter(
        or_(WasteReport.severity == "Critical", WasteReport.priority == "Critical")
    ).scalar() or 0

    # Category breakdown
    cat_rows = db.session.query(WasteReport.waste_type, func.count(WasteReport.id)).group_by(WasteReport.waste_type).all()
    categories = {r[0]: r[1] for r in cat_rows if r[0]}

    # Ward breakdown
    ward_rows = db.session.query(WasteReport.ward, func.count(WasteReport.id)).group_by(WasteReport.ward).all()
    wards = {r[0]: r[1] for r in ward_rows if r[0]}

    return jsonify({
        "total": total,
        "resolved": resolved,
        "inProgress": in_progress,
        "pending": pending,
        "critical": critical,
        "categories": categories,
        "wards": wards,
        "resolutionRate": round((resolved / total * 100), 1) if total > 0 else 0.0,
    }), 200


# ============================================================================
# 9. MUNICIPAL CONFIG INFO
# ============================================================================
@reports_bp.get("/reports/municipal-config")
def get_municipal_config():
    api_url = current_app.config.get("MUNICIPAL_API_URL")
    return jsonify({
        "authorityName": current_app.config.get("MUNICIPAL_NAME"),
        "isLiveApiConnected": bool(api_url),
        "apiEndpointConfigured": bool(api_url),
        "operatingMode": "Live Government API Submission" if api_url else "GoGreen Municipal Registry & Administrative Dispatch",
        "supportedCategories": [
            "Roadside Garbage",
            "Overflowing Dustbin",
            "Plastic Waste",
            "Construction Waste",
            "Drainage Waste",
            "Illegal Dumping",
            "Other"
        ],
        "supportedSeverities": ["Low", "Medium", "High", "Critical"]
    }), 200


# ============================================================================
# 10. DELETE REPORT
# ============================================================================
@reports_bp.delete("/reports/<path:identifier>")
@login_required
def delete_report(identifier):
    report = _find_report(identifier)
    if not report:
        return jsonify({"error": "Report not found"}), 404

    if report.user_id != request.current_user.id and request.current_user.role != "admin":
        return jsonify({"error": "You do not have permission to delete this report"}), 403

    db.session.delete(report)
    db.session.commit()
    return jsonify({"message": f"Report #{report.complaint_id} deleted successfully"}), 200


# ============================================================================
# 11. SERVE UPLOADED IMAGES
# ============================================================================
@reports_bp.get("/uploads/<path:filename>")
def get_upload(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
