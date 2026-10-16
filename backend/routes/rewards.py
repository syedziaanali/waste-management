import uuid
from flask import Blueprint, jsonify, request
from extensions import db
from models import RewardVoucher, Notification, User
from auth_utils import login_required, optional_login

rewards_bp = Blueprint("rewards", __name__, url_prefix="/api/rewards")

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


@rewards_bp.get("/catalog")
def get_rewards_catalog():
    """Returns available vouchers and rewards."""
    return jsonify({"catalog": REWARDS_CATALOG}), 200


@rewards_bp.post("/redeem")
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


@rewards_bp.get("/my-vouchers")
@login_required
def get_my_vouchers():
    """Returns all redeemed vouchers for the current user."""
    user = request.current_user
    vouchers = RewardVoucher.query.filter_by(user_id=user.id).order_by(RewardVoucher.created_at.desc()).all()
    return jsonify({"vouchers": [v.to_dict() for v in vouchers]}), 200
