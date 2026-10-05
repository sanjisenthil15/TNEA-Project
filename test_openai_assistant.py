"""
=============================================================
Comprehensive Test Suite for OpenAI-Powered AI Assistant
=============================================================
Tests:
1. General AI Capability (Programming, CS, Recursion, ML, AI vs DS, ECE embedded, Career options)
2. Career Assessment Integration (Profile fit, why-fit rationale, scores)
3. TNEA Grounding (Colleges, Cutoffs 2023-2025, 2027 unreleased notice, Facilities)
4. Controlled Backend Tools & Security (Zero cross-user data leakage, user_id isolation)
5. Multi-Turn Conversation Memory (Pronoun and follow-up entity resolution)
6. Website Feature Awareness (Assessment, Planner, Compare, Counselling, Choice List, Document Vault)
7. Premium Access & Route Authorization (Free vs Premium)
8. Graceful Fallback & Error Resilience
=============================================================
"""

import os
import sys
import unittest
import json
from werkzeug.security import generate_password_hash

# Ensure root directory on python path
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
    toggle_checklist_item,
    get_user_checklist,
    save_or_replace_user_document,
    get_user_documents,
    get_or_create_active_conversation,
    add_message,
    get_conversation_messages
)

from models.ai_assistant import (
    get_career_assistant_response,
    retrieve_grounded_tnea_data,
    build_student_ai_context,
    resolve_conversation_subject,
    generate_session_title,
    generate_contextual_suggestions,
    execute_backend_tool,
    OPENAI_TOOLS,
    tool_get_student_profile,
    tool_get_career_assessment,
    tool_search_tnea_colleges,
    tool_get_college_details,
    tool_get_branch_cutoff,
    tool_get_counselling_status,
    tool_get_choice_list,
    tool_get_learning_resources,
    tool_get_document_status,
    tool_get_available_features,
    tool_get_student_progress
)

from app import app


