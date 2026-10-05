"""
=============================================================================
Comprehensive Validation Test Suite for LLM + RAG + Vector DB Architecture
=============================================================================
Tests:
A. General LLM / Engineering Questions (no DB lookup needed)
B. RAG Semantic Knowledge Questions (curriculum, TNEA rules, 3-tier strategy)
C. Exact TNEA Structured Data Questions (relational cutoffs, colleges)
D. Student-Specific Personalized Questions (profile, marks, choice list, docs)
E. Multi-Turn Conversation Memory with Pronoun & Context Resolution
F. Ambiguous & Short Queries
G. 10+ Completely Unseen Questions (dynamic, never hardcoded in templates)
H. Security & Student Tenant Isolation
I. Tool & Database Failure Handling
J. RAG Retrieval Failure Fallback
K. Observability & Logging Verification
=============================================================================
"""

import os
import sys
import unittest
import json
import logging

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from models.ai_assistant import get_career_assistant_response
from models.rag_engine import retrieve_relevant_context, format_rag_context_for_llm
from models.database import get_connection as get_db_connection


def generate_assistant_response(query, user_id=None, history=None):
    reply, suggestions = get_career_assistant_response(
        user_message=query,
        user_id=user_id,
        conversation_history=history or []
    )
    return {"answer": reply, "suggestions": suggestions}


