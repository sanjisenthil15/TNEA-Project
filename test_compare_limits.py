"""
Unit and Integration Tests for Free vs Premium College Comparison Limits
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, _build_comparison_summary
from models.database import init_auth_db, get_connection, create_user, set_user_premium_status, get_college_details, get_college_branches

class TestCollegeComparisonLimits(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_auth_db()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE email IN ('free_cmp@test.com', 'prem_cmp@test.com')")
        conn.commit()
        conn.close()

        cls.free_user_id = create_user("Free User", "free_cmp@test.com", "hash_free")
        set_user_premium_status(cls.free_user_id, False)

        cls.prem_user_id = create_user("Premium User", "prem_cmp@test.com", "hash_prem")
        set_user_premium_status(cls.prem_user_id, True)

        cls.client = app.test_client()

    def test_01_free_user_compare_2_colleges_allowed(self):
        """Free user can compare 2 colleges successfully."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.free_user_id
            sess["user_name"] = "Free User"
            sess["is_premium"] = 0

        resp = self.client.get("/compare?college1=1&college2=2006")
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode("utf-8")
        self.assertIn("College Comparison", content)
        self.assertIn("Side-by-Side Comparison", content)
        self.assertIn("College A", content)
        self.assertIn("College B", content)
        self.assertNotIn("Cannot Load Comparison", content)
        self.assertNotIn("Free accounts can compare up to 2 colleges", content)

    def test_02_free_user_compare_3_colleges_blocked(self):
        """Free user attempting to compare 3 colleges is blocked with an upgrade prompt."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.free_user_id
            sess["user_name"] = "Free User"
            sess["is_premium"] = 0

        resp = self.client.get("/compare?college1=1&college2=2006&college3=1219")
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode("utf-8")
        self.assertIn("Free accounts can compare up to 2 colleges at a time", content)
        self.assertIn("Upgrade to Premium", content)
        self.assertIn("/premium", content)

    def test_03_free_user_comma_separated_3_colleges_blocked(self):
        """Free user attempting to pass colleges=1,2006,1219 is blocked on server."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.free_user_id
            sess["user_name"] = "Free User"
            sess["is_premium"] = 0

        resp = self.client.get("/compare?colleges=1,2006,1219")
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode("utf-8")
        self.assertIn("Free accounts can compare up to 2 colleges at a time", content)

    def test_04_premium_user_compare_2_colleges_allowed(self):
        """Premium user can compare 2 colleges."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.prem_user_id
            sess["user_name"] = "Premium User"
            sess["is_premium"] = 1

        resp = self.client.get("/compare?college1=1&college2=2006")
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode("utf-8")
        self.assertIn("College Comparison", content)
        self.assertIn("College A", content)
        self.assertIn("College B", content)

    def test_05_premium_user_compare_3_colleges_allowed(self):
        """Premium user can compare 3 colleges."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.prem_user_id
            sess["user_name"] = "Premium User"
            sess["is_premium"] = 1

        resp = self.client.get("/compare?college1=1&college2=2006&college3=1219")
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode("utf-8")
        self.assertIn("College Comparison", content)
        self.assertIn("College A", content)
        self.assertIn("College B", content)
        self.assertIn("College C", content)
        self.assertNotIn("Free accounts can compare up to 2 colleges", content)

    def test_06_premium_user_compare_5_colleges_allowed(self):
        """Premium user can compare up to 5 colleges."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.prem_user_id
            sess["user_name"] = "Premium User"
            sess["is_premium"] = 1

        resp = self.client.get("/compare?college1=1&college2=2006&college3=1219&college4=1315&college5=1399")
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode("utf-8")
        self.assertIn("College Comparison", content)
        self.assertIn("College A", content)
        self.assertIn("College B", content)
        self.assertIn("College C", content)
        self.assertIn("College D", content)
        self.assertIn("College E", content)

    def test_07_premium_user_compare_6_colleges_blocked(self):
        """Premium user attempting 6 colleges is blocked with a maximum limit message."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.prem_user_id
            sess["user_name"] = "Premium User"
            sess["is_premium"] = 1

        resp = self.client.get("/compare?college1=1&college2=2006&college3=1219&college4=1315&college5=1399&colleges=1419")
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode("utf-8")
        self.assertIn("maximum of 5 colleges", content)

    def test_08_free_user_tampering_session_flag_blocked_by_server_db(self):
        """Free user attempting to tamper session flag to is_premium=1 is blocked because DB ground truth is Free."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.free_user_id
            sess["user_name"] = "Free User"
            sess["is_premium"] = 1  # Spoofed in session, but DB has is_premium = 0

        resp = self.client.get("/compare?college1=1&college2=2006&college3=1219")
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode("utf-8")
        self.assertIn("Free accounts can compare up to 2 colleges at a time", content)

    def test_09_minimum_colleges_required(self):
        """Fewer than 2 colleges prompts the user to select at least 2."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.free_user_id
            sess["user_name"] = "Free User"
            sess["is_premium"] = 0

        resp1 = self.client.get("/compare")
        self.assertEqual(resp1.status_code, 200)
        self.assertIn("Select 2 or more colleges", resp1.data.decode("utf-8"))

        resp2 = self.client.get("/compare?college1=1")
        self.assertEqual(resp2.status_code, 200)
        self.assertIn("select at least 2 colleges", resp2.data.decode("utf-8"))

    def test_10_search_and_result_page_limits_rendered(self):
        """Verify Free vs Premium limit text in Search and Result pages."""
        # Free user on search page
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.free_user_id
            sess["user_name"] = "Free User"
            sess["is_premium"] = 0

        resp_search_free = self.client.get("/search")
        self.assertEqual(resp_search_free.status_code, 200)
        search_free_html = resp_search_free.data.decode("utf-8")
        self.assertIn("Selected <span class=\"cmp-count\" id=\"compareCount\">0</span> of 2 colleges", search_free_html)
        self.assertIn("var MAX = IS_PREMIUM ? 5 : 2;", search_free_html)

        # Premium user on search page
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.prem_user_id
            sess["user_name"] = "Premium User"
            sess["is_premium"] = 1

        resp_search_prem = self.client.get("/search")
        self.assertEqual(resp_search_prem.status_code, 200)
        search_prem_html = resp_search_prem.data.decode("utf-8")
        self.assertIn("Selected <span class=\"cmp-count\" id=\"compareCount\">0</span> of 5 colleges", search_prem_html)

    def test_11_comparison_summary_multi_college_logic(self):
        """Test _build_comparison_summary with 3 colleges."""
        c1 = {"college_code": 1, "college_name": "CEG", "autonomous": "Yes", "transport": "Yes", "hostel_boys": "Yes", "hostel_girls": "Yes", "district": "Chennai"}
        c2 = {"college_code": 2006, "college_name": "PSG", "autonomous": "Yes", "transport": "No", "hostel_boys": "Yes", "hostel_girls": "Yes", "district": "Coimbatore"}
        c3 = {"college_code": 1219, "college_name": "SVCE", "autonomous": "No", "transport": "Yes", "hostel_boys": "No", "hostel_girls": "Yes", "district": "Sriperumbudur"}

        b1 = [{"branch_code": "CS"}, {"branch_code": "EC"}]
        b2 = [{"branch_code": "CS"}, {"branch_code": "EC"}, {"branch_code": "ME"}]
        b3 = [{"branch_code": "CS"}]

        summary = _build_comparison_summary([c1, c2, c3], [b1, b2, b3])
        self.assertTrue(any("Autonomous status" in s for s in summary))
        self.assertTrue(any("Transport facilities" in s for s in summary))
        self.assertTrue(any("Boys hostel" in s for s in summary))
        self.assertTrue(any("PSG (3)" in s for s in summary))


if __name__ == "__main__":
    unittest.main(verbosity=2)