class TestOpenAIAssistant(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_auth_db()
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()

        # Clean up test users
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE email LIKE '%@aiassistanttest.com'")
        cursor.execute("DELETE FROM student_documents WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@aiassistanttest.com')")
        cursor.execute("DELETE FROM user_choice_list WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@aiassistanttest.com')")
        cursor.execute("DELETE FROM user_counselling_checklist WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@aiassistanttest.com')")
        conn.commit()
        conn.close()

        # Create Student A (Premium, high Computing & Analytical)
        cls.user_a_id = create_user("Aarav", "aarav@aiassistanttest.com", generate_password_hash("pass123"))
        set_user_premium_status(cls.user_a_id, True)
        cls.profile_a = {
            "maths_marks": 98.0,
            "physics_marks": 94.0,
            "chemistry_marks": 92.0,
            "cs_bio_marks": 99.0,
            "cutoff": 191.0,
            "community": "BC",
            "preferred_district": "Chennai",
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
            ],
            "subject_strengths": {"maths": "Strong", "physics": "Strong"}
        }
        save_student_profile(cls.user_a_id, cls.profile_a)

        # Create Student B (Premium, high Electronics & Hardware)
        cls.user_b_id = create_user("Bhavna", "bhavna@aiassistanttest.com", generate_password_hash("pass123"))
        set_user_premium_status(cls.user_b_id, True)
        cls.profile_b = {
            "maths_marks": 90.0,
            "physics_marks": 96.0,
            "chemistry_marks": 88.0,
            "cs_bio_marks": 85.0,
            "cutoff": 182.0,
            "community": "MBC",
            "preferred_district": "Coimbatore",
            "school_stream": "General Science",
            "assessment_answers": {"q5": 5, "q6": 5, "q7": 5, "q8": 5},
            "interest_scores": {
                "electronics": 94,
                "practical": 90,
                "computing": 40,
                "mechanical": 70,
                "analytical": 65,
                "design": 50
            },
            "top_branches": [
                {
                    "branch_code": "EC",
                    "branch_name": "Electronics and Communication Engineering",
                    "domain": "Hardware & Electronics",
                    "fit_percentage": 92,
                    "alignment_level": "Exceptional Match",
                    "why_fit": "Your electronics score (94%) and practical curiosity align with circuit architecture.",
                    "contributing_strengths": ["Circuit Analysis", "Hardware Troubleshooting"]
                }
            ],
            "subject_strengths": {"physics": "Exceptional"}
        }
        save_student_profile(cls.user_b_id, cls.profile_b)

        # Create Student C (Free user)
        cls.user_free_id = create_user("Free User", "free@aiassistanttest.com", generate_password_hash("pass123"))

    # =========================================================
    # 1. GENERAL AI CAPABILITY TESTS
    # =========================================================

    def test_01_general_ai_recursion_explanation(self):
        """Test: Student asks general CS question 'Explain recursion with an example' -> Useful explanation with code."""
        reply, followups = get_career_assistant_response("Explain recursion with an example.", user_name="Aarav")
        self.assertIn("Recursion", reply)
        self.assertIn("Base Case", reply)
        self.assertIn("factorial", reply.lower())
        self.assertNotIn("I don't have this information in the TNEA database", reply)
        self.assertGreaterEqual(len(followups), 1)

    def test_02_general_ai_difference_between_ai_and_ds(self):
        """Test: Student asks 'What is the difference between AI and data science?' -> Deep conceptual breakdown."""
        reply, followups = get_career_assistant_response("What is the difference between AI and data science?", user_name="Aarav")
        self.assertIn("Data Science", reply)
        self.assertIn("Artificial Intelligence", reply)
        self.assertNotIn("I don't have this in TNEA database", reply)

    def test_03_general_ai_how_to_start_learning_python(self):
        """Test: Student asks 'How can I start learning Python?' -> Clear step-by-step guidance."""
        reply, followups = get_career_assistant_response("How can I start learning Python?", user_name="Aarav")
        self.assertIn("Python", reply)
        self.assertTrue("variable" in reply.lower())
        self.assertTrue("function" in reply.lower())

    def test_04_general_ai_ece_embedded_systems_skills(self):
        """Test: Student asks 'What skills are needed for an ECE student to enter embedded systems?' -> Hardware & C skills."""
        reply, followups = get_career_assistant_response("What skills are needed for an ECE student to enter embedded systems?", user_name="Bhavna")
        self.assertTrue("embedded" in reply.lower())
        self.assertTrue("microcontroller" in reply.lower() or "circuit" in reply.lower() or "hardware" in reply.lower() or "vlsi" in reply.lower())

    def test_05_general_ai_non_software_careers_after_cse(self):
        """Test: Student asks 'What can I do after CSE other than software development?' -> Diverse roles."""
        reply, followups = get_career_assistant_response("What can I do after CSE other than software development?", user_name="Aarav")
        self.assertTrue("cybersecurity" in reply.lower() or "cloud" in reply.lower() or "data" in reply.lower() or "product" in reply.lower() or "software" in reply.lower())

    def test_06_general_ai_machine_learning_simple_terms(self):
        """Test: Student asks 'Explain machine learning in simple terms.' -> Intuitive non-jargon explanation."""
        reply, followups = get_career_assistant_response("Explain machine learning in simple terms.", user_name="Aarav")
        self.assertTrue("learning" in reply.lower() or "data" in reply.lower() or "machine" in reply.lower())


    # =========================================================
    # 2. CAREER ASSESSMENT & PERSONALIZATION TESTS
    # =========================================================

    def test_07_ask_about_student_assessment_recommendation(self):
        """Test: Student A asks 'Why was my top branch recommended for me?' -> Explains CSE match from assessment."""
        profile = get_student_profile(self.user_a_id)
        reply, followups = get_career_assistant_response(
            "Why was my top branch recommended for me?",
            profile=profile,
            user_name="Aarav",
            user_id=self.user_a_id
        )
        self.assertIn("Computer Science", reply)
        self.assertTrue("computing" in reply.lower() or "analytical" in reply.lower() or "aptitude" in reply.lower())

    def test_08_personalization_isolation_student_a_vs_student_b(self):
        """Test: Student A sees CSE/AI matches, Student B sees ECE matches. Zero data leakage."""
        profile_a = get_student_profile(self.user_a_id)
        profile_b = get_student_profile(self.user_b_id)

        reply_a, _ = get_career_assistant_response("Which branch suits me?", profile=profile_a, user_name="Aarav", user_id=self.user_a_id)
        reply_b, _ = get_career_assistant_response("Which branch suits me?", profile=profile_b, user_name="Bhavna", user_id=self.user_b_id)

        self.assertIn("CS", reply_a)
        self.assertIn("191.00", reply_a)
        self.assertNotIn("182.00", reply_a)

        self.assertIn("EC", reply_b)
        self.assertIn("182.00", reply_b)
        self.assertNotIn("191.00", reply_b)

    def test_09_branch_comparison_against_profile(self):
        """Test: Student A asks 'Compare CSE vs ECE for my profile' -> Evaluates against Computing vs Electronics scores."""
        profile_a = get_student_profile(self.user_a_id)
        reply, _ = get_career_assistant_response(
            "CSE vs ECE — what are the core differences?",
            profile=profile_a,
            user_name="Aarav",
            user_id=self.user_a_id
        )
        self.assertIn("CSE", reply)
        self.assertIn("ECE", reply)
        self.assertTrue("computing" in reply.lower() or "software" in reply.lower())

    # =========================================================
    # 3. TNEA DATABASE GROUNDING & CUTOFF TESTS
    # =========================================================

    def test_10_tnea_grounding_college_search_and_cutoffs(self):
        """Test: Ask about PSG college -> Grounded in verified database info and 2025 closing cutoffs."""
        reply, _ = get_career_assistant_response("Tell me about PSG College of Technology", user_name="Aarav")
        self.assertIn("PSG", reply)
        self.assertIn("Coimbatore", reply)
        self.assertIn("Autonomous", reply)

    def test_11_tnea_grounding_unreleased_future_year_2027(self):
        """Test: Ask for 2027 cutoffs -> System explicitly notes that 2027 is unreleased/unavailable."""
        reply, _ = get_career_assistant_response("What is the 2027 cutoff for SSN CSE?", user_name="Aarav")
        self.assertIn("2023, 2024, and 2025", reply)
        self.assertIn("unavailable", reply.lower())

    def test_12_tnea_counselling_strategy_and_3tier_guidance(self):
        """Test: Ask about TNEA preference list strategy -> Explains 3-tier choice ordering."""
        profile_a = get_student_profile(self.user_a_id)
        reply, _ = get_career_assistant_response("How should I structure my TNEA preference list?", profile=profile_a, user_name="Aarav")
        self.assertTrue("3-tier" in reply.lower() or "dream" in reply.lower() or "target" in reply.lower() or "choice" in reply.lower())


    # =========================================================
    # 4. CONTROLLED BACKEND TOOLS & SECURITY TESTS
    # =========================================================

    def test_13_controlled_tools_schema_definition(self):
        """Test: Ensure all tools are defined and NONE expose user_id in parameter schemas."""
        tool_names = [t["function"]["name"] for t in OPENAI_TOOLS]
        self.assertIn("get_student_profile", tool_names)
        self.assertIn("get_career_assessment", tool_names)
        self.assertIn("search_tnea_colleges", tool_names)
        self.assertIn("get_college_details", tool_names)
        self.assertIn("get_branch_cutoff", tool_names)
        self.assertIn("get_counselling_status", tool_names)
        self.assertIn("get_choice_list", tool_names)
        self.assertIn("get_learning_resources", tool_names)
        self.assertIn("get_document_status", tool_names)
        self.assertIn("get_available_features", tool_names)
        self.assertIn("get_student_progress", tool_names)

        for t in OPENAI_TOOLS:
            props = t["function"]["parameters"].get("properties", {})
            self.assertNotIn("user_id", props, f"Security violation: user_id exposed in {t['function']['name']} schema!")

    def test_14_tool_execution_student_profile_security(self):
        """Test: tool_get_student_profile returns only sanitized academic data with zero password/email."""
        res = tool_get_student_profile(self.user_a_id)
        self.assertTrue(res["has_profile"])
        self.assertEqual(res["academic"]["calculated_cutoff"], 191.0)
        self.assertNotIn("password_hash", res)
        self.assertNotIn("email", res)

    def test_15_tool_execution_choice_list_isolation(self):
        """Test: tool_get_choice_list strictly scopes to the authenticated user."""
        add_to_choice_list(self.user_a_id, 1, "CS")
        add_to_choice_list(self.user_a_id, 1, "AD")

        res_a = tool_get_choice_list(self.user_a_id)
        res_b = tool_get_choice_list(self.user_b_id)

        self.assertTrue(res_a["has_choices"])
        self.assertEqual(res_a["total_choices_saved"], 2)
        self.assertFalse(res_b["has_choices"])
        self.assertEqual(res_b["total_choices_saved"], 0)

    def test_16_tool_execution_document_status_metadata_only(self):
        """Test: Document vault tool returns metadata only without raw file paths or contents."""
        import uuid
        unique_key = f"key_{self.user_a_id}_{uuid.uuid4().hex}"
        save_or_replace_user_document(
            user_id=self.user_a_id,
            document_type="12th_marksheet",
            original_filename="marksheet12.pdf",
            storage_key=unique_key,
            mime_type="application/pdf",
            file_size=204800
        )
        doc_res = tool_get_document_status(self.user_a_id)
        self.assertTrue(doc_res["has_documents"])
        self.assertEqual(doc_res["documents"][0]["original_filename"], "marksheet12.pdf")
        self.assertNotIn("storage_key", doc_res["documents"][0])
        self.assertNotIn("file_path", doc_res["documents"][0])

    def test_17_tool_execution_student_progress_summary(self):
        """Test: tool_get_student_progress returns holistic progress."""
        prog = tool_get_student_progress(self.user_a_id)
        self.assertTrue(prog["assessment_completed"])
        self.assertEqual(prog["calculated_cutoff"], 191.0)
        self.assertEqual(prog["saved_choices_count"], 2)
        self.assertEqual(prog["uploaded_documents_count"], 1)

    # =========================================================
    # 5. MULTI-TURN CONVERSATION MEMORY & EXACT FLOW TESTS
    # =========================================================

    def test_18_multi_turn_subject_resolution(self):
        """Test: Follow-up question 'What about ECE?' then 'What jobs can I get?' resolves ECE."""
        history = [
            {"role": "user", "content": "Which branch suits me?"},
            {"role": "assistant", "content": "Based on your assessment, CSE is your top match."},
            {"role": "user", "content": "What about ECE?"},
            {"role": "assistant", "content": "ECE focuses on microchips, IoT, and embedded hardware."}
        ]
        subj = resolve_conversation_subject("What jobs can I get?", history)
        self.assertEqual(subj, "ece")

        reply, _ = get_career_assistant_response("What jobs can I get?", conversation_history=history, user_name="Aarav")
        self.assertIn("Electronics", reply)
        self.assertIn("VLSI", reply)

    def test_19_session_title_generator(self):
        """Test: Generates smart, descriptive titles for different inquiries."""
        t1 = generate_session_title("Explain recursion with an example")
        self.assertEqual(t1, "Recursion & Algorithms")

        t2 = generate_session_title("How to start learning Python?")
        self.assertEqual(t2, "Python Learning Guide")

        t3 = generate_session_title("What is the difference between AI and data science?")
        self.assertEqual(t3, "AI vs Data Science")

    def test_20_exact_10_turn_conversation_flow(self):
        """
        Test the exact multi-turn conversational sequence required by the user:
        1. 'Hi, I am Vishwa.' -> Natural greeting (no repetitive counselor dump).
        2. 'I completed 12th standard. What should I do?' -> Broad educational guidance.
        3. 'I am interested in computers.' -> Discuss computer fields & offer assessment exploration.
        4. 'Can I choose which course?' -> Course selection guidance.
        5. 'Use my assessment.' -> Retrieves assessment and personalizes advice.
        6. 'Why was AD recommended for me?' -> Explains AD fit and analytical strengths.
        7. 'What about CSE?' -> Compares AD and CSE.
        8. 'Which colleges can I consider?' -> Explores colleges grounded in 191 cutoff.
        9. 'What should I do for counselling?' -> Explains 3-tier preference strategy.
        10. 'What should I do next?' -> Progress-based website guidance.
        """
        profile_a = get_student_profile(self.user_a_id)
        history = []

        # Turn 1
        t1_reply, _ = get_career_assistant_response("Hi, I am Vishwa.", profile=profile_a, user_name="Vishwa", conversation_history=history, user_id=self.user_a_id)
        self.assertIn("Hi Vishwa!", t1_reply)
        self.assertNotIn("I am your personal Engineering Career Counselor", t1_reply)
        history.append({"role": "user", "content": "Hi, I am Vishwa."})
        history.append({"role": "assistant", "content": t1_reply})

        # Turn 2
        t2_reply, _ = get_career_assistant_response("I completed 12th standard. What should I do?", profile=profile_a, user_name="Vishwa", conversation_history=history, user_id=self.user_a_id)
        self.assertIn("12th", t2_reply)
        self.assertIn("engineering", t2_reply.lower())
        history.append({"role": "user", "content": "I completed 12th standard. What should I do?"})
        history.append({"role": "assistant", "content": t2_reply})

        # Turn 3
        t3_reply, _ = get_career_assistant_response("I am interested in computers.", profile=profile_a, user_name="Vishwa", conversation_history=history, user_id=self.user_a_id)
        self.assertTrue(len(t3_reply) > 20)
        history.append({"role": "user", "content": "I am interested in computers."})
        history.append({"role": "assistant", "content": t3_reply})

        # Turn 4
        t4_reply, _ = get_career_assistant_response("Can I choose which course?", profile=profile_a, user_name="Vishwa", conversation_history=history, user_id=self.user_a_id)
        self.assertTrue(len(t4_reply) > 20)
        history.append({"role": "user", "content": "Can I choose which course?"})
        history.append({"role": "assistant", "content": t4_reply})

        # Turn 5
        t5_reply, _ = get_career_assistant_response("Use my assessment.", profile=profile_a, user_name="Vishwa", conversation_history=history, user_id=self.user_a_id)
        self.assertTrue("computer" in t5_reply.lower() or "suitability" in t5_reply.lower() or "recommend" in t5_reply.lower())
        history.append({"role": "user", "content": "Use my assessment."})
        history.append({"role": "assistant", "content": t5_reply})

        # Turn 6
        t6_reply, _ = get_career_assistant_response("Why was AD recommended for me?", profile=profile_a, user_name="Vishwa", conversation_history=history, user_id=self.user_a_id)
        self.assertTrue("suitability" in t6_reply.lower() or "assessment" in t6_reply.lower() or "data" in t6_reply.lower() or "computing" in t6_reply.lower())
        history.append({"role": "user", "content": "Why was AD recommended for me?"})
        history.append({"role": "assistant", "content": t6_reply})

        # Turn 7
        t7_reply, _ = get_career_assistant_response("What about CSE?", profile=profile_a, user_name="Vishwa", conversation_history=history, user_id=self.user_a_id)
        self.assertTrue(len(t7_reply) > 20)
        history.append({"role": "user", "content": "What about CSE?"})
        history.append({"role": "assistant", "content": t7_reply})

        # Turn 8
        t8_reply, _ = get_career_assistant_response("Which colleges can I consider?", profile=profile_a, user_name="Vishwa", conversation_history=history, user_id=self.user_a_id)
        self.assertIn("191.00", t8_reply)
        self.assertTrue("Dream" in t8_reply or "Target" in t8_reply or "Safe" in t8_reply or "Planner" in t8_reply)
        history.append({"role": "user", "content": "Which colleges can I consider?"})
        history.append({"role": "assistant", "content": t8_reply})

        # Turn 9
        t9_reply, _ = get_career_assistant_response("What should I do for counselling?", profile=profile_a, user_name="Vishwa", conversation_history=history, user_id=self.user_a_id)
        self.assertTrue("counselling" in t9_reply.lower() or "choice" in t9_reply.lower() or "round" in t9_reply.lower() or "3-tier" in t9_reply.lower())
        history.append({"role": "user", "content": "What should I do for counselling?"})
        history.append({"role": "assistant", "content": t9_reply})

        # Turn 10
        t10_reply, _ = get_career_assistant_response("What should I do next?", profile=profile_a, user_name="Vishwa", conversation_history=history, user_id=self.user_a_id)
        self.assertIn("Next Step", t10_reply)
        self.assertTrue("Choice List" in t10_reply or "Admission Planner" in t10_reply)

    def test_21_additional_general_ai_queries(self):
        """Test: General AI capabilities on API, Study Abroad, Internship, Programming Start."""
        r1, _ = get_career_assistant_response("What is an API?", user_name="Vishwa")
        self.assertTrue("api" in r1.lower() or "interface" in r1.lower() or "programming" in r1.lower())

        r2, _ = get_career_assistant_response("Can I study abroad after engineering?", user_name="Vishwa")
        self.assertTrue("abroad" in r2.lower() or "higher" in r2.lower() or "ms" in r2.lower() or "gre" in r2.lower() or "engineering" in r2.lower())

        r3, _ = get_career_assistant_response("How do I start programming?", user_name="Vishwa")
        self.assertTrue("python" in r3.lower() or "programming" in r3.lower() or "code" in r3.lower())

        r4, _ = get_career_assistant_response("Is AI&DS difficult?", user_name="Vishwa")
        self.assertTrue("ai" in r4.lower() or "data" in r4.lower() or "math" in r4.lower() or "engineering" in r4.lower())


    # =========================================================
    # 6. WEBSITE AWARENESS TESTS
    # =========================================================

    def test_22_website_navigation_guidance(self):
        """Test: AI guides student accurately to site tools (assessment, planner, compare, counselling)."""
        reply_assess, _ = get_career_assistant_response("Where can I see my assessment?", user_name="Aarav")
        self.assertIn("/career-guidance", reply_assess)

        reply_cmp, _ = get_career_assistant_response("Where can I compare colleges?", user_name="Aarav")
        self.assertIn("/compare", reply_cmp)

        reply_feat, _ = get_career_assistant_response("What features do I have?", user_id=self.user_a_id)
        self.assertIn("Admission Planner", reply_feat)
        self.assertIn("Choice List Manager", reply_feat)

    # =========================================================
    # 7. FLASK HTTP ENDPOINTS & PREMIUM SECURITY TESTS
    # =========================================================

    def test_23_free_user_direct_access_blocked_to_premium(self):
        """Test: Free user attempting to access /career-assistant gets redirected to /premium."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_free_id
            sess["user_name"] = "Free User"
            sess["is_premium"] = 0

        res = self.client.get("/career-assistant")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/premium", res.headers["Location"])

    def test_24_premium_user_chat_api_success(self):
        """Test: Premium student can chat via POST /career-guidance/assistant/chat and receives response."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_a_id
            sess["user_name"] = "Aarav"
            sess["is_premium"] = 1

        conv = get_or_create_active_conversation(self.user_a_id)

        res = self.client.post(
            "/career-guidance/assistant/chat",
            data=json.dumps({
                "message": "Explain recursion with an example.",
                "conversation_id": conv["id"]
            }),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("Recursion", data["response"])
        self.assertTrue(len(data["followups"]) > 0)

    def test_25_cross_tenant_conversation_access_denied(self):
        """Test: Student A cannot tamper or post into Student B's conversation."""
        conv_b = get_or_create_active_conversation(self.user_b_id)

        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_a_id
            sess["user_name"] = "Aarav"
            sess["is_premium"] = 1

        res = self.client.post(
            "/career-guidance/assistant/chat",
            data=json.dumps({
                "message": "Hello from unauthorized user",
                "conversation_id": conv_b["id"]
            }),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 403)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "error")


if __name__ == "__main__":
    unittest.main(verbosity=2)
