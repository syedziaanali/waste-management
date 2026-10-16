import uuid
import hashlib
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from extensions import db
from models import WasteReport, CollectionSchedule, User, SensorBin, RewardBadge, RewardVoucher, Notification
from auth_utils import login_required, optional_login

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.get("/stats")
def impact_stats():
    """Site-wide counters for the homepage's animated stat cards."""
    report_count = db.session.query(func.count(WasteReport.id)).scalar() or 0
    resolved_count = (
        db.session.query(func.count(WasteReport.id))
        .filter(WasteReport.status == "Resolved")
        .scalar()
        or 0
    )
    schedule_count = db.session.query(func.count(CollectionSchedule.id)).scalar() or 0
    user_count = db.session.query(func.count(User.id)).scalar() or 0

    # Base realistic platform numbers + live DB entries
    total_reports = 25000 + report_count
    successful_collections = 18500 + schedule_count
    recycled_kg = 12000 + (resolved_count * 15) + (schedule_count * 20)
    green_citizens = 8000 + user_count
    resolved_reports = 12500 + resolved_count

    return jsonify({
        "wasteReports": total_reports,
        "successfulCollections": successful_collections,
        "recycledKg": recycled_kg,
        "greenCitizens": green_citizens,
        "resolvedReports": resolved_reports,
        "satisfactionRate": "4.9/5",
        "avgResponseTime": "18 min",
        "wardsConnected": 42
    }), 200


@dashboard_bp.get("/activity")
@optional_login
def weekly_activity():
    """Returns 7-day activity metrics formatted directly for Chart.js."""
    today = datetime.now(timezone.utc).date()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]

    # Base values for a realistic chart
    base_collected = [12, 19, 14, 22, 18, 9, 15]
    base_recycled = [8, 13, 10, 17, 14, 6, 11]

    collected_data = []
    recycled_data = []

    for i, day in enumerate(days):
        day_str = day.isoformat()
        
        # User-specific or platform counts
        q_rep = WasteReport.query.filter(func.date(WasteReport.created_at) == day_str)
        q_sch = CollectionSchedule.query.filter(CollectionSchedule.pickup_date == day)

        if request.current_user:
            q_rep = q_rep.filter(WasteReport.user_id == request.current_user.id)
            q_sch = q_sch.filter(CollectionSchedule.user_id == request.current_user.id)

        rep_count = q_rep.count()
        sch_count = q_sch.count()

        collected_data.append(base_collected[i] + (rep_count * 3))
        recycled_data.append(base_recycled[i] + (sch_count * 4))

    return jsonify({
        "labels": [d.strftime("%a") for d in days],
        "collected": collected_data,
        "recycled": recycled_data,
    }), 200


@dashboard_bp.get("/rewards")
@optional_login
def rewards():
    user = request.current_user
    if not user:
        return jsonify({
            "ecoPoints": 850,
            "level": "Recycling Hero",
            "streakDays": 14,
            "progressToNextLevel": 85,
            "nextLevel": "Eco Warrior",
            "pointsToNext": 150,
            "badges": [
                {"name": "Green Beginner", "icon": "🌱", "unlocked": True, "description": "Joined Go Green"},
                {"name": "Recycling Hero", "icon": "♻️", "unlocked": True, "description": "Reached 500+ points"},
                {"name": "Eco Warrior", "icon": "🌍", "unlocked": True, "description": "Reached 1000+ points"},
                {"name": "Planet Protector", "icon": "🏆", "unlocked": False, "description": "Reach 1500+ points"}
            ]
        }), 200

    pts = user.eco_points
    if pts >= 1500:
        progress = 100
        next_level = "Max Level"
        points_to_next = 0
    elif pts >= 1000:
        progress = min(100, int(((pts - 1000) / 500) * 100))
        next_level = "Planet Protector"
        points_to_next = 1500 - pts
    elif pts >= 500:
        progress = min(100, int(((pts - 500) / 500) * 100))
        next_level = "Eco Warrior"
        points_to_next = 1000 - pts
    else:
        progress = min(100, int((pts / 500) * 100))
        next_level = "Recycling Hero"
        points_to_next = 500 - pts

    all_badges = [
        {"name": "Green Beginner", "icon": "🌱", "unlocked": pts >= 0, "description": "Joined Go Green"},
        {"name": "Recycling Hero", "icon": "♻️", "unlocked": pts >= 500, "description": "Reached 500+ points"},
        {"name": "Eco Warrior", "icon": "🌍", "unlocked": pts >= 1000, "description": "Reached 1000+ points"},
        {"name": "Planet Protector", "icon": "🏆", "unlocked": pts >= 1500, "description": "Reach 1500+ points"},
    ]

    return jsonify({
        "ecoPoints": user.eco_points,
        "level": user.level,
        "streakDays": user.streak_days,
        "progressToNextLevel": max(5, progress),
        "nextLevel": next_level,
        "pointsToNext": max(0, points_to_next),
        "badges": all_badges,
    }), 200


