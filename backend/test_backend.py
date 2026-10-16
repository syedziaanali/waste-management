import sys
import os
import unittest
import json
import io
import uuid

# Ensure backend directory is in Python path
BACKEND_DIR = os.path.abspath(os.path.dirname(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app
from extensions import db
from models import User, WasteReport, CollectionSchedule, SensorBin, RewardBadge


class TestGoGreenBackend(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_01_health_and_index(self):
        # Health check
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json().get("status"), "ok")

        # API info route
        api_res = self.client.get("/api")
        self.assertEqual(api_res.status_code, 200)
        self.assertIn("endpoints", api_res.get_json())

        # Frontend index website route
        index_res = self.client.get("/")
        self.assertEqual(index_res.status_code, 200)
        self.assertIn("Go Green", index_res.data.decode("utf-8"))

        # Frontend login page
        login_page_res = self.client.get("/login.html")
        self.assertEqual(login_page_res.status_code, 200)

        # Frontend signup page
        signup_page_res = self.client.get("/signup.html")
        self.assertEqual(signup_page_res.status_code, 200)

        # Frontend dashboard page
        dash_res = self.client.get("/dashboard")
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn("Dashboard", dash_res.data.decode("utf-8"))

    def test_02_auth_signup_and_login(self):
        unique_email = f"citizen_{uuid.uuid4().hex[:8]}@test.com"
        signup_res = self.client.post("/api/auth/signup", json={
            "name": "Rohan Kumar",
            "email": unique_email,
            "password": "securepass123",
            "ward": "Ward 2"
        })
        self.assertEqual(signup_res.status_code, 201)
        data = signup_res.get_json()
        self.assertIn("token", data)
        self.assertEqual(data["user"]["name"], "Rohan Kumar")
        self.assertEqual(data["user"]["ecoPoints"], 100)
        rohan_token = data["token"]

        dup_res = self.client.post("/api/auth/signup", json={
            "name": "Rohan Clone",
            "email": unique_email,
            "password": "securepass123"
        })
        self.assertEqual(dup_res.status_code, 409)
        self.assertEqual(dup_res.get_json().get("error"), "You have already registered. Please log in.")
        self.assertTrue(dup_res.get_json().get("alreadyRegistered"))

        # Check email availability endpoint
        chk_res = self.client.get(f"/api/auth/check-email?email={unique_email}")
        self.assertEqual(chk_res.status_code, 200)
        self.assertTrue(chk_res.get_json().get("exists"))

        login_res = self.client.post("/api/auth/login", json={
            "email": unique_email,
            "password": "securepass123"
        })
        self.assertEqual(login_res.status_code, 200)

        me_res = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {rohan_token}"})
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.get_json()["user"]["email"], unique_email)

        up_res = self.client.put("/api/auth/profile", json={"ward": "Ward 9"}, headers={"Authorization": f"Bearer {rohan_token}"})
        self.assertEqual(up_res.status_code, 200)
        self.assertEqual(up_res.get_json()["user"]["ward"], "Ward 9")

    def test_02b_google_oauth(self):
        # Auth config endpoint
        cfg_res = self.client.get("/api/auth/config")
        self.assertEqual(cfg_res.status_code, 200)
        self.assertIn("methods", cfg_res.get_json())

        # Google Sign-In New User
        google_email = f"google_user_{uuid.uuid4().hex[:6]}@gmail.com"
        g_res = self.client.post("/api/auth/google", json={
            "email": google_email,
            "name": "Google Tester",
            "picture": "https://example.com/avatar.jpg",
            "googleId": f"gid_{uuid.uuid4().hex[:10]}"
        })
        self.assertEqual(g_res.status_code, 200)
        data = g_res.get_json()
        self.assertTrue(data.get("isNew"))
        self.assertEqual(data["user"]["email"], google_email)
        self.assertEqual(data["user"]["authProvider"], "google")
        self.assertEqual(data["user"]["ecoPoints"], 100)
        g_token = data["token"]

        # Attempt to sign up again with same Google account (mode="signup") -> must be rejected with 409
        dup_g_res = self.client.post("/api/auth/google", json={
            "email": google_email,
            "name": "Google Tester",
            "googleId": data["user"]["googleId"],
            "mode": "signup"
        })
        self.assertEqual(dup_g_res.status_code, 409)
        self.assertEqual(dup_g_res.get_json().get("error"), "You have already registered. Please log in.")
        self.assertTrue(dup_g_res.get_json().get("alreadyRegistered"))

        # Authenticate again with same Google account in login mode (Existing user login)
        g_res2 = self.client.post("/api/auth/google", json={
            "email": google_email,
            "name": "Google Tester",
            "googleId": data["user"]["googleId"],
            "mode": "login"
        })
        self.assertEqual(g_res2.status_code, 200)
        self.assertFalse(g_res2.get_json().get("isNew"))

        # Verify /api/auth/me works with Google JWT
        me_res = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {g_token}"})
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.get_json()["user"]["email"], google_email)

    def test_03_reports_flow_with_image(self):
        login_res = self.client.post("/api/auth/login", json={
            "email": "ananya@example.com",
            "password": "password123"
        })
        token = login_res.get_json()["token"]

        image_data = io.BytesIO(b"fake image data simulation")
        image_data.name = "sample_waste.jpg"

        res = self.client.post(
            "/api/reports",
            data={
                "repName": "Ananya Sharma",
                "repEmail": "ananya@example.com",
                "repType": "Organic Waste",
                "repLocation": "Green Park, Ward 7",
                "repDesc": "Fallen tree branch blocking walkway",
                "repImage": (image_data, "sample_waste.jpg")
            },
            headers={"Authorization": f"Bearer {token}"},
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        report_id = data["report"]["id"]
        self.assertIsNotNone(data["report"]["imageUrl"])

        get_res = self.client.get(f"/api/reports/{report_id}")
        self.assertEqual(get_res.status_code, 200)

        patch_res = self.client.patch(f"/api/reports/{report_id}/status", json={"status": "In Progress"})
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.get_json()["report"]["status"], "In Progress")

        list_res = self.client.get("/api/reports?mine=true", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(list_res.status_code, 200)
        self.assertTrue(len(list_res.get_json()["reports"]) >= 1)

    def test_04_schedule_flow(self):
        res = self.client.post("/api/schedule", json={
            "wasteType": "E-Waste",
            "date": "2026-11-20",
            "timeSlot": "4:00 – 6:00 PM",
            "address": "Flat 304, Green Heights, Ward 4",
            "notes": "Fragile CRT monitor"
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        ref = data["reference"]

        ref_res = self.client.get(f"/api/schedule/ref/{ref}")
        self.assertEqual(ref_res.status_code, 200)
        self.assertEqual(ref_res.get_json()["schedule"]["wasteType"], "E-Waste")

    def test_05_dashboard_metrics_and_rewards(self):
        stats_res = self.client.get("/api/dashboard/stats")
        self.assertEqual(stats_res.status_code, 200)
        stats = stats_res.get_json()
        self.assertGreater(stats["wasteReports"], 0)
        self.assertGreater(stats["recycledKg"], 0)

        rewards_res = self.client.get("/api/dashboard/rewards")
        self.assertEqual(rewards_res.status_code, 200)
        rewards = rewards_res.get_json()
        self.assertIn("ecoPoints", rewards)
        self.assertIn("badges", rewards)

        overview_res = self.client.get("/api/dashboard/overview")
        self.assertEqual(overview_res.status_code, 200)
        ov = overview_res.get_json()
        self.assertIn("upcomingPickup", ov)
        self.assertIn("recentReports", ov)

    def test_06_ai_waste_scanner(self):
        login_res = self.client.post("/api/auth/login", json={
            "email": "ananya@example.com",
            "password": "password123"
        })
        token = login_res.get_json()["token"]

        scan_res = self.client.post(
            "/api/recycling/scan-ai",
            json={"query": "plastic bottle pet"},
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(scan_res.status_code, 200)
        data = scan_res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["scanResult"]["category"], "Recyclable")
        self.assertEqual(data["pointsAwarded"], 10)
        self.assertIsNotNone(data["userPoints"])

    def test_07_iot_bins_and_dispatch(self):
        login_res = self.client.post("/api/auth/login", json={
            "email": "ananya@example.com",
            "password": "password123"
        })
        token = login_res.get_json()["token"]

        bins_res = self.client.get("/api/dashboard/bins")
        self.assertEqual(bins_res.status_code, 200)
        bins = bins_res.get_json()["bins"]
        self.assertTrue(len(bins) > 0)
        first_bin_id = bins[0]["id"]

        dispatch_res = self.client.post(
            f"/api/dashboard/bins/{first_bin_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(dispatch_res.status_code, 200)
        data = dispatch_res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["bountyAwarded"], 25)

    def test_08_rewards_catalog_and_vouchers(self):
        user = User.query.filter_by(email="ananya@example.com").first()
        if user and user.eco_points < 300:
            user.eco_points = 1250
            db.session.commit()

        login_res = self.client.post("/api/auth/login", json={
            "email": "ananya@example.com",
            "password": "password123"
        })
        token = login_res.get_json()["token"]

        cat_res = self.client.get("/api/rewards/catalog")
        self.assertEqual(cat_res.status_code, 200)
        catalog = cat_res.get_json()["catalog"]
        self.assertTrue(len(catalog) >= 1)

        # Redeem metro pass
        redeem_res = self.client.post(
            "/api/rewards/redeem",
            json={"catalogId": "metro_pass"},
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(redeem_res.status_code, 201)
        vouch_data = redeem_res.get_json()
        self.assertTrue(vouch_data["success"])
        self.assertIn("GG-", vouch_data["voucher"]["voucherCode"])

        # Check my vouchers
        my_vouch_res = self.client.get(
            "/api/rewards/my-vouchers",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(my_vouch_res.status_code, 200)
        self.assertTrue(len(my_vouch_res.get_json()["vouchers"]) >= 1)

    def test_09_leaderboard_and_carbon_esg(self):
        lb_res = self.client.get("/api/dashboard/leaderboard")
        self.assertEqual(lb_res.status_code, 200)
        lb = lb_res.get_json()
        self.assertIn("citizens", lb)
        self.assertIn("wardLeague", lb)

        esg_res = self.client.get("/api/dashboard/carbon-esg")
        self.assertEqual(esg_res.status_code, 200)
        esg = esg_res.get_json()
        self.assertIn("carbonMetrics", esg)
        self.assertIn("certificate", esg)

    def test_10_notifications_flow(self):
        login_res = self.client.post("/api/auth/login", json={
            "email": "ananya@example.com",
            "password": "password123"
        })
        token = login_res.get_json()["token"]

        notif_res = self.client.get(
            "/api/notifications",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(notif_res.status_code, 200)
        self.assertIn("notifications", notif_res.get_json())

        read_all_res = self.client.post(
            "/api/notifications/mark-all-read",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(read_all_res.status_code, 200)

    def test_11_smart_garbage_reporting_system(self):
        # 1. Test image analysis with synthetic PNG
        import io
        from PIL import Image
        img = Image.new("RGB", (200, 200), color=(180, 50, 50))
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="PNG")
        img_bytes = img_byte_arr.getvalue()

        cv_res = self.client.post(
            "/api/reports/analyze-image",
            data={"image": (io.BytesIO(img_bytes), "camera_snapshot.png")},
            content_type="multipart/form-data"
        )
        self.assertEqual(cv_res.status_code, 200)
        cv_data = cv_res.get_json()
        self.assertTrue(cv_data.get("success"))
        self.assertIn("suggestedCategory", cv_data)
        self.assertIn("boundingBoxes", cv_data)

        # 2. Test create complaint with GPS and Live Camera snapshot
        import base64
        b64_str = "data:image/png;base64," + base64.b64encode(img_bytes).decode("utf-8")

        comp_res = self.client.post("/api/reports", json={
            "name": "Meera Patel",
            "email": "meera@example.com",
            "wasteCategory": "Overflowing Dustbin",
            "description": "Public bin near metro pillar 42 is spilling over onto sidewalk.",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "locationAccuracy": 8.5,
            "address": "Metro Pillar 42, Connaught Sector, Ward 3",
            "ward": "Ward 3",
            "severity": "High",
            "imageBase64": b64_str
        })
        self.assertEqual(comp_res.status_code, 201)
        comp_data = comp_res.get_json()
        self.assertTrue(comp_data.get("success"))
        cid = comp_data.get("complaintId")
        self.assertTrue(cid.startswith("GG-GRB-"))
        rep = comp_data.get("report")
        self.assertEqual(rep["wasteCategory"], "Overflowing Dustbin")
        self.assertEqual(rep["assignedDepartment"], "City Sanitation & Public Cleansing Division")
        self.assertEqual(rep["latitude"], 28.6139)
        self.assertEqual(rep["longitude"], 77.2090)
        self.assertEqual(rep["locationAccuracy"], 8.5)

        # 3. Test lookup by complaint ID string
        get_res = self.client.get(f"/api/reports/{cid}")
        self.assertEqual(get_res.status_code, 200)
        got_rep = get_res.get_json()["report"]
        self.assertEqual(got_rep["complaintId"], cid)
        self.assertGreater(len(got_rep["statusHistory"]), 0)

        # 4. Test Admin login & Municipal Forwarding workflow
        admin_login = self.client.post("/api/auth/login", json={
            "email": "admin@gogreen.city",
            "password": "admin123"
        })
        self.assertEqual(admin_login.status_code, 200)
        admin_token = admin_login.get_json()["token"]

        fwd_res = self.client.post(
            f"/api/reports/{cid}/forward",
            json={"notes": "Dispatched to Ward 3 Mobile Squad"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        self.assertEqual(fwd_res.status_code, 200)
        fwd_data = fwd_res.get_json()
        self.assertTrue(fwd_data.get("officialReference").startswith("MUNI-"))
        self.assertEqual(fwd_data["report"]["status"], "Forwarded to Authority")

        # 5. Test Status transition to Cleanup in Progress
        status_res = self.client.patch(
            f"/api/reports/{cid}/status",
            json={"status": "Cleanup in Progress", "notes": "Sanitation crew on site"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        self.assertEqual(status_res.status_code, 200)
        self.assertEqual(status_res.get_json()["report"]["status"], "Cleanup in Progress")

        # 6. Test Resolve with cleanup verification photo
        clean_img = Image.new("RGB", (200, 200), color=(50, 180, 50))
        clean_byte_arr = io.BytesIO()
        clean_img.save(clean_byte_arr, format="PNG")
        clean_b64 = "data:image/png;base64," + base64.b64encode(clean_byte_arr.getvalue()).decode("utf-8")

        res_res = self.client.post(
            f"/api/reports/{cid}/resolve",
            json={
                "resolutionImage": clean_b64,
                "notes": "Area cleaned, dustbin emptied, and sidewalk sanitized."
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        self.assertEqual(res_res.status_code, 200)
        resolved_rep = res_res.get_json()["report"]
        self.assertEqual(resolved_rep["status"], "Resolved")
        self.assertIsNotNone(resolved_rep["resolutionImageUrl"])
        self.assertIsNotNone(resolved_rep["resolvedAt"])

        # 7. Test Complaint Stats & Municipal Config endpoints
        stats_res = self.client.get("/api/reports/stats")
        self.assertEqual(stats_res.status_code, 200)
        self.assertIn("resolutionRate", stats_res.get_json())

        config_res = self.client.get("/api/reports/municipal-config")
        self.assertEqual(config_res.status_code, 200)
        self.assertIn("supportedCategories", config_res.get_json())


if __name__ == "__main__":
    unittest.main()

