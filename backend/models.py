from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=True)  # Nullable for Google OAuth users
    google_id = db.Column(db.String(120), nullable=True, unique=True, index=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    auth_provider = db.Column(db.String(20), default="local", nullable=False)  # 'local', 'google'
    role = db.Column(db.String(20), default="citizen", nullable=False)  # citizen, admin, collector
    ward = db.Column(db.String(50), default="Ward 7", nullable=False)

    eco_points = db.Column(db.Integer, default=0, nullable=False)
    level = db.Column(db.String(60), default="Green Beginner", nullable=False)
    streak_days = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    reports = db.relationship("WasteReport", backref="user", lazy=True, cascade="all, delete-orphan")
    schedules = db.relationship("CollectionSchedule", backref="user", lazy=True, cascade="all, delete-orphan")
    badges = db.relationship("RewardBadge", backref="user", lazy=True, cascade="all, delete-orphan")
    vouchers = db.relationship("RewardVoucher", backref="user", lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship("Notification", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, raw_password):
        if raw_password:
            self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        if not self.password_hash or self.password_hash.startswith("GOOGLE_OAUTH_"):
            return False
        return check_password_hash(self.password_hash, raw_password)

    def add_points(self, amount):
        self.eco_points = (self.eco_points or 0) + amount
        if self.eco_points >= 1500:
            self.level = "Planet Protector"
        elif self.eco_points >= 1000:
            self.level = "Eco Warrior"
        elif self.eco_points >= 500:
            self.level = "Recycling Hero"
        else:
            self.level = "Green Beginner"

    def get_initials(self):
        parts = self.name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        elif parts:
            return parts[0][:2].upper()
        return "GG"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "ward": self.ward,
            "googleId": self.google_id,
            "avatarUrl": self.avatar_url,
            "authProvider": self.auth_provider,
            "initials": self.get_initials(),
            "ecoPoints": self.eco_points,
            "level": self.level,
            "streakDays": self.streak_days,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "badges": [b.to_dict() for b in self.badges] if self.badges else [],
        }


class WasteReport(db.Model):
    __tablename__ = "waste_reports"

    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.String(40), unique=True, index=True, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), nullable=False)
    waste_type = db.Column(db.String(60), nullable=False)
    waste_category = db.Column(db.String(80), nullable=True)
    location = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    location_accuracy = db.Column(db.Float, nullable=True)  # in meters
    ward = db.Column(db.String(50), default="Ward 7", nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)

    status = db.Column(db.String(40), default="Submitted to GoGreen", nullable=False)
    priority = db.Column(db.String(20), default="Medium", nullable=False)
    severity = db.Column(db.String(20), default="Medium", nullable=False)  # Low, Medium, High, Critical

    assigned_department = db.Column(db.String(120), nullable=True)
    assigned_team = db.Column(db.String(120), nullable=True)
    official_reference_id = db.Column(db.String(80), nullable=True)

    resolution_image_filename = db.Column(db.String(255), nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)

    status_history = db.relationship(
        "ComplaintStatusLog",
        backref="report",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="ComplaintStatusLog.created_at.desc()"
    )

    def to_dict(self, include_history=True):
        cid = self.complaint_id or f"GG-GRB-2026-{self.id:04d}"
        data = {
            "id": self.id,
            "complaintId": cid,
            "userId": self.user_id,
            "name": self.name,
            "email": self.email,
            "wasteType": self.waste_type,
            "wasteCategory": self.waste_category or self.waste_type,
            "location": self.location,
            "address": self.address or self.location,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "locationAccuracy": self.location_accuracy,
            "ward": self.ward,
            "description": self.description,
            "imageUrl": f"/api/uploads/{self.image_filename}" if self.image_filename else None,
            "resolutionImageUrl": f"/api/uploads/{self.resolution_image_filename}" if self.resolution_image_filename else None,
            "resolutionNotes": self.resolution_notes,
            "status": self.status,
            "priority": self.priority or self.severity or "Medium",
            "severity": self.severity or self.priority or "Medium",
            "assignedDepartment": self.assigned_department,
            "assignedTeam": self.assigned_team,
            "officialReferenceId": self.official_reference_id,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else (self.created_at.isoformat() if self.created_at else None),
            "resolvedAt": self.resolved_at.isoformat() if self.resolved_at else None,
        }
        if include_history:
            data["statusHistory"] = [log.to_dict() for log in self.status_history] if self.status_history else []
        return data