@dashboard_bp.get("/bins")
def live_bins():
    """Returns live sensor bin statuses across city wards."""
    bins = SensorBin.query.order_by(SensorBin.ward_number.asc()).all()
    if not bins:
        # Fallback default wards if DB hasn't been seeded yet
        default_bins = [
            {"ward": "Ward 4", "fillLevel": 22, "status": "low", "location": "Market Road"},
            {"ward": "Ward 9", "fillLevel": 61, "status": "mid", "location": "Greenfield Ave"},
            {"ward": "Ward 2", "fillLevel": 88, "status": "high", "location": "Central Square"},
            {"ward": "Ward 7", "fillLevel": 15, "status": "low", "location": "Lakeview Colony"},
            {"ward": "Ward 1", "fillLevel": 54, "status": "mid", "location": "MG Road"},
            {"ward": "Ward 6", "fillLevel": 30, "status": "low", "location": "Highland Park"},
        ]
        return jsonify({"bins": default_bins}), 200

    return jsonify({"bins": [b.to_dict() for b in bins]}), 200


@dashboard_bp.get("/overview")
@optional_login
def dashboard_overview():
    """Provides bundled stats for the dashboard preview and overview component."""
    user = request.current_user
    user_id = user.id if user else None

    if user:
        total_reports = WasteReport.query.filter_by(user_id=user_id).count()
        pending_reports = WasteReport.query.filter_by(user_id=user_id, status="Pending").count()
        completed_collections = CollectionSchedule.query.filter_by(user_id=user_id, status="Completed").count()
        recent_reports = WasteReport.query.filter_by(user_id=user_id).order_by(WasteReport.created_at.desc()).limit(3).all()
        upcoming_pickup = CollectionSchedule.query.filter_by(user_id=user_id).order_by(CollectionSchedule.pickup_date.asc()).first()
    else:
        total_reports = 32
        pending_reports = 4
        completed_collections = 28
        recent_reports = WasteReport.query.order_by(WasteReport.created_at.desc()).limit(3).all()
        upcoming_pickup = CollectionSchedule.query.order_by(CollectionSchedule.pickup_date.asc()).first()

    return jsonify({
        "userName": user.name if user else "Citizen",
        "ward": user.ward if user else "Ward 7",
        "ecoPoints": user.eco_points if user else 850,
        "totalReports": total_reports,
        "pendingReports": pending_reports,
        "completedCollections": completed_collections,
        "upcomingPickup": upcoming_pickup.to_dict() if upcoming_pickup else {
            "reference": "GG-8842",
            "wasteType": "Mixed Recyclables",
            "timeSlot": "9:00 – 11:00 AM",
            "address": "12 Lakeview Colony",
            "status": "Scheduled"
        },
        "recentReports": [r.to_dict() for r in recent_reports] if recent_reports else [
            {"location": "Overflowing bin — MG Road", "status": "Resolved"},
            {"location": "Illegal dumping — Sector 5", "status": "In Progress"},
            {"location": "E-waste pickup — Park St", "status": "Pending"},
        ]
    }), 200


