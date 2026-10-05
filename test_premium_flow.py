"""
=============================================================
Phase 6 Final Navigation + Premium UX Test Suite (20 Tests)
=============================================================
TEST 1:  Open login page while logged out -> No authenticated student navigation.
TEST 2:  Login as a FREE student -> Single Premium entry in navbar, no individual Premium links.
TEST 3:  Verify FREE user navbar structure has no overlapping elements.
TEST 4:  Click Premium -> Existing Premium Access page.
TEST 5:  Premium page shows all FIVE Premium benefits.
TEST 6:  Career Guidance is listed as Premium benefit.
TEST 7:  Choice List / Advanced Choice Analysis is listed as Premium benefit.
TEST 8:  Complete successful test payment -> Premium activated on same account.
TEST 9:  Refresh -> Premium remains active.
TEST 10: Logout and login again -> Premium remains active.
TEST 11: Login as Premium user -> Individual Premium navigation items appear.
TEST 12: Premium user sees PRO/Premium status.
TEST 13: Premium user does NOT see "Unlock PRO ₹200".
TEST 14: FREE user attempts direct access to Career Guidance -> Premium Access page.
TEST 15: FREE user attempts direct access to AI Assistant -> Premium Access page.
TEST 16: FREE user attempts direct access to Counselling -> Premium Access page.
TEST 17: FREE user attempts direct access to Resources -> Premium Access page.
TEST 18: FREE user attempts direct access to Advanced Choice Analysis -> Premium Access page.
TEST 19: Verify existing free features still work.
TEST 20: Verify Choice List college_code + branch_code behavior is unchanged.
=============================================================
"""

import os
import sys
import unittest
import json
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.database import (
    get_connection,
    init_auth_db,
    create_user,
    get_user_by_email,
    get_user_by_id,
    create_payment_order,
    verify_and_activate_premium,
    set_user_premium_status,
    get_user_choice_list,
    add_to_choice_list,
    clear_user_choice_list
)

from app import app


