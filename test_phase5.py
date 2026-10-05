"""
=============================================================
Phase 5 Comprehensive Verification Test Suite
=============================================================
Tests:
1. Unique (college_code, branch_code) choice list logic in DB
2. Different branches for same college (CSE, IT, AI&DS)
3. Duplicate addition prevention
4. Removal and preference re-indexing
5. Reordering preferences
6. Multi-user security isolation
7. Counselling checklist state tracking and persistence
8. Learning resources catalog retrieval, filtering, and search
9. Profile-based personalized learning resource ranking across 4 student profiles:
   - CSE/AI&DS strong fit
   - ECE/EEE strong fit
   - Mechanical strong fit
   - Mixed profile
10. AI Assistant counselling grounding and 2027 future cutoff unavailability
11. Flask route endpoints (/counselling, /resources, /choice-list, and APIs)
=============================================================
"""

import os
import sys
import unittest
import json

# Ensure parent directory is on pythonpath
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.database import (
    get_connection,
    init_auth_db,
    create_user,
    get_user_by_email,
    get_user_choice_list,
    add_to_choice_list,
    remove_from_choice_list,
    reorder_choice_list,
    clear_user_choice_list,
    get_user_checklist,
    toggle_checklist_item,
    DEFAULT_CHECKLIST_ITEMS
)

from models.resources import (
    get_all_resources,
    get_personalized_resources,
    RESOURCE_CATEGORIES,
    LEARNING_RESOURCES
)

from models.ai_assistant import (
    get_career_assistant_response,
    retrieve_grounded_tnea_data
)

from app import app