@dashboard_bp.get("/leaderboard")
@optional_login
def get_leaderboard():
    """Returns Top Eco-Citizens and Ward Cleanliness Rankings."""
    # 1. Top Citizens
    top_users = User.query.order_by(User.eco_points.desc()).limit(10).all()
    user_rankings = []
    
    for idx, u in enumerate(top_users, start=1):
        user_rankings.append({
            "rank": idx,
            "id": u.id,
            "name": u.name,
            "initials": u.get_initials(),
            "avatarUrl": u.avatar_url,
            "ward": u.ward,
            "ecoPoints": u.eco_points,
            "level": u.level,
            "streakDays": u.streak_days,
            "isCurrentUser": request.current_user and request.current_user.id == u.id
        })

    # If logged in user is outside top 10, include their current rank
    current_user_data = None
    if request.current_user:
        higher_count = User.query.filter(User.eco_points > request.current_user.eco_points).count()
        user_rank = higher_count + 1
        current_user_data = {
            "rank": user_rank,
            "name": request.current_user.name,
            "ecoPoints": request.current_user.eco_points,
            "level": request.current_user.level,
            "ward": request.current_user.ward,
        }

    # 2. Ward Cleanliness League (Ward 1 to Ward 9)
    ward_stats = [
        {"ward": "Ward 4", "cleanlinessScore": 96.4, "segregationRate": "92%", "divertedTons": 48.2, "status": "Elite Gold", "rank": 1},
        {"ward": "Ward 7", "cleanlinessScore": 94.8, "segregationRate": "89%", "divertedTons": 42.6, "status": "Elite Gold", "rank": 2},
        {"ward": "Ward 1", "cleanlinessScore": 91.2, "segregationRate": "85%", "divertedTons": 39.1, "status": "Silver", "rank": 3},
        {"ward": "Ward 9", "cleanlinessScore": 88.5, "segregationRate": "82%", "divertedTons": 34.7, "status": "Silver", "rank": 4},
        {"ward": "Ward 6", "cleanlinessScore": 86.0, "segregationRate": "78%", "divertedTons": 30.5, "status": "Bronze", "rank": 5},
        {"ward": "Ward 2", "cleanlinessScore": 81.3, "segregationRate": "74%", "divertedTons": 26.8, "status": "Active", "rank": 6},
        {"ward": "Ward 3", "cleanlinessScore": 79.5, "segregationRate": "70%", "divertedTons": 22.4, "status": "Active", "rank": 7},
        {"ward": "Ward 5", "cleanlinessScore": 77.0, "segregationRate": "68%", "divertedTons": 19.8, "status": "Needs Improvement", "rank": 8},
        {"ward": "Ward 8", "cleanlinessScore": 74.2, "segregationRate": "65%", "divertedTons": 16.5, "status": "Needs Improvement", "rank": 9},
    ]

    return jsonify({
        "citizens": user_rankings,
        "currentUserRank": current_user_data,
        "wardLeague": ward_stats
    }), 200


@dashboard_bp.post("/bins/<int:bin_id>/dispatch")
@optional_login
def dispatch_emergency_truck(bin_id):
    """
    Citizen Emergency Truck Dispatch.
    Dispatches a collection crew for full bins and awards the citizen +25 bounty points.
    """
    bin_obj = db.session.get(SensorBin, bin_id)
    if not bin_obj:
        return jsonify({"error": "Sensor bin not found"}), 404

    bounty_points = 25
    bin_obj.is_dispatched = True
    bin_obj.fill_level = max(15, bin_obj.fill_level - 40)
    bin_obj.last_updated = datetime.now(timezone.utc)

    user = request.current_user
    user_points = None
    if user:
        user.add_points(bounty_points)
        notif = Notification(
            user_id=user.id,
            title="🚨 Emergency Dispatch Work Order Created",
            message=f"You dispatched an emergency pickup crew for Smart Bin #{bin_obj.sensor_code or bin_obj.id} at {bin_obj.location_name} ({bin_obj.ward_number}). +{bounty_points} Eco Bounty Points awarded!",
            type="sensor"
        )
        db.session.add(notif)
        user_points = user.eco_points

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Emergency truck dispatched to {bin_obj.location_name} ({bin_obj.ward_number}).",
        "bin": bin_obj.to_dict(),
        "bountyAwarded": bounty_points,
        "userPoints": user_points
    }), 200