class TestPhase6FinalNavigation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_auth_db()
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()

        # Clean test user database records
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE email LIKE '%@phase6test.com'")
        cursor.execute("DELETE FROM orders")
        conn.commit()
        conn.close()

        # Create base test users
        cls.free_user_id = create_user("Free Student", "free_student@phase6test.com", generate_password_hash("password123"))
        cls.prem_user_id = create_user("Prem Student", "prem_student@phase6test.com", generate_password_hash("password123"))
        set_user_premium_status(cls.prem_user_id, True)

    def test_01_unauthenticated_login_page_minimal_header(self):
        """TEST 1: Open /login while logged out -> No authenticated student navigation."""
        unauth_client = app.test_client()
        res = unauth_client.get("/login")
        self.assertEqual(res.status_code, 200)
        content = res.data.decode("utf-8")
        
        # Extract the navbar HTML
        nav_html = content.split("<nav")[1].split("</nav>")[0]

        # Verify minimal public header presence
        self.assertIn("Sign In", nav_html)
        self.assertIn("Create Account", nav_html)
        
        # Verify authenticated navigation links are NOT present
        self.assertNotIn('href="/logout"', nav_html)
        self.assertNotIn('href="/career-guidance"', nav_html)
        self.assertNotIn('href="/counselling"', nav_html)
        self.assertNotIn('href="/career-assistant"', nav_html)
        self.assertNotIn('href="/choice-list"', nav_html)
        self.assertNotIn('href="/planner"', nav_html)
        self.assertNotIn('href="/compare"', nav_html)
        self.assertNotIn('href="/analytics"', nav_html)
        self.assertNotIn('href="/trend"', nav_html)
        self.assertNotIn('href="/search"', nav_html)

    def test_02_free_user_navbar_structure(self):
        """TEST 2: Login as FREE student -> One single Premium entry in navbar, no individual Premium links."""
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = self.free_user_id
            sess["user_name"] = "Free Student"
            sess["user_email"] = "free_student@phase6test.com"
            sess["is_premium"] = 0

        res = client.get("/")
        self.assertEqual(res.status_code, 200)
        content = res.data.decode("utf-8")
        nav_html = content.split("<nav")[1].split("</nav>")[0]

        # Standard free navigation items present
        self.assertIn('href="/"', nav_html)
        self.assertIn('href="/planner"', nav_html)
        self.assertIn('href="/compare"', nav_html)
        self.assertIn('href="/analytics"', nav_html)
        self.assertIn('href="/trend"', nav_html)
        self.assertIn('href="/search"', nav_html)
        self.assertIn('href="/premium"', nav_html)
        self.assertIn("Premium ✦", nav_html)
        self.assertIn("FREE", nav_html)
        self.assertIn('href="/logout"', nav_html)

        # Individual Premium feature links MUST NOT appear in FREE navbar
        self.assertNotIn('href="/career-guidance"', nav_html)
        self.assertNotIn('href="/counselling"', nav_html)
        self.assertNotIn('href="/resources"', nav_html)
        self.assertNotIn('href="/career-assistant"', nav_html)
        self.assertNotIn('href="/choice-list"', nav_html)

    def test_03_free_user_navbar_no_separate_pro_badges(self):
        """TEST 3: Verify FREE user navbar does NOT contain five separate PRO badges causing overlap."""
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = self.free_user_id
            sess["user_name"] = "Free Student"
            sess["is_premium"] = 0

        res = client.get("/")
        content = res.data.decode("utf-8")
        nav_html = content.split("<nav")[1].split("</nav>")[0]

        # Ensure no multiple lock badges in nav links
        self.assertEqual(nav_html.count("bi-lock-fill"), 0)

    def test_04_free_user_clicks_premium_entry(self):
        """TEST 4: Click Premium -> Existing Premium Access page."""
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = self.free_user_id
            sess["is_premium"] = 0

        res = client.get("/premium")
        self.assertEqual(res.status_code, 200)
        content = res.data.decode("utf-8")
        self.assertIn("Unlock Full Premium Access for", content)
        self.assertIn("200", content)

    def test_05_premium_page_shows_five_benefits(self):
        """TEST 5: Premium page shows all FIVE Premium benefits together."""
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = self.free_user_id
            sess["is_premium"] = 0

        res = client.get("/premium")
        self.assertEqual(res.status_code, 200)
        content = res.data.decode("utf-8")

        self.assertIn("Career Guidance", content)
        self.assertIn("AI Career Assistant", content)
        self.assertIn("TNEA Counselling Assistant", content)
        self.assertIn("Personalized Learning Resources", content)
        self.assertIn("Advanced Choice Analysis", content)

    def test_06_career_guidance_listed_as_premium(self):
        """TEST 6: Career Guidance is listed as Premium benefit."""
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = self.free_user_id
            sess["is_premium"] = 0
        res = client.get("/premium")
        self.assertEqual(res.status_code, 200)
        content = res.data.decode("utf-8")
        self.assertIn("Career Guidance & Aptitude Assessment", content)
        self.assertIn("Benefit 1", content)

    def test_07_choice_list_advanced_listed_as_premium(self):
        """TEST 7: Choice List / Advanced Choice Analysis is listed as Premium."""
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = self.free_user_id
            sess["is_premium"] = 0
        res = client.get("/premium")
        self.assertEqual(res.status_code, 200)
        content = res.data.decode("utf-8")
        self.assertIn("Advanced Choice Analysis", content)
        self.assertIn("Benefit 5", content)

    def test_08_complete_successful_test_payment(self):
        """TEST 8: Complete successful test payment -> Premium activated on same account."""
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = self.free_user_id
            sess["is_premium"] = 0

        # Step 1: Create Order
        res_order = client.post("/api/payment/create-order", json={"amount": 200.0, "currency": "INR"})
        self.assertEqual(res_order.status_code, 200)
        order_id = res_order.get_json()["order_id"]

        # Step 2: Verify and Activate
        res_verify = client.post("/api/payment/verify", json={
            "order_id": order_id,
            "payment_id": "pay_test_phase6_final",
            "signature": "sig_test_phase6_final"
        })
        self.assertEqual(res_verify.status_code, 200)
        self.assertTrue(res_verify.get_json()["is_premium"])

        # Database verification
        user = get_user_by_id(self.free_user_id)
        self.assertEqual(user["is_premium"], 1)

    def test_09_refresh_premium_remains_active(self):
        """TEST 9: Refresh -> Premium remains active."""
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = self.free_user_id
            sess["is_premium"] = 1

        res = client.get("/")
        self.assertEqual(res.status_code, 200)
        content = res.data.decode("utf-8")
        self.assertIn("PRO", content)

    def test_10_logout_and_login_again_premium_persists(self):
        """TEST 10: Logout and login again -> Premium remains active."""
        client = app.test_client()
        # 1. Logout
        client.get("/logout")

        # 2. Login again
        res_login = client.post("/login", data={
            "email": "free_student@phase6test.com",
            "password": "password123"
        }, follow_redirects=False)
        self.assertEqual(res_login.status_code, 302)

        # 3. User is verified premium from DB
        user = get_user_by_email("free_student@phase6test.com")
        self.assertEqual(user["is_premium"], 1)

    def test_11_premium_user_navigation_items_revealed(self):
        """TEST 11: Login as Premium user -> Individual Premium navigation items appear."""
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = self.prem_user_id
            sess["user_name"] = "Prem Student"
            sess["user_email"] = "prem_student@phase6test.com"
            sess["is_premium"] = 1

        res = client.get("/")
        self.assertEqual(res.status_code, 200)
        content = res.data.decode("utf-8")
        nav_html = content.split("<nav")[1].split("</nav>")[0]

        # All 5 individual Premium items appear
        self.assertIn('href="/career-guidance"', nav_html)
        self.assertIn('href="/counselling"', nav_html)
        self.assertIn('href="/resources"', nav_html)
        self.assertIn('href="/career-assistant"', nav_html)
        self.assertIn('href="/choice-list"', nav_html)

    def test_12_premium_user_status_badge(self):
        """TEST 12: Premium user sees PRO/Premium status."""
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = self.prem_user_id
            sess["user_name"] = "Prem Student"
            sess["is_premium"] = 1

        res = client.get("/")
        content = res.data.decode("utf-8")
        nav_html = content.split("<nav")[1].split("</nav>")[0]
        self.assertIn("PRO", nav_html)

    def test_13_premium_user_does_not_see_unlock_pro_button(self):
        """TEST 13: Premium user does NOT see Unlock PRO ₹200 button or single Premium item."""
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = self.prem_user_id
            sess["user_name"] = "Prem Student"
            sess["is_premium"] = 1

        res = client.get("/")
        content = res.data.decode("utf-8")
        nav_html = content.split("<nav")[1].split("</nav>")[0]
        self.assertNotIn("Unlock PRO", nav_html)
        self.assertNotIn("Unlock Full Premium Access", nav_html)
        self.assertNotIn("Premium ✦", nav_html)

    def test_14_free_user_direct_career_guidance_redirects_to_premium(self):
        """TEST 14: FREE user attempts direct access to Career Guidance -> Premium Access page."""
        # Create a fresh free user
        uid = create_user("Temp Free1", "temp_free1@phase6test.com", generate_password_hash("pass123"))
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = uid
            sess["is_premium"] = 0

        res = client.get("/career-guidance")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/premium", res.headers["Location"])

    def test_15_free_user_direct_ai_assistant_redirects_to_premium(self):
        """TEST 15: FREE user attempts direct access to AI Assistant -> Premium Access page."""
        uid = create_user("Temp Free2", "temp_free2@phase6test.com", generate_password_hash("pass123"))
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = uid
            sess["is_premium"] = 0

        res = client.get("/career-assistant")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/premium", res.headers["Location"])

    def test_16_free_user_direct_counselling_redirects_to_premium(self):
        """TEST 16: FREE user attempts direct access to Counselling -> Premium Access page."""
        uid = create_user("Temp Free3", "temp_free3@phase6test.com", generate_password_hash("pass123"))
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = uid
            sess["is_premium"] = 0

        res = client.get("/counselling")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/premium", res.headers["Location"])

    def test_17_free_user_direct_resources_redirects_to_premium(self):
        """TEST 17: FREE user attempts direct access to Resources -> Premium Access page."""
        uid = create_user("Temp Free4", "temp_free4@phase6test.com", generate_password_hash("pass123"))
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = uid
            sess["is_premium"] = 0

        res = client.get("/resources")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/premium", res.headers["Location"])

    def test_18_free_user_direct_choice_analysis_redirects_to_premium(self):
        """TEST 18: FREE user attempts direct access to Advanced Choice Analysis -> Premium Access page."""
        uid = create_user("Temp Free5", "temp_free5@phase6test.com", generate_password_hash("pass123"))
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = uid
            sess["is_premium"] = 0

        res1 = client.get("/choice-list")
        self.assertEqual(res1.status_code, 302)
        self.assertIn("/premium", res1.headers["Location"])

        res2 = client.get("/choice-list/advanced")
        self.assertEqual(res2.status_code, 302)
        self.assertIn("/premium", res2.headers["Location"])

    def test_19_existing_free_features_remain_functional(self):
        """TEST 19: Verify existing free features still work."""
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = self.prem_user_id
            sess["is_premium"] = 1

        free_paths = ["/", "/planner", "/search", "/compare", "/analytics", "/trend", "/college/1"]
        for p in free_paths:
            res = client.get(p)
            self.assertEqual(res.status_code, 200, f"Failed accessing free route {p}")

    def test_20_choice_list_college_and_branch_uniqueness(self):
        """TEST 20: Verify Choice List college_code + branch_code behavior is unchanged."""
        import uuid
        uid = create_user(f"Uniq User {uuid.uuid4().hex[:4]}", f"uniq_{uuid.uuid4().hex[:6]}@phase6test.com", "hash")
        clear_user_choice_list(uid)

        # Add College 1 + CS
        r1 = add_to_choice_list(uid, 1, "CS")
        self.assertTrue(r1["success"])
        self.assertFalse(r1["already_exists"])

        # Add College 1 + IT
        r2 = add_to_choice_list(uid, 1, "IT")
        self.assertTrue(r2["success"])
        self.assertFalse(r2["already_exists"])

        # Add College 1 + AD
        r3 = add_to_choice_list(uid, 1, "AD")
        self.assertTrue(r3["success"])
        self.assertFalse(r3["already_exists"])

        # Try adding College 1 + CS duplicate
        r_dup = add_to_choice_list(uid, 1, "CS")
        self.assertTrue(r_dup["already_exists"])

        choices = get_user_choice_list(uid)
        self.assertEqual(len(choices), 3)

    def test_21_choice_list_multi_user_isolation(self):
        """TEST 21: Premium Student A choices are never visible to Premium Student B."""
        import uuid
        uid_a = create_user(f"Student A {uuid.uuid4().hex[:4]}", f"student_a_{uuid.uuid4().hex[:6]}@phase6test.com", "hash")
        uid_b = create_user(f"Student B {uuid.uuid4().hex[:4]}", f"student_b_{uuid.uuid4().hex[:6]}@phase6test.com", "hash")
        set_user_premium_status(uid_a, True)
        set_user_premium_status(uid_b, True)

        clear_user_choice_list(uid_a)
        clear_user_choice_list(uid_b)

        # Student A adds 3 choices
        add_to_choice_list(uid_a, 1, "CS")
        add_to_choice_list(uid_a, 1, "IT")
        add_to_choice_list(uid_a, 2006, "AD")

        choices_a = get_user_choice_list(uid_a)
        self.assertEqual(len(choices_a), 3)

        # Student B initially has 0 choices (Empty state)
        choices_b_init = get_user_choice_list(uid_b)
        self.assertEqual(len(choices_b_init), 0)

        # Student B adds 1 choice
        add_to_choice_list(uid_b, 1399, "EC")
        choices_b = get_user_choice_list(uid_b)
        self.assertEqual(len(choices_b), 1)
        self.assertEqual(choices_b[0]["college_code"], 1399)
        self.assertEqual(choices_b[0]["branch_code"], "EC")

        # Student A still has only their 3 choices
        choices_a_after = get_user_choice_list(uid_a)
        self.assertEqual(len(choices_a_after), 3)

    def test_22_free_user_choice_list_api_endpoints_denied(self):
        """TEST 22: FREE user attempting direct API calls to choice list endpoints is denied (403)."""
        uid = create_user("Free API Student", "free_api@phase6test.com", generate_password_hash("pass123"))
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = uid
            sess["is_premium"] = 0

        # GET /api/choice-list
        r_get = client.get("/api/choice-list")
        self.assertEqual(r_get.status_code, 403)

        # POST /api/choice-list/add
        r_add = client.post("/api/choice-list/add", json={"college_code": 1, "branch_code": "CS"})
        self.assertEqual(r_add.status_code, 403)

        # POST /api/choice-list/remove
        r_rem = client.post("/api/choice-list/remove", json={"college_code": 1, "branch_code": "CS"})
        self.assertEqual(r_rem.status_code, 403)

        # POST /api/choice-list/reorder
        r_ord = client.post("/api/choice-list/reorder", json={"items": []})
        self.assertEqual(r_ord.status_code, 403)

        # POST /api/choice-list/clear
        r_clr = client.post("/api/choice-list/clear")
        self.assertEqual(r_clr.status_code, 403)

    def test_23_empty_state_rendered_when_premium_user_has_no_choices(self):
        """TEST 23: Premium user with no choices sees clean empty state."""
        import uuid
        uid = create_user(f"Empty User {uuid.uuid4().hex[:4]}", f"empty_{uuid.uuid4().hex[:6]}@phase6test.com", "hash")
        set_user_premium_status(uid, True)
        clear_user_choice_list(uid)

        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = uid
            sess["is_premium"] = 1

        res = client.get("/choice-list")
        self.assertEqual(res.status_code, 200)
        content = res.data.decode("utf-8")
        self.assertIn("My Choice List is empty", content)
        self.assertIn("Add colleges and branches from the Planner or College Search to start building your preference list.", content)
        self.assertIn("Explore Colleges", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
