from datetime import datetime, timedelta, timezone
from extensions import db
from models import User, WasteReport, CollectionSchedule, SensorBin, RewardBadge, RewardVoucher, Notification


def seed_database():
    # Only seed if no users exist
    if User.query.first():
        return

    print("[Go Green Seed] Populating database with sample data...")

    # 1. Users
    ananya = User(
        name="Ananya Sharma",
        email="ananya@example.com",
        ward="Ward 7",
        eco_points=850,
        level="Recycling Hero",
        streak_days=14,
        role="citizen"
    )
    ananya.set_password("password123")

    aarav = User(
        name="Aarav Sharma",
        email="aarav@example.com",
        ward="Ward 4",
        eco_points=1120,
        level="Eco Warrior",
        streak_days=21,
        role="citizen"
    )
    aarav.set_password("password123")

    admin = User(
        name="Ward Supervisor",
        email="admin@gogreen.city",
        ward="Central Ward",
        eco_points=2500,
        level="Planet Protector",
        streak_days=45,
        role="admin"
    )
    admin.set_password("admin123")

    db.session.add_all([ananya, aarav, admin])
    db.session.flush()

    # 2. Badges
    badges = [
        RewardBadge(user_id=ananya.id, name="Green Beginner", icon="🌱", description="Joined the Go Green movement"),
        RewardBadge(user_id=ananya.id, name="Recycling Hero", icon="♻️", description="Sorted & reported 15+ items"),
        RewardBadge(user_id=aarav.id, name="Green Beginner", icon="🌱", description="Joined the Go Green movement"),
        RewardBadge(user_id=aarav.id, name="Recycling Hero", icon="♻️", description="Sorted & reported 15+ items"),
        RewardBadge(user_id=aarav.id, name="Eco Warrior", icon="🌍", description="Achieved 1000+ Eco Points"),
    ]
    db.session.add_all(badges)

    # 3. Sensor Bins (for Hero Live Sensor Feed and IoT Dispatch Hub)
    sensor_bins = [
        SensorBin(sensor_code="IOT-W4-01", ward_number="Ward 4", location_name="Market Road Central", fill_level=24, temperature=25.2, battery_level=96, status="low"),
        SensorBin(sensor_code="IOT-W9-02", ward_number="Ward 9", location_name="Greenfield Ave North", fill_level=62, temperature=27.1, battery_level=89, status="mid"),
        SensorBin(sensor_code="IOT-W2-03", ward_number="Ward 2", location_name="Central Metro Plaza", fill_level=88, temperature=29.4, battery_level=78, status="critical"),
        SensorBin(sensor_code="IOT-W7-04", ward_number="Ward 7", location_name="Lakeview Colony Gate", fill_level=18, temperature=24.8, battery_level=98, status="low"),
        SensorBin(sensor_code="IOT-W1-05", ward_number="Ward 1", location_name="MG Road High Street", fill_level=79, temperature=28.3, battery_level=84, status="high"),
        SensorBin(sensor_code="IOT-W6-06", ward_number="Ward 6", location_name="Highland Tech Park", fill_level=35, temperature=25.9, battery_level=92, status="low"),
        SensorBin(sensor_code="IOT-W3-07", ward_number="Ward 3", location_name="Civic Center Square", fill_level=76, temperature=28.0, battery_level=81, status="high"),
        SensorBin(sensor_code="IOT-W5-08", ward_number="Ward 5", location_name="Riverside Promenade", fill_level=42, temperature=26.0, battery_level=94, status="mid"),
        SensorBin(sensor_code="IOT-W8-09", ward_number="Ward 8", location_name="Suburban Rail Station", fill_level=85, temperature=29.8, battery_level=75, status="critical"),
    ]
    db.session.add_all(sensor_bins)

    now = datetime.now(timezone.utc)

    # 4. Waste Reports
    reports = [
        WasteReport(
            user_id=ananya.id,
            name="Ananya Sharma",
            email="ananya@example.com",
            waste_type="Plastic Waste",
            location="Overflowing bin — MG Road",
            ward="Ward 1",
            description="Public bin near metro gate 2 is full and plastics are spilling onto sidewalk.",
            status="Resolved",
            priority="High",
            created_at=now - timedelta(days=2),
            resolved_at=now - timedelta(days=1)
        ),
        WasteReport(
            user_id=ananya.id,
            name="Ananya Sharma",
            email="ananya@example.com",
            waste_type="Mixed Waste",
            location="Illegal dumping — Sector 5",
            ward="Ward 7",
            description="Construction debris and mixed bags left near the vacant plot.",
            status="In Progress",
            priority="Medium",
            created_at=now - timedelta(days=1)
        ),
        WasteReport(
            user_id=ananya.id,
            name="Ananya Sharma",
            email="ananya@example.com",
            waste_type="E-Waste",
            location="E-waste pickup — Park St",
            ward="Ward 7",
            description="Box with discarded monitors and cables ready for specialized collection.",
            status="Pending",
            priority="Low",
            created_at=now - timedelta(hours=4)
        ),
        WasteReport(
            user_id=aarav.id,
            name="Aarav Sharma",
            email="aarav@example.com",
            waste_type="Organic Waste",
            location="Community Garden — Ward 4",
            ward="Ward 4",
            description="Large pile of fallen branches and grass clippings after storm.",
            status="Resolved",
            priority="Medium",
            created_at=now - timedelta(days=4),
            resolved_at=now - timedelta(days=3)
        ),
    ]
    db.session.add_all(reports)

    # 5. Collection Schedules
    tomorrow = (now + timedelta(days=1)).date()
    next_week = (now + timedelta(days=4)).date()

    schedules = [
        CollectionSchedule(
            user_id=ananya.id,
            reference="GG-8842",
            waste_type="Mixed Recyclables",
            pickup_date=tomorrow,
            time_slot="9:00 – 11:00 AM",
            address="12 Lakeview Colony, Ward 7",
            notes="Cardboard boxes broken down and tied neatly at the main gate.",
            status="Scheduled"
        ),
        CollectionSchedule(
            user_id=aarav.id,
            reference="GG-4120",
            waste_type="E-Waste",
            pickup_date=next_week,
            time_slot="2:00 – 4:00 PM",
            address="45 Market Street, Ward 4",
            notes="Old computer printer and lithium batteries.",
            status="Scheduled"
        ),
    ]
    db.session.add_all(schedules)

    # 6. Sample Vouchers
    vouchers = [
        RewardVoucher(
            user_id=ananya.id,
            voucher_code="GG-METRO-4B9E81",
            title="1-Day Unlimited Metro Green Pass",
            partner_name="Urban Metro Rapid Transit",
            points_cost=150,
            status="Active",
            created_at=now - timedelta(days=2)
        ),
        RewardVoucher(
            user_id=ananya.id,
            voucher_code="GG-CAFE-7F3A22",
            title="₹150 Organic Cafe Coffee & Snack Coupon",
            partner_name="Earthy Beans Zero-Waste Cafe",
            points_cost=250,
            status="Active",
            created_at=now - timedelta(days=5)
        ),
    ]
    db.session.add_all(vouchers)

    # 7. Sample Notifications
    notifications = [
        Notification(
            user_id=ananya.id,
            title="🌱 Eco Points Milestone Reached",
            message="Congratulations! You earned +100 bonus Eco Points for 14-day recycling streak.",
            type="reward",
            is_read=False,
            created_at=now - timedelta(hours=2)
        ),
        Notification(
            user_id=ananya.id,
            title="🚛 Collection Route Confirmed",
            message="Your door-to-door pickup (Ref #GG-8842) is confirmed for tomorrow 9:00 AM.",
            type="pickup",
            is_read=False,
            created_at=now - timedelta(hours=6)
        ),
        Notification(
            user_id=ananya.id,
            title="🎟️ Metro Pass Active",
            message="Your Metro Green Pass voucher GG-METRO-4B9E81 is active and valid for the next 28 days.",
            type="reward",
            is_read=True,
            created_at=now - timedelta(days=2)
        ),
    ]
    db.session.add_all(notifications)

    db.session.commit()
    print("[Go Green Seed] Sample data successfully inserted!")


if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        seed_database()