@dashboard_bp.get("/carbon-esg")
@optional_login
def get_carbon_esg():
    """Calculates live Carbon Footprint offset, ESG metrics, and generates official Green Citizen Certificate."""
    user = request.current_user
    user_pts = user.eco_points if user else 850
    user_name = user.name if user else "Verified Green Citizen"
    user_ward = user.ward if user else "Ward 7"

    # Precise conversion metrics
    # 1 Eco-point ~ 0.35 kg of CO2 equivalent diverted
    total_co2_kg = round(user_pts * 0.35 + 42.5, 1)
    trees_equiv = round(total_co2_kg / 21.7, 1)  # 1 mature tree absorbs ~21.7 kg CO2/year
    clean_energy_kwh = round(total_co2_kg * 1.85, 1)
    water_saved_liters = round(total_co2_kg * 14.2, 1)
    landfill_diverted_kg = round(total_co2_kg * 1.45, 1)

    # Dynamic ESG Certificate
    cert_hash = hashlib.sha256(f"{user_name}-{user_pts}-{total_co2_kg}".encode()).hexdigest()[:16].upper()
    cert_id = f"ESG-2026-GG-{(user.id if user else 77):04d}"

    return jsonify({
        "carbonMetrics": {
            "totalCo2DivertedKg": total_co2_kg,
            "treesEquivalent": trees_equiv,
            "cleanEnergyKwh": clean_energy_kwh,
            "waterSavedLiters": water_saved_liters,
            "landfillDivertedKg": landfill_diverted_kg,
            "circularScore": "A+ Elite",
            "cityPercentile": "Top 5% Eco Contributor"
        },
        "certificate": {
            "certificateId": cert_id,
            "citizenName": user_name,
            "ward": user_ward,
            "pointsVerified": user_pts,
            "totalCo2Offset": f"{total_co2_kg} kg CO₂e",
            "treesPlanted": f"{trees_equiv} Trees",
            "issueDate": datetime.now(timezone.utc).strftime("%B %d, %Y"),
            "verificationHash": cert_hash,
            "issuingAuthority": "Go Green Smart Urban Waste Authority & UN SDG Alliance"
        }
    }), 200


# ======================================================================
# REWARDS MARKETPLACE & VOUCHERS
# ======================================================================