class ComplaintStatusLog(db.Model):
    __tablename__ = "complaint_status_logs"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("waste_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status = db.Column(db.String(50), nullable=True)
    to_status = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    official_reference = db.Column(db.String(80), nullable=True)
    updated_by = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "reportId": self.report_id,
            "fromStatus": self.from_status,
            "toStatus": self.to_status,
            "action": self.action,
            "notes": self.notes,
            "officialReference": self.official_reference,
            "updatedBy": self.updated_by,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class CollectionSchedule(db.Model):
    __tablename__ = "collection_schedules"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    waste_type = db.Column(db.String(60), nullable=False)
    pickup_date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(60), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    notes = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), default="Scheduled", nullable=False)  # Scheduled / In Progress / Completed / Cancelled
    reference = db.Column(db.String(20), nullable=False, unique=True, index=True)  # e.g. GG-8842
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "reference": self.reference,
            "wasteType": self.waste_type,
            "date": self.pickup_date.isoformat() if self.pickup_date else None,
            "timeSlot": self.time_slot,
            "address": self.address,
            "notes": self.notes,
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


# Alias for backward compatibility
PickupSchedule = CollectionSchedule


class SensorBin(db.Model):
    __tablename__ = "sensor_bins"

    id = db.Column(db.Integer, primary_key=True)
    sensor_code = db.Column(db.String(30), default="IOT-BIN-01", nullable=False)
    ward_number = db.Column(db.String(20), nullable=False)  # e.g. "Ward 4"
    location_name = db.Column(db.String(120), nullable=False)
    fill_level = db.Column(db.Integer, default=0, nullable=False)  # Percentage 0-100
    temperature = db.Column(db.Float, default=26.5, nullable=False)  # Celsius
    battery_level = db.Column(db.Integer, default=95, nullable=False)  # %
    is_dispatched = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(20), default="low", nullable=False)  # low / mid / high / critical
    last_updated = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "sensorCode": self.sensor_code or f"IOT-W{self.ward_number[-1] if self.ward_number else '1'}-{self.id:02d}",
            "ward": self.ward_number,
            "location": self.location_name,
            "fillLevel": self.fill_level,
            "temperature": round(self.temperature, 1) if self.temperature else 26.5,
            "batteryLevel": self.battery_level or 95,
            "isDispatched": self.is_dispatched or False,
            "status": "critical" if self.fill_level >= 80 else ("high" if self.fill_level >= 65 else ("mid" if self.fill_level >= 40 else "low")),
            "lastUpdated": self.last_updated.isoformat() if self.last_updated else None,
        }


class RewardBadge(db.Model):
    __tablename__ = "reward_badges"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    icon = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    unlocked_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "description": self.description,
            "unlockedAt": self.unlocked_at.isoformat() if self.unlocked_at else None,
        }


class RewardVoucher(db.Model):
    __tablename__ = "reward_vouchers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    voucher_code = db.Column(db.String(40), nullable=False, unique=True, index=True)
    title = db.Column(db.String(150), nullable=False)
    partner_name = db.Column(db.String(100), nullable=False)
    points_cost = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="Active", nullable=False)  # Active / Redeemed / Expired
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "voucherCode": self.voucher_code,
            "title": self.title,
            "partnerName": self.partner_name,
            "pointsCost": self.points_cost,
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(30), default="system", nullable=False)  # reward / report / pickup / sensor
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "title": self.title,
            "message": self.message,
            "type": self.type,
            "isRead": self.is_read,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }

