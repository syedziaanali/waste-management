from flask import Blueprint, jsonify, request
from extensions import db
from models import Notification, User
from auth_utils import login_required

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@notifications_bp.get("")
@notifications_bp.get("/")
@login_required
def get_notifications():
    """Returns user notification alerts and unread count."""
    user = request.current_user
    notifs = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(15).all()
    unread_count = Notification.query.filter_by(user_id=user.id, is_read=False).count()
    return jsonify({
        "notifications": [n.to_dict() for n in notifs],
        "unreadCount": unread_count
    }), 200


@notifications_bp.post("/<int:notif_id>/read")
@login_required
def mark_notification_read(notif_id):
    """Marks a single notification as read."""
    user = request.current_user
    notif = Notification.query.filter_by(id=notif_id, user_id=user.id).first()
    if not notif:
        return jsonify({"error": "Notification not found"}), 404
    notif.is_read = True
    db.session.commit()
    return jsonify({"success": True, "notification": notif.to_dict()}), 200


@notifications_bp.post("/mark-all-read")
@login_required
def mark_all_notifications_read():
    """Marks all user notifications as read."""
    user = request.current_user
    Notification.query.filter_by(user_id=user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"success": True}), 200
