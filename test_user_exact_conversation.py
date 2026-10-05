"""
=============================================================
Verification Test Suite for User Required Exact 12 Questions
=============================================================
1. "hi"
2. "whether Sri Shakthi college is located in Coimbatore?"
3. "AI&DS what is mean by this"
4. "cse"
5. "what is cse?"
6. "can i get cse?"
7. "what is the difference between cse and ai&ds?"
8. "which one is suitable for me?"
9. "why?"
10. "which colleges can I consider?"
11. "what should I do for counselling?"
12. "what should I do next?"
+ Free user vs Premium user
+ Student A vs Student B data isolation
=============================================================
"""

import os
import sys
import unittest
import json
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.database import (
    init_auth_db,
    get_connection,
    create_user,
    get_user_by_id,
    save_student_profile,
    get_student_profile,
    set_user_premium_status,
    add_to_choice_list,
    get_user_choice_list,
    get_or_create_active_conversation,
    add_message,
    get_conversation_messages
)

from models.ai_assistant import (
    get_career_assistant_response,
    retrieve_grounded_tnea_data,
    build_student_ai_context,
    OPENAI_TOOLS,
    execute_backend_tool,
    tool_search_tnea_colleges,
    tool_get_college_details,
    tool_get_branch_cutoff,
    tool_get_tnea_recommendations
)

from app import app