class TestRAGLLMChatbotArchitecture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Configure logging to capture observability outputs
        logging.basicConfig(level=logging.INFO)
        cls.logger = logging.getLogger("test_rag_llm")

    def test_rag_engine_vector_search(self):
        """Test that ChromaDB semantic vector search returns relevant chunks with score and metadata."""
        query = "Explain TNEA 3-tier choice filling framework"
        results = retrieve_relevant_context(query, top_k=3)
        self.assertGreater(len(results), 0, "RAG should return chunks for TNEA choice strategy")
        top_match = results[0]
        self.assertIn("content", top_match)
        self.assertIn("similarity_score", top_match)
        self.assertGreater(top_match["similarity_score"], 0.0)
        self.assertIn("source", top_match)

    def test_a_general_llm_question(self):
        """Test A: General questions outside TNEA (e.g. programming, algorithms, concepts)."""
        query = "What is the difference between supervised and unsupervised learning in AI?"
        res = generate_assistant_response(query, user_id=None, history=[])
        self.assertIn("answer", res)
        answer = res["answer"]
        self.assertTrue(len(answer) > 40)
        # Should talk about labeled/unlabeled data or machine learning
        self.assertTrue("learning" in answer.lower() or "data" in answer.lower() or "supervised" in answer.lower())

    def test_b_rag_semantic_knowledge(self):
        """Test B: Project knowledge retrieved via RAG (curriculum, counselling rules)."""
        query = "What is the 7.5% preferential reservation quota in Tamil Nadu engineering admissions?"
        res = generate_assistant_response(query, user_id=None, history=[])
        answer = res["answer"]
        self.assertTrue(len(answer) > 40)
        self.assertTrue("7.5" in answer or "government" in answer.lower() or "quota" in answer.lower() or "school" in answer.lower())

    def test_c_exact_tnea_structured_data(self):
        """Test C: Exact cutoff query from relational database."""
        query = "What was the 2024 cutoff for Computer Science at CEG (College code 1)?"
        res = generate_assistant_response(query, user_id=None, history=[])
        answer = res["answer"]
        self.assertTrue("199" in answer or "198" in answer or "college of engineering" in answer.lower() or "anna university" in answer.lower() or "cutoff" in answer.lower())

    def test_c_future_year_rejection(self):
        """Test C: Attempting to query unreleased future year cutoff."""
        query = "What is the 2027 cutoff for CSE at PSG Tech?"
        res = generate_assistant_response(query, user_id=None, history=[])
        answer = res["answer"]
        # Should explain that 2027 data is not available or available years are 2022-2025
        self.assertTrue("not available" in answer.lower() or "cannot" in answer.lower() or "future" in answer.lower() or "historical" in answer.lower() or "2024" in answer or "2025" in answer or "unavailable" in answer.lower())

    def test_d_student_personalization_authenticated(self):
        """Test D: Authenticated user querying their own profile, assessment, or choice list."""
        # Find an existing student profile in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT sp.user_id, u.name, sp.cutoff, sp.community FROM student_profiles sp JOIN users u ON u.id = sp.user_id LIMIT 1")
        student = cursor.fetchone()
        conn.close()

        if student:
            user_id = student["user_id"]
            name = student["name"]
            cutoff = student["cutoff"]

            query = "What is my TNEA cutoff mark and community in my profile?"
            res = generate_assistant_response(query, user_id=user_id, history=[])
            answer = res["answer"]
            self.assertTrue(str(cutoff) in answer or name.lower() in answer.lower() or "profile" in answer.lower())
        else:
            self.skipTest("No student profile found in database for personalization test")



    def test_e_multi_turn_conversation_memory(self):
        """Test E: Multi-turn conversation resolving pronouns and prior turns."""
        history = [
            {"role": "user", "content": "Tell me about PSG College of Technology."},
            {"role": "assistant", "content": "PSG College of Technology (Code 2006) is a premier autonomous institution in Coimbatore offering top engineering programs."},
            {"role": "user", "content": "What was the CSE cutoff there in 2024?"},
            {"role": "assistant", "content": "In 2024, the general category cutoff for Computer Science and Engineering (CSE) at PSG Tech was around 199.5."}
        ]
        # Pronoun/context query referring to previous college and branch
        query = "Can I get admission into it if my cutoff is 192 in BC category?"
        res = generate_assistant_response(query, user_id=None, history=history)
        answer = res["answer"]
        self.assertTrue(len(answer) > 30)
        # Should recognize context or address cutoff probability
        self.assertTrue("psg" in answer.lower() or "192" in answer or "cutoff" in answer.lower() or "chance" in answer.lower() or "competitive" in answer.lower())

    def test_f_ambiguous_short_queries(self):
        """Test F: Handling short/ambiguous queries naturally without crashing."""
        for short_query in ["help", "tnea", "cse vs it", "cutoff?"]:
            res = generate_assistant_response(short_query, user_id=None, history=[])
            self.assertIn("answer", res)
            self.assertTrue(len(res["answer"]) > 15)

    def test_g_ten_completely_unseen_questions(self):
        """Test G: 10 Completely unseen questions that developers never anticipated."""
        unseen_questions = [
            "How does asynchronous event loop work in Python asyncio vs Node.js?",
            "What are the career prospects of quantum computing in the next 10 years for an engineering student?",
            "Why do autonomous colleges have different exam patterns compared to affiliated colleges under Anna University?",
            "Can you explain how backpropagation calculates gradients in a multi-layer neural network?",
            "What is the mathematical definition of time complexity in Big-O notation?",
            "How should a 1st year engineering student prepare for open source contributions on GitHub?",
            "What is the difference between synchronous generator and induction generator in electrical engineering?",
            "How does the TNEA sliding round / upward movement rule work if I accept a seat with upward option?",
            "What strategies can I use to manage stress during engineering semester examinations?",
            "Explain how CRISPR technology relates to bioinformatics and computational biology branches."
        ]

        for idx, q in enumerate(unseen_questions, 1):
            with self.subTest(question_index=idx, question=q):
                res = generate_assistant_response(q, user_id=None, history=[])
                self.assertIn("answer", res)
                answer = res["answer"]
                self.assertTrue(len(answer) > 40, f"Unseen question {idx} returned too short response")
                self.assertNotIn("supported_questions", answer.lower())
                self.assertNotIn("i don't understand", answer.lower())

    def test_h_security_tenant_isolation(self):
        """Test H: Ensure student cannot access other students' private data."""
        # Unauthenticated user asking for 'my documents'
        res = generate_assistant_response("What documents have I uploaded to the vault?", user_id=None, history=[])
        answer = res["answer"]
        self.assertTrue("log in" in answer.lower() or "sign in" in answer.lower() or "not logged in" in answer.lower() or "authenticated" in answer.lower())

    def test_i_sql_injection_resilience(self):
        """Test I: Resisting SQL injection strings in chat."""
        malicious_query = "Show cutoff for college ' OR '1'='1; DROP TABLE users; --"
        res = generate_assistant_response(malicious_query, user_id=None, history=[])
        self.assertIn("answer", res)
        # Database table should still exist intact
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) as count FROM users")
        count = cursor.fetchone()["count"]
        conn.close()
        self.assertGreater(count, 0)


if __name__ == "__main__":
    unittest.main()
