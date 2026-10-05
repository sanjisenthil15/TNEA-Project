"""
Full Regression Test Suite across all existing and new features
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models.database import init_auth_db, get_connection, create_user, get_user_by_email

class FullRegressionTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_auth_db()
        from models.database import set_user_premium_status
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE email = 'regression_user@test.com'")
        conn.commit()
        conn.close()

        cls.user_id = create_user("Regression User", "regression_user@test.com", "hash_reg")
        set_user_premium_status(cls.user_id, True)
        cls.client = app.test_client()

    def test_routes_status_codes(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id
            sess["user_name"] = "Regression User"
            sess["is_premium"] = 1

        routes_to_test = [
            ("/", 200),
            ("/planner", 200),
            ("/compare", 200),
            ("/analytics", 200),
            ("/trend", 200),
            ("/search", 200),
            ("/career-guidance", 200),
            ("/counselling", 200),
            ("/resources", 200),
            ("/choice-list", 200),
            ("/college/1", 200) # CEG Guindy
        ]
        for path, expected_code in routes_to_test:
            with self.subTest(path=path):
                resp = self.client.get(path)
                self.assertEqual(resp.status_code, expected_code, f"Failed for {path}")

        # Unauthenticated endpoints
        unauth_client = app.test_client()
        for path in ["/login", "/register"]:
            with self.subTest(path=path):
                resp = unauth_client.get(path)
                self.assertEqual(resp.status_code, 200, f"Failed for {path}")

    def test_recommend_post(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id
            sess["user_name"] = "Regression User"
            sess["is_premium"] = 1
        resp = self.client.post("/recommend", data={
            "cutoff": "185.0",
            "community": "BC",
            "branch": "CS",
            "district": "Chennai",
            "year": "2025"
        })
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode("utf-8")
        self.assertIn("Recommendation Results", content)
        self.assertIn("cmp-check-wrap", content)
        self.assertIn("rec-college-name", content)
        self.assertIn("cmp-checkbox", content)

    def test_compare_colleges(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id
            sess["user_name"] = "Regression User"
            sess["is_premium"] = 1
        resp = self.client.get("/compare?college1=1&college2=2006")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"College Comparison", resp.data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