REWARDS_CATALOG = [
    {
        "id": "metro_pass",
        "title": "1-Day Unlimited Metro Green Pass",
        "partnerName": "Urban Metro Rapid Transit",
        "category": "Mobility",
        "pointsCost": 150,
        "icon": "train",
        "badge": "Popular",
        "description": "Unlimited travel across all metro lines for 24 hours. Reduce your personal transport footprint to zero."
    },
    {
        "id": "tree_plant",
        "title": "Plant a Native Tree in Your Name",
        "partnerName": "Green Earth Urban Forestry",
        "category": "Climate",
        "pointsCost": 300,
        "icon": "trees",
        "badge": "High Impact",
        "description": "A geo-tagged native sapling will be planted in the city green belt with real-time GPS growth tracking."
    },
    {
        "id": "cafe_voucher",
        "title": "₹150 Organic Cafe Coffee & Snack Coupon",
        "partnerName": "Earthy Beans Zero-Waste Cafe",
        "category": "Dining",
        "pointsCost": 250,
        "icon": "coffee",
        "badge": "Special",
        "description": "Enjoy fair-trade organic beverages and snacks served in zero-plastic, 100% compostable ware."
    },
    {
        "id": "eco_kit",
        "title": "Zero-Waste Bamboo Cutlery & Tote Bag Kit",
        "partnerName": "EcoLife Sustainable Goods",
        "category": "Lifestyle",
        "pointsCost": 450,
        "icon": "shopping-bag",
        "badge": "Physical Gift",
        "description": "Handmade organic bamboo utensils, stainless steel straw, and organic cotton shopping bag shipped to your address."
    },
    {
        "id": "solar_pass",
        "title": "Solar EV Charging Station 1-Month Pass",
        "partnerName": "SunPower Urban Grids",
        "category": "Energy",
        "pointsCost": 500,
        "icon": "zap",
        "badge": "EV Special",
        "description": "Free 1-month charging at 50+ city solar-powered two-wheeler and four-wheeler charging kiosks."
    },
    {
        "id": "composter_discount",
        "title": "15% Off Smart Aerobic Home Composter",
        "partnerName": "SmartCompost India",
        "category": "Home",
        "pointsCost": 600,
        "icon": "package",
        "badge": "Home Gear",
        "description": "Convert kitchen waste into nutrient soil in under 14 days with zero odor technology."
    }
]


@dashboard_bp.get("/rewards/catalog")
def get_rewards_catalog():
    """Returns available vouchers and rewards."""
    return jsonify({"catalog": REWARDS_CATALOG}), 200


@dashboard_bp.post("/rewards/redeem")
@login_required
def redeem_reward():
    """Redeems an item from the rewards catalog using user's Eco-Points."""
    user = request.current_user
    data = request.get_json(silent=True) or {}
    item_id = data.get("catalogId")

    catalog_item = next((item for item in REWARDS_CATALOG if item["id"] == item_id), None)
    if not catalog_item:
        return jsonify({"error": "Reward item not found"}), 404

    cost = catalog_item["pointsCost"]
    if user.eco_points < cost:
        return jsonify({
            "error": f"Insufficient Eco-Points. You have {user.eco_points} pts, but this reward requires {cost} pts."
        }), 400

    # Deduct points
    user.eco_points -= cost

    # Generate secure voucher code
    random_suffix = uuid.uuid4().hex[:6].upper()
    voucher_code = f"GG-{catalog_item['id'][:5].upper()}-{random_suffix}"

    voucher = RewardVoucher(
        user_id=user.id,
        voucher_code=voucher_code,
        title=catalog_item["title"],
        partner_name=catalog_item["partnerName"],
        points_cost=cost,
        status="Active"
    )
    db.session.add(voucher)

    # Add notification
    notif = Notification(
        user_id=user.id,
        title="🎟️ Reward Voucher Redeemed!",
        message=f"You successfully redeemed '{catalog_item['title']}' for {cost} Eco-Points. Voucher code: {voucher_code}",
        type="reward"
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Voucher successfully generated!",
        "voucher": voucher.to_dict(),
        "remainingPoints": user.eco_points
    }), 201


@dashboard_bp.get("/rewards/my-vouchers")
@login_required
def get_my_vouchers():
    """Returns all redeemed vouchers for the current user."""
    user = request.current_user
    vouchers = RewardVoucher.query.filter_by(user_id=user.id).order_by(RewardVoucher.created_at.desc()).all()
    return jsonify({"vouchers": [v.to_dict() for v in vouchers]}), 200


# ======================================================================
# IN-APP NOTIFICATIONS
# ======================================================================

@dashboard_bp.get("/notifications")
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


@dashboard_bp.post("/notifications/<int:notif_id>/read")
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


@dashboard_bp.post("/notifications/mark-all-read")
@login_required
def mark_all_notifications_read():
    """Marks all user notifications as read."""
    user = request.current_user
    Notification.query.filter_by(user_id=user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"success": True}), 200

