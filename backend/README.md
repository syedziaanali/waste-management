# Go Green — Flask Backend API

A production-grade Python + Flask backend for the **Go Green** Smart Waste Management platform. Powered by SQLite and SQLAlchemy with zero complex setup, JWT authentication, multipart image uploads, live sensors simulation, and gamified eco-points.

---

## 1. Quick Start

### Prerequisites
- Python 3.10+ installed

### Run Backend Server
```bash
# 1. Open a terminal in the backend directory
cd backend

# 2. Run the server
python app.py
```

The API will start at `http://127.0.0.1:5000`. On first start, SQLite (`gogreen.db`) is automatically initialized and seeded with realistic demo data.

---

## 2. Demo User Accounts

| Role | Email | Password | Details |
|------|-------|----------|---------|
| **Citizen (Ananya)** | `ananya@example.com` | `password123` | 850 Eco Points · Level 4 (Recycling Hero) · 14 day streak |
| **Citizen (Aarav)** | `aarav@example.com` | `password123` | 1120 Eco Points · Level 5 (Eco Warrior) · 21 day streak |
| **Ward Admin** | `admin@gogreen.city` | `admin123` | Ward Supervisor access |

---

## 3. API Endpoints

### 🔐 Authentication (`/api/auth`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/auth/signup` | — | Register citizen (`name`, `email`, `password`, `ward`) + 100 welcome bonus pts |
| `POST` | `/api/auth/login` | — | Sign in with email & password |
| `GET` | `/api/auth/me` | Bearer | Current user profile & earned badges |
| `PUT` | `/api/auth/profile` | Bearer | Update profile info (name, ward, password) |

### 🗑️ Waste Reporting (`/api/reports`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/reports` | Optional | Submit waste report (multipart form or JSON) with image upload |
| `GET` | `/api/reports` | Optional | List reports with optional `?mine=true&status=...&ward=...` |
| `GET` | `/api/reports/<id>` | — | Get single report details |
| `PATCH` | `/api/reports/<id>/status` | — | Update status (`Pending`, `In Progress`, `Resolved`) |
| `DELETE` | `/api/reports/<id>` | Bearer | Delete report |
| `GET` | `/api/uploads/<filename>` | — | Serve uploaded report photos |

### 📅 Collection Scheduling (`/api/schedule`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/schedule` | Optional | Book pickup slot (`wasteType`, `date`, `timeSlot`, `address`, `notes`) |
| `GET` | `/api/schedule` | Optional | List scheduled pickups (`?mine=true&status=...`) |
| `GET` | `/api/schedule/<id>` | — | Get pickup details |
| `GET` | `/api/schedule/ref/<ref>` | — | Lookup pickup by reference code (e.g. `GG-8842`) |
| `PATCH` | `/api/schedule/<id>/status`| — | Update status (`Scheduled`, `In Progress`, `Completed`, `Cancelled`) |
| `DELETE` | `/api/schedule/<id>` | Bearer | Cancel pickup |

### 📊 Dashboard & Metrics (`/api/dashboard`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/dashboard/stats` | — | Live citywide counters for hero cards |
| `GET` | `/api/dashboard/activity` | Optional | 7-day collected & recycled trends for Chart.js |
| `GET` | `/api/dashboard/rewards` | Optional | User Eco Points, tier level, streak, next milestone |
| `GET` | `/api/dashboard/bins` | — | Live fill-level simulation across city wards (Ward 1–9) |
| `GET` | `/api/dashboard/overview` | Optional | Bundled summary for dashboard widgets |

### ♻️ Recycling Guide (`/api/recycling`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/recycling/categories` | — | Waste segregation guide (Organic, Recyclables, Hazardous, E-Waste) |
| `GET` | `/api/recycling/categories/<id>` | — | Detailed tips for a specific category |
| `GET` | `/api/recycling/centers` | — | Nearby city drop-off centers and timings |

---

## 4. Running Tests

Run the full automated test suite anytime:
```bash
python test_backend.py
```
