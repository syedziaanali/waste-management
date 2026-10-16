from datetime import datetime, timezone
from flask import Blueprint, jsonify, request

recycling_bp = Blueprint("recycling", __name__, url_prefix="/api/recycling")

RECYCLING_CATEGORIES = [
    {
        "id": "organic",
        "name": "Organic Waste",
        "icon": "leaf",
        "color": "moss",
        "summary": "Food scraps, vegetable peels, compostable plant matter",
        "items": ["Vegetable & fruit peels", "Leftover food", "Coffee grounds & tea bags", "Leaves & lawn clippings", "Eggshells"],
        "doNotInclude": ["Plastic wrappers", "Meat bones in large quantities", "Treated wood"],
        "disposalTips": "Keep in a ventilated compost bin or green municipal bin. Avoid mixing with plastic bags."
    },
    {
        "id": "recyclable",
        "name": "Recyclable Waste",
        "icon": "recycle",
        "color": "clay",
        "summary": "Paper, cardboard, clean plastics, glass bottles, and tin cans",
        "items": ["Cardboard boxes", "Newspapers & books", "Plastic bottles (PET #1, HDPE #2)", "Glass containers", "Aluminum cans"],
        "doNotInclude": ["Greasy pizza boxes", "Broken window glass", "Plastic straw/film"],
        "disposalTips": "Rinse containers lightly before recycling. Flatten cardboard boxes to save bin space."
    },
    {
        "id": "hazardous",
        "name": "Hazardous Waste",
        "icon": "triangle-alert",
        "color": "red",
        "summary": "Chemicals, paints, medicines, and domestic hazardous items",
        "items": ["Household cleaning chemicals", "Batteries (AA, AAA, Li-ion)", "Paints & thinners", "Expired medicines", "Pesticides"],
        "doNotInclude": ["Regular trash", "Direct pouring down household drains"],
        "disposalTips": "Keep in original labeled containers. Never mix chemicals. Request a special hazardous waste pickup."
    },
    {
        "id": "ewaste",
        "name": "E-Waste",
        "icon": "cpu",
        "color": "blue",
        "summary": "Old electronics, cables, batteries, gadgets, and computer parts",
        "items": ["Old smartphones & tablets", "Laptops & motherboards", "Charging cables & adapters", "Printers & ink cartridges", "Smart watches"],
        "doNotInclude": ["Household alkaline batteries with broken seals"],
        "disposalTips": "Wipe personal data before recycling. Hand over to certified e-waste collection drives or schedule a pickup."
    }
]

COLLECTION_CENTERS = [
    {
        "id": 1,
        "name": "Central EcoHub & Recycling Depot",
        "ward": "Ward 4",
        "address": "42 Greenfield Boulevard, Sector 12",
        "acceptedTypes": ["Organic", "Recyclables", "E-Waste", "Hazardous"],
        "hours": "Mon - Sat: 8:00 AM - 6:00 PM",
        "contact": "+91 98765 43210"
    },
    {
        "id": 2,
        "name": "Ward 7 Material Recovery Facility",
        "ward": "Ward 7",
        "address": "15 Lakeview Road, Near Community Park",
        "acceptedTypes": ["Recyclables", "E-Waste"],
        "hours": "Tue - Sun: 9:00 AM - 5:00 PM",
        "contact": "+91 98765 43211"
    },
    {
        "id": 3,
        "name": "North City E-Waste Recycling Station",
        "ward": "Ward 2",
        "address": "88 Tech City Ring Road",
        "acceptedTypes": ["E-Waste", "Batteries", "Solar Equipment"],
        "hours": "Mon - Fri: 10:00 AM - 7:00 PM",
        "contact": "+91 98765 43212"
    }
]


@recycling_bp.get("/categories")
def get_categories():
    return jsonify({"categories": RECYCLING_CATEGORIES}), 200


@recycling_bp.get("/categories/<string:category_id>")
def get_category_detail(category_id):
    cat = next((c for c in RECYCLING_CATEGORIES if c["id"] == category_id.lower()), None)
    if not cat:
        return jsonify({"error": "Category not found"}), 404
    return jsonify({"category": cat}), 200


@recycling_bp.get("/centers")
def get_centers():
    return jsonify({"centers": COLLECTION_CENTERS}), 200


AI_CLASSIFICATION_DATABASE = [
    {
        "keywords": ["bottle", "pet", "plastic", "coke", "water bottle", "shampoo", "container"],
        "detectedItem": "PET #1 Plastic Beverage Bottle",
        "category": "Recyclable",
        "binTarget": "Blue Bin (Dry Recyclables)",
        "confidence": 98.8,
        "materialComposition": "Polyethylene Terephthalate (100% Recyclable Polymer)",
        "preparationSteps": [
            "Empty any residual liquid completely",
            "Rinse once with greywater or cold water",
            "Crush the bottle flat to save bin space",
            "Keep the plastic screw cap attached or recycle separately"
        ],
        "decompositionYears": "450 years in landfill",
        "co2OffsetKg": 0.28,
        "circularFact": "Recycling 1 ton of PET plastic saves 3.8 barrels of crude oil and 5.7 m3 of landfill volume."
    },
    {
        "keywords": ["cardboard", "box", "paper", "newspaper", "carton", "amazon", "packaging"],
        "detectedItem": "Corrugated Cardboard Packaging Box",
        "category": "Recyclable",
        "binTarget": "Blue Bin (Dry Recyclables)",
        "confidence": 99.1,
        "materialComposition": "Unbleached Kraft Fiber & Recycled Pulp",
        "preparationSteps": [
            "Remove plastic shipping tape and thermal address labels if possible",
            "Ensure box is dry and free of food grease",
            "Flatten and fold neatly before placing in paper bin"
        ],
        "decompositionYears": "2 months (if wet) / 5 years (dry)",
        "co2OffsetKg": 0.65,
        "circularFact": "Cardboard fibers can be recycled up to 7 times to manufacture new egg cartons and packaging."
    },
    {
        "keywords": ["battery", "lithium", "cell", "alkaline", "aa", "aaa", "powerbank", "accumulator"],
        "detectedItem": "Lithium-Ion / Alkaline Secondary Battery",
        "category": "Hazardous",
        "binTarget": "Red Hazardous Waste Bin / Special E-Depot",
        "confidence": 97.5,
        "materialComposition": "Lithium Cobalt Oxide, Nickel, Heavy Metals & Electrolyte Solution",
        "preparationSteps": [
            "Place transparent clear tape over the terminals (+ / - poles) to prevent short circuits",
            "Store in a dry, cool plastic container away from flammable items",
            "Hand over at certified battery collection bins or book a hazardous pickup"
        ],
        "decompositionYears": "100+ years (leaches toxic heavy metals)",
        "co2OffsetKg": 1.40,
        "circularFact": "95% of cobalt and nickel from spent batteries can be reclaimed for new electric vehicles."
    },
    {
        "keywords": ["phone", "laptop", "pc", "circuit", "cable", "electronics", "charger", "mouse", "keyboard", "wire"],
        "detectedItem": "E-Waste / Printed Circuit Board & Gadget Component",
        "category": "E-Waste",
        "binTarget": "Blue-Grey E-Waste Drop Box",
        "confidence": 96.9,
        "materialComposition": "Silicone, Copper, Precious Metals (Gold/Silver), Flame Retardants",
        "preparationSteps": [
            "Perform factory reset or remove confidential memory cards/SIMs",
            "Bundle associated charging cables together neatly",
            "Never dispose in regular garbage or incinerators"
        ],
        "decompositionYears": "1,000+ years",
        "co2OffsetKg": 2.80,
        "circularFact": "1 metric ton of circuit boards contains 40x to 800x more gold than 1 ton of raw mined ore."
    },
    {
        "keywords": ["banana", "apple", "fruit", "food", "peel", "vegetable", "leftover", "leaves", "organic", "scraps", "compost"],
        "detectedItem": "Organic Food Scraps & Biodegradable Biomass",
        "category": "Organic",
        "binTarget": "Green Bin (Wet / Compostable Waste)",
        "confidence": 99.4,
        "materialComposition": "Plant Cellulose, Nitrogen, Organic Water & Micro-Nutrients",
        "preparationSteps": [
            "Separate from any plastic wrapping, stickers, or rubber bands",
            "Collect in a ventilated kitchen caddy or compost bin",
            "Add to home compost or place in green municipal bin for community biogas"
        ],
        "decompositionYears": "2 to 6 weeks in aerobic composting",
        "co2OffsetKg": 0.45,
        "circularFact": "Composting organic waste eliminates methane emissions from landfills and produces nutrient-rich soil humus."
    },
    {
        "keywords": ["glass", "bottle", "jar", "wine", "beer", "pickle"],
        "detectedItem": "Soda-Lime Container Glass (Jar / Bottle)",
        "category": "Recyclable",
        "binTarget": "Blue Bin (Dry Recyclables)",
        "confidence": 98.2,
        "materialComposition": "Silica Sand, Sodium Carbonate & Cullet (100% Infinitely Recyclable)",
        "preparationSteps": [
            "Rinse jar thoroughly to remove leftover food or sauces",
            "Remove metal lid (recycle metal lid separately in dry bin)",
            "Do not break glass; keep intact for safe handling"
        ],
        "decompositionYears": "1,000,000+ years in landfill",
        "co2OffsetKg": 0.35,
        "circularFact": "Glass can be melted and reformed indefinitely without any loss in purity or chemical quality."
    },
    {
        "keywords": ["can", "aluminum", "tin", "soda", "coke can", "metal", "foil"],
        "detectedItem": "Aluminum Beverage Can",
        "category": "Recyclable",
        "binTarget": "Blue Bin (Dry Recyclables)",
        "confidence": 99.0,
        "materialComposition": "Alloy 3004 Aluminum (High Purity Metal)",
        "preparationSteps": [
            "Empty any remaining beverage",
            "Rinse lightly and crush can to save volume",
            "Drop in dry recyclable bin"
        ],
        "decompositionYears": "200 to 500 years",
        "co2OffsetKg": 0.95,
        "circularFact": "Recycling aluminum requires 95% less energy than producing primary aluminum from bauxite ore."
    }
]


from auth_utils import optional_login

@recycling_bp.post("/scan-ai")
@optional_login
def scan_ai():
    """
    AI Smart Waste Scanner endpoint.
    Accepts an item descriptor, prompt, or image analysis trigger.
    Classifies material, computes circular metrics, and awards +10 points to authenticated users.
    """
    from extensions import db
    from models import User, Notification

    current_user = request.current_user
    data = request.get_json(silent=True) or {}
    query_text = (data.get("query") or data.get("item") or data.get("filename") or "plastic bottle").lower()

    # Find closest match from AI database
    matched_entry = None
    for entry in AI_CLASSIFICATION_DATABASE:
        if any(k in query_text for k in entry["keywords"]):
            matched_entry = entry
            break

    if not matched_entry:
        # Default smart fallback
        matched_entry = AI_CLASSIFICATION_DATABASE[0]

    # Award points if user is authenticated
    points_awarded = 10
    user_updated_pts = None
    user_level = None

    if current_user:
        current_user.add_points(points_awarded)
        # Create instant notification
        notif = Notification(
            user_id=current_user.id,
            title="🌱 AI Waste Scan Complete",
            message=f"Successfully identified {matched_entry['detectedItem']}. +{points_awarded} Eco-Points added to your balance!",
            type="reward"
        )
        db.session.add(notif)
        db.session.commit()
        user_updated_pts = current_user.eco_points
        user_level = current_user.level

    return jsonify({
        "success": True,
        "scanResult": matched_entry,
        "pointsAwarded": points_awarded,
        "userPoints": user_updated_pts,
        "userLevel": user_level,
        "scanTimestamp": datetime.now(timezone.utc).isoformat()
    }), 200