class TestPhase5CounsellingAndResources(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_auth_db()
        # Create test users
        conn = get_connection()
        cursor = conn.cursor()
        
        # Clean up test user records if exist
        cursor.execute("DELETE FROM users WHERE email IN ('student_a@tneatest.com', 'student_b@tneatest.com')")
        cursor.execute("DELETE FROM user_choice_list")
        cursor.execute("DELETE FROM user_counselling_checklist")
        conn.commit()
        conn.close()

        cls.user_a_id = create_user("Student A", "student_a@tneatest.com", "hash_a")
        cls.user_b_id = create_user("Student B", "student_b@tneatest.com", "hash_b")

    def test_01_choice_list_same_college_multiple_branches(self):
        """Test: Add CSE, IT, and AD for College 1 — all three must be added as distinct choices."""
        # Add College 1 + CS
        r1 = add_to_choice_list(self.user_a_id, 1, "CS")
        self.assertTrue(r1["success"])
        self.assertFalse(r1["already_exists"])
        self.assertEqual(r1["preference_order"], 1)

        # Add College 1 + IT
        r2 = add_to_choice_list(self.user_a_id, 1, "IT")
        self.assertTrue(r2["success"])
        self.assertFalse(r2["already_exists"])
        self.assertEqual(r2["preference_order"], 2)

        # Add College 1 + AD
        r3 = add_to_choice_list(self.user_a_id, 1, "AD")
        self.assertTrue(r3["success"])
        self.assertFalse(r3["already_exists"])
        self.assertEqual(r3["preference_order"], 3)

        choices = get_user_choice_list(self.user_a_id)
        self.assertEqual(len(choices), 3)
        branch_codes = [c["branch_code"] for c in choices]
        self.assertIn("CS", branch_codes)
        self.assertIn("IT", branch_codes)
        self.assertIn("AD", branch_codes)

    def test_02_choice_list_duplicate_prevention(self):
        """Test: Adding College 1 + CS again must NOT create duplicates."""
        initial_choices = get_user_choice_list(self.user_a_id)
        count_before = len(initial_choices)

        dup_res = add_to_choice_list(self.user_a_id, 1, "CS")
        self.assertTrue(dup_res["success"])
        self.assertTrue(dup_res["already_exists"])

        after_choices = get_user_choice_list(self.user_a_id)
        self.assertEqual(len(after_choices), count_before)

    def test_03_choice_list_removal_and_reindex(self):
        """Test: Remove IT -> CSE and AD must remain with reindexed preference orders."""
        rem_res = remove_from_choice_list(self.user_a_id, 1, "IT")
        self.assertTrue(rem_res)

        choices = get_user_choice_list(self.user_a_id)
        self.assertEqual(len(choices), 2)
        
        branch_codes = [c["branch_code"] for c in choices]
        self.assertIn("CS", branch_codes)
        self.assertIn("AD", branch_codes)
        self.assertNotIn("IT", branch_codes)

        # Verify sequential preference orders (1, 2)
        orders = [c["preference_order"] for c in choices]
        self.assertEqual(orders, [1, 2])

    def test_04_choice_list_reordering(self):
        """Test: Reorder choices (place AD as #1 and CS as #2)."""
        reorder_items = [
            {"college_code": 1, "branch_code": "AD"},
            {"college_code": 1, "branch_code": "CS"}
        ]
        ok = reorder_choice_list(self.user_a_id, reorder_items)
        self.assertTrue(ok)

        choices = get_user_choice_list(self.user_a_id)
        self.assertEqual(choices[0]["branch_code"], "AD")
        self.assertEqual(choices[0]["preference_order"], 1)
        self.assertEqual(choices[1]["branch_code"], "CS")
        self.assertEqual(choices[1]["preference_order"], 2)

    def test_05_multi_user_isolation(self):
        """Test: Student B has empty choice list, adding choice to B does not touch A."""
        b_choices_initial = get_user_choice_list(self.user_b_id)
        self.assertEqual(len(b_choices_initial), 0)

        # Add choice to Student B
        add_to_choice_list(self.user_b_id, 2006, "EC")
        b_choices = get_user_choice_list(self.user_b_id)
        self.assertEqual(len(b_choices), 1)
        self.assertEqual(b_choices[0]["branch_code"], "EC")

        # Verify Student A choices are still intact and isolated
        a_choices = get_user_choice_list(self.user_a_id)
        self.assertEqual(len(a_choices), 2)
        self.assertNotIn("EC", [c["branch_code"] for c in a_choices])

    def test_06_counselling_checklist_state_and_isolation(self):
        """Test: Actionable checklist toggle and user isolation."""
        # Student A toggles two items
        toggle_checklist_item(self.user_a_id, "review_career_fit", True)
        toggle_checklist_item(self.user_a_id, "check_cutoff_trends", True)

        a_status = get_user_checklist(self.user_a_id)
        self.assertTrue(a_status.get("review_career_fit"))
        self.assertTrue(a_status.get("check_cutoff_trends"))
        self.assertFalse(a_status.get("shortlist_colleges", False))

        # Student B checklist must be completely empty / independent
        b_status = get_user_checklist(self.user_b_id)
        self.assertFalse(b_status.get("review_career_fit", False))
        self.assertFalse(b_status.get("check_cutoff_trends", False))

    def test_07_verified_learning_resources_catalog(self):
        """Test: Resources catalog integrity, YouTube URLs, and category filtering."""
        all_res = get_all_resources()
        self.assertGreaterEqual(len(all_res), 15)

        for r in all_res:
            self.assertTrue(r["id"].startswith("res_"))
            self.assertTrue(r["title"])
            self.assertTrue(r["url"].startswith("https://www.youtube.com/watch?v="))
            self.assertTrue(r["youtube_id"])
            self.assertTrue(r["channel"])
            self.assertTrue(r["category"])

        # Category filter test
        prog_res = get_all_resources(category="programming")
        self.assertTrue(all(r["category"] == "programming" for r in prog_res))
        self.assertGreaterEqual(len(prog_res), 2)

        # Search test
        math_search = get_all_resources(search_query="calculus")
        self.assertTrue(any("calculus" in r["title"].lower() or "calculus" in r["description"].lower() for r in math_search))

    def test_08_personalized_resources_different_profiles(self):
        """Test: Personalized resource recommendations differ across profiles."""
        # 1. CSE/AI&DS Profile
        profile_cse = {
            "top_branches": [{"branch_code": "CS", "branch_name": "Computer Science"}, {"branch_code": "AD", "branch_name": "AI & DS"}],
            "interest_scores": {"computing": 95, "analytical": 90, "electronics": 30, "mechanical": 20}
        }
        res_cse = get_personalized_resources(profile_cse, limit=4)
        cse_categories = [r["category"] for r in res_cse]
        self.assertTrue("programming" in cse_categories or "ai_data" in cse_categories)

        # 2. ECE/EEE Profile
        profile_ece = {
            "top_branches": [{"branch_code": "EC", "branch_name": "Electronics & Communication"}, {"branch_code": "EE", "branch_name": "Electrical & Electronics"}],
            "interest_scores": {"electronics": 95, "practical": 90, "computing": 40, "mechanical": 30}
        }
        res_ece = get_personalized_resources(profile_ece, limit=4)
        ece_categories = [r["category"] for r in res_ece]
        self.assertIn("electronics", ece_categories)

        # 3. Mechanical Profile
        profile_mech = {
            "top_branches": [{"branch_code": "ME", "branch_name": "Mechanical Engineering"}, {"branch_code": "AU", "branch_name": "Automobile"}],
            "interest_scores": {"mechanical": 95, "practical": 90, "design": 85, "computing": 20}
        }
        res_mech = get_personalized_resources(profile_mech, limit=4)
        mech_categories = [r["category"] for r in res_mech]
        self.assertIn("mechanical", mech_categories)

        # 4. Mixed Profile
        profile_mixed = {
            "top_branches": [{"branch_code": "CE", "branch_name": "Civil Engineering"}, {"branch_code": "CS", "branch_name": "Computer Science"}],
            "interest_scores": {"civil": 80, "computing": 80}
        }
        res_mixed = get_personalized_resources(profile_mixed, limit=4)

        # Ensure recommendation sets differ between CSE and Mechanical
        cse_titles = {r["title"] for r in res_cse}
        mech_titles = {r["title"] for r in res_mech}
        self.assertNotEqual(cse_titles, mech_titles)

    def test_09_grounded_tnea_data_future_year_unavailable(self):
        """Test: Future cutoff year (2027) request is explicitly noted as unavailable."""
        data = retrieve_grounded_tnea_data("What is the 2027 cutoff for SSN CSE?")
        self.assertTrue(data.get("has_grounding"))
        self.assertTrue(data.get("unavailable_year_requested"))
        self.assertIn("2023, 2024, and 2025", data.get("unavailable_year_message"))

    def test_10_flask_routes_and_apis(self):
        """Test: HTTP route responses for /counselling, /resources, /choice-list, and APIs."""
        client = app.test_client()
        from models.database import set_user_premium_status
        set_user_premium_status(self.user_a_id, True)

        # Authenticate session as User A (Premium)
        with client.session_transaction() as sess:
            sess["user_id"] = self.user_a_id
            sess["user_name"] = "Student A"
            sess["is_premium"] = 1

        # 1. GET /counselling
        resp_c = client.get("/counselling")
        self.assertEqual(resp_c.status_code, 200)
        self.assertIn(b"TNEA Choice-Filling Guidance", resp_c.data)
        self.assertIn(b"3-Tier Preference Strategy", resp_c.data)

        # 2. GET /resources
        resp_r = client.get("/resources")
        self.assertEqual(resp_r.status_code, 200)
        self.assertIn(b"Pre-Engineering Learning Resources", resp_r.data)
        self.assertIn(b"Harvard CS50", resp_r.data)

        # 3. GET /choice-list
        resp_cl = client.get("/choice-list")
        self.assertEqual(resp_cl.status_code, 200)
        self.assertIn(b"My TNEA Choice List", resp_cl.data)

        # 4. API /api/choice-list with authenticated session
        resp_api_get = client.get("/api/choice-list")
        self.assertEqual(resp_api_get.status_code, 200)
        data_get = json.loads(resp_api_get.data)
        self.assertEqual(data_get["status"], "success")

        # 5. API /api/checklist/toggle
        resp_api_toggle = client.post(
            "/api/checklist/toggle",
            data=json.dumps({"item_key": "review_dream_choices", "is_completed": True}),
            content_type="application/json"
        )
        self.assertEqual(resp_api_toggle.status_code, 200)
        data_toggle = json.loads(resp_api_toggle.data)
        self.assertEqual(data_toggle["status"], "success")
        self.assertTrue(data_toggle["is_completed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