class TestExactUserConversation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_auth_db()
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()

        # Clean up test users
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE email LIKE '%@exacttest.com'")
        cursor.execute("DELETE FROM student_documents WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@exacttest.com')")
        cursor.execute("DELETE FROM user_choice_list WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@exacttest.com')")
        cursor.execute("DELETE FROM user_counselling_checklist WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@exacttest.com')")
        conn.commit()
        conn.close()

        # Free User
        cls.free_user_id = create_user("Free Student", "free@exacttest.com", generate_password_hash("pass123"))

        # Student A (Premium, cutoff 191, CS top branch)
        cls.user_a_id = create_user("Vishwa G", "vishwa@exacttest.com", generate_password_hash("pass123"))
        set_user_premium_status(cls.user_a_id, True)
        cls.profile_a = {
            "maths_marks": 98.0,
            "physics_marks": 94.0,
            "chemistry_marks": 92.0,
            "cs_bio_marks": 99.0,
            "cutoff": 191.0,
            "community": "BC",
            "preferred_district": "Coimbatore",
            "school_stream": "Computer Science",
            "assessment_answers": {"q1": 5, "q2": 5, "q9": 5, "q12": 5},
            "interest_scores": {
                "computing": 95,
                "analytical": 92,
                "electronics": 45,
                "mechanical": 30,
                "design": 60,
                "practical": 50,
                "research": 80,
                "civil": 20,
                "chemical_bio": 25
            },
            "top_branches": [
                {
                    "branch_code": "CS",
                    "branch_name": "Computer Science and Engineering",
                    "domain": "Computing & Software Systems",
                    "fit_percentage": 94,
                    "alignment_level": "Exceptional Match",
                    "why_fit": "Your top analytical (92%) and computing (95%) scores align directly with algorithm design.",
                    "contributing_strengths": ["Algorithmic Thinking", "Data Logic"]
                },
                {
                    "branch_code": "AD",
                    "branch_name": "Artificial Intelligence and Data Science",
                    "domain": "Computing & Software Systems",
                    "fit_percentage": 91,
                    "alignment_level": "High Match",
                    "why_fit": "Strong match for statistical modeling and predictive machine learning.",
                    "contributing_strengths": ["Quantitative Analysis", "Pattern Recognition"]
                }
            ]
        }
        save_student_profile(cls.user_a_id, cls.profile_a)

        # Student B (Premium, cutoff 178, ECE top branch)
        cls.user_b_id = create_user("Ananya", "ananya@exacttest.com", generate_password_hash("pass123"))
        set_user_premium_status(cls.user_b_id, True)
        cls.profile_b = {
            "maths_marks": 88.0,
            "physics_marks": 95.0,
            "chemistry_marks": 85.0,
            "cs_bio_marks": 82.0,
            "cutoff": 178.0,
            "community": "MBC",
            "preferred_district": "Chennai",
            "school_stream": "General Science",
            "assessment_answers": {"q5": 5, "q6": 5, "q7": 5, "q8": 5},
            "interest_scores": {
                "computing": 50,
                "analytical": 70,
                "electronics": 94,
                "mechanical": 65,
                "design": 40,
                "practical": 85,
                "research": 70,
                "civil": 30,
                "chemical_bio": 35
            },
            "top_branches": [
                {
                    "branch_code": "EC",
                    "branch_name": "Electronics and Communication Engineering",
                    "domain": "Circuits & Semiconductor Systems",
                    "fit_percentage": 93,
                    "alignment_level": "Exceptional Match",
                    "why_fit": "Your electronics (94%) and practical curiosity (85%) match hardware and VLSI engineering.",
                    "contributing_strengths": ["Circuit Logic", "Microcontroller Hardware"]
                }
            ]
        }
        save_student_profile(cls.user_b_id, cls.profile_b)

    def test_exact_12_turn_conversation_sequence(self):
        """Tests each of the 12 required user queries in sequence with conversation memory."""
        profile = get_student_profile(self.user_a_id)
        history = []
        user_name = "Vishwa G"

        # 1. "hi"
        r1, _ = get_career_assistant_response("hi", profile=profile, user_name=user_name, conversation_history=history, user_id=self.user_a_id)
        self.assertTrue("hi" in r1.lower() or "hello" in r1.lower())
        self.assertNotIn("Could you share a bit more detail about what you'd like to explore", r1)
        history.append({"role": "user", "content": "hi"})
        history.append({"role": "assistant", "content": r1})

        # 2. "whether Sri Shakthi college is located in Coimbatore?"
        r2, _ = get_career_assistant_response("whether Sri Shakthi college is located in Coimbatore?", profile=profile, user_name=user_name, conversation_history=history, user_id=self.user_a_id)
        self.assertIn("Sri Shakthi", r2)
        self.assertIn("Coimbatore", r2)
        self.assertTrue("Yes" in r2 or "yes" in r2)
        self.assertNotIn("Could you share a bit more detail", r2)
        history.append({"role": "user", "content": "whether Sri Shakthi college is located in Coimbatore?"})
        history.append({"role": "assistant", "content": r2})

        # 3. "AI&DS what is mean by this"
        r3, _ = get_career_assistant_response("AI&DS what is mean by this", profile=profile, user_name=user_name, conversation_history=history, user_id=self.user_a_id)
        self.assertIn("Artificial Intelligence", r3)
        self.assertIn("Data Science", r3)
        self.assertIn("Machine Learning", r3)
        self.assertNotIn("Could you share a bit more detail", r3)
        history.append({"role": "user", "content": "AI&DS what is mean by this"})
        history.append({"role": "assistant", "content": r3})

        # 4. "cse"
        r4, _ = get_career_assistant_response("cse", profile=profile, user_name=user_name, conversation_history=history, user_id=self.user_a_id)
        self.assertIn("Computer Science", r4)
        self.assertNotIn("Could you share a bit more detail", r4)
        history.append({"role": "user", "content": "cse"})
        history.append({"role": "assistant", "content": r4})

        # 5. "what is cse?"
        r5, _ = get_career_assistant_response("what is cse?", profile=profile, user_name=user_name, conversation_history=history, user_id=self.user_a_id)
        self.assertIn("Computer Science", r5)
        self.assertIn("Software", r5)
        self.assertNotIn("Could you share a bit more detail", r5)
        history.append({"role": "user", "content": "what is cse?"})
        history.append({"role": "assistant", "content": r5})

        # 6. "can i get cse?"
        r6, _ = get_career_assistant_response("can i get cse?", profile=profile, user_name=user_name, conversation_history=history, user_id=self.user_a_id)
        self.assertIn("191.00", r6)
        self.assertTrue("Target" in r6 or "Dream" in r6 or "Yes" in r6)
        self.assertNotIn("Could you share a bit more detail", r6)
        history.append({"role": "user", "content": "can i get cse?"})
        history.append({"role": "assistant", "content": r6})

        # 7. "what is the difference between cse and ai&ds?"
        r7, _ = get_career_assistant_response("what is the difference between cse and ai&ds?", profile=profile, user_name=user_name, conversation_history=history, user_id=self.user_a_id)
        self.assertIn("CSE", r7)
        self.assertIn("AI & Data Science", r7)
        self.assertIn("Machine Learning", r7)
        self.assertNotIn("Could you share a bit more detail", r7)
        history.append({"role": "user", "content": "what is the difference between cse and ai&ds?"})
        history.append({"role": "assistant", "content": r7})

        # 8. "which one is suitable for me?"
        r8, _ = get_career_assistant_response("which one is suitable for me?", profile=profile, user_name=user_name, conversation_history=history, user_id=self.user_a_id)
        self.assertIn("Suitability", r8)
        self.assertTrue("Computer Science" in r8 or "CS" in r8)
        self.assertNotIn("Could you share a bit more detail", r8)
        history.append({"role": "user", "content": "which one is suitable for me?"})
        history.append({"role": "assistant", "content": r8})

        # 9. "why?"
        r9, _ = get_career_assistant_response("why?", profile=profile, user_name=user_name, conversation_history=history, user_id=self.user_a_id)
        self.assertTrue("Computing" in r9 or "Analytical" in r9 or "score" in r9.lower())
        self.assertNotIn("Could you share a bit more detail", r9)
        history.append({"role": "user", "content": "why?"})
        history.append({"role": "assistant", "content": r9})

        # 10. "which colleges can I consider?"
        r10, _ = get_career_assistant_response("which colleges can I consider?", profile=profile, user_name=user_name, conversation_history=history, user_id=self.user_a_id)
        self.assertIn("191.00", r10)
        self.assertTrue("Dream" in r10 or "Target" in r10 or "Safe" in r10)
        self.assertNotIn("Could you share a bit more detail", r10)
        history.append({"role": "user", "content": "which colleges can I consider?"})
        history.append({"role": "assistant", "content": r10})

        # 11. "what should I do for counselling?"
        r11, _ = get_career_assistant_response("what should I do for counselling?", profile=profile, user_name=user_name, conversation_history=history, user_id=self.user_a_id)
        self.assertIn("3-Tier", r11)
        self.assertIn("Choices 1–10", r11)
        self.assertNotIn("Could you share a bit more detail", r11)
        history.append({"role": "user", "content": "what should I do for counselling?"})
        history.append({"role": "assistant", "content": r11})

        # 12. "what should I do next?"
        r12, _ = get_career_assistant_response("what should I do next?", profile=profile, user_name=user_name, conversation_history=history, user_id=self.user_a_id)
        self.assertIn("Next Step", r12)
        self.assertTrue("Choice List" in r12 or "Admission Planner" in r12 or "Assessment" in r12)
        self.assertNotIn("Could you share a bit more detail", r12)

    def test_student_isolation_and_security(self):
        """Verifies Student A and Student B have completely isolated profiles and cutoff data."""
        p_a = get_student_profile(self.user_a_id)
        p_b = get_student_profile(self.user_b_id)

        reply_a, _ = get_career_assistant_response("Which branch suits me?", profile=p_a, user_name="Vishwa G", user_id=self.user_a_id)
        reply_b, _ = get_career_assistant_response("Which branch suits me?", profile=p_b, user_name="Ananya", user_id=self.user_b_id)

        # Student A sees CS and 191.00
        self.assertIn("CS", reply_a)
        self.assertIn("191.00", reply_a)
        self.assertNotIn("178.00", reply_a)

        # Student B sees EC and 178.00
        self.assertIn("EC", reply_b)
        self.assertIn("178.00", reply_b)
        self.assertNotIn("191.00", reply_b)

    def test_free_user_access_blocked(self):
        """Ensures free user is prevented from unauthorized chat endpoint."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.free_user_id
            sess["user_name"] = "Free Student"
            sess["is_premium"] = 0

        res = self.client.get("/career-assistant")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/premium", res.headers["Location"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
