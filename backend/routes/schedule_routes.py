import random
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app

from extensions import db
from models import CollectionSchedule
from auth_utils import optional_login, login_required

schedule_bp = Blueprint("schedule", __name__, url_prefix="/api")


def _generate_reference():
    while True:
        ref = f"GG-{random.randint(1000, 9999)}"
        if not CollectionSchedule.query.filter_by(reference=ref).first():
            return ref


@schedule_bp.post("/schedule")
@optional_login
def create_schedule():
    data = request.get_json(silent=True) or {}

    waste_type = (data.get("wasteType") or data.get("type") or "").strip()
    date_str = (data.get("date") or data.get("pickupDate") or "").strip()
    time_slot = (data.get("timeSlot") or data.get("slot") or "").strip()
    address = (data.get("address") or "").strip()
    notes = (data.get("notes") or "").strip() or None

    missing = []
    if not waste_type: missing.append("wasteType")
    if not date_str: missing.append("date")
    if not time_slot: missing.append("timeSlot")
    if not address: missing.append("address")

    if missing:
        return jsonify({"error": "Missing required fields", "fields": missing}), 400

    try:
        pickup_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "date must be in YYYY-MM-DD format"}), 400

    ref = _generate_reference()

    schedule = CollectionSchedule(
        user_id=request.current_user.id if request.current_user else None,
        waste_type=waste_type,
        pickup_date=pickup_date,
        time_slot=time_slot,
        address=address,
        notes=notes,
        reference=ref,
        status="Scheduled"
    )
    db.session.add(schedule)

    points_earned = 0
    if request.current_user:
        points_earned = current_app.config["POINTS_PER_SCHEDULE"]
        request.current_user.add_points(points_earned)

    db.session.commit()

    return jsonify({
        "message": f"Collection #{ref} scheduled successfully.",
        "schedule": schedule.to_dict(),
        "reference": ref,
        "pointsEarned": points_earned,
        "totalPoints": request.current_user.eco_points if request.current_user else None
    }), 201


@schedule_bp.get("/schedule")
@optional_login
def list_schedules():
    status_filter = request.args.get("status")
    mine_only = request.args.get("mine", "false").lower() in {"true", "1", "yes"}

    query = CollectionSchedule.query.order_by(CollectionSchedule.pickup_date.asc())

    if request.current_user and (mine_only or request.current_user.role == "citizen"):
        if mine_only:
            query = query.filter_by(user_id=request.current_user.id)

    if status_filter:
        query = query.filter_by(status=status_filter)

    limit = min(int(request.args.get("limit", 50)), 100)
    schedules = query.limit(limit).all()

    return jsonify({
        "schedules": [s.to_dict() for s in schedules],
        "count": len(schedules)
    }), 200


@schedule_bp.get("/schedule/<int:schedule_id>")
def get_schedule(schedule_id):
    schedule = db.get_or_404(CollectionSchedule, schedule_id)
    return jsonify({"schedule": schedule.to_dict()}), 200


@schedule_bp.get("/schedule/ref/<string:reference>")
def get_schedule_by_ref(reference):
    schedule = CollectionSchedule.query.filter_by(reference=reference.upper()).first_or_404()
    return jsonify({"schedule": schedule.to_dict()}), 200


@schedule_bp.patch("/schedule/<int:schedule_id>/status")
def update_status(schedule_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in {"Scheduled", "In Progress", "Completed", "Cancelled"}:
        return jsonify({"error": "Invalid status. Allowed: Scheduled, In Progress, Completed, Cancelled"}), 400

    schedule = db.get_or_404(CollectionSchedule, schedule_id)
    schedule.status = status
    db.session.commit()
    return jsonify({"message": f"Schedule status updated to {status}", "schedule": schedule.to_dict()}), 200


@schedule_bp.delete("/schedule/<int:schedule_id>")
@login_required
def delete_schedule(schedule_id):
    schedule = db.get_or_404(CollectionSchedule, schedule_id)
    if schedule.user_id != request.current_user.id and request.current_user.role != "admin":
        return jsonify({"error": "You do not have permission to cancel this schedule"}), 403

    schedule.status = "Cancelled"
    db.session.commit()
    return jsonify({"message": "Schedule cancelled successfully"}), 200
