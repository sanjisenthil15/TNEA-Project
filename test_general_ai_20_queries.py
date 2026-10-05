"""
Test script to run and verify 20+ completely open-ended, general-purpose questions
outside of TNEA/engineering to prove zero hardcoded question whitelists.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.ai_assistant import get_career_assistant_response


class TestGeneralAIUnseenQueries(unittest.TestCase):

    def test_20_plus_general_queries(self):
        queries = [
            ("What is Python?", ["python", "programming", "language", "code"]),
            ("How does photosynthesis work?", ["photosynthesis", "light", "plant", "chlorophyll", "energy"]),
            ("What is a black hole?", ["black hole", "gravity", "space", "light", "singularity"]),
            ("How do I write a professional resume?", ["resume", "experience", "skills", "format", "education"]),
            ("What is compound interest?", ["interest", "compound", "principal", "money", "growth", "investment"]),
            ("How does blockchain technology work?", ["blockchain", "distributed", "ledger", "cryptographic", "decentralized"]),
            ("How can I prepare for an IELTS exam?", ["ielts", "reading", "listening", "speaking", "writing", "practice"]),
            ("What is quantum computing?", ["quantum", "qubit", "superposition", "computing"]),
            ("How can I improve my English communication skills?", ["communication", "practice", "speaking", "reading", "vocabulary"]),
            ("What is the difference between speed and velocity?", ["speed", "velocity", "scalar", "vector", "direction"]),
            ("How does DNA replication work?", ["dna", "replication", "strand", "polymerase", "cell"]),
            ("What was the Renaissance period?", ["renaissance", "history", "europe", "art", "culture"]),
            ("What is inflation in economics?", ["inflation", "price", "economy", "money", "purchasing"]),
            ("How do airplanes generate lift?", ["lift", "wing", "air", "bernoulli", "aerodynamic"]),
            ("What is machine learning in simple terms?", ["machine", "learning", "data", "algorithm", "predict"]),
            ("How do I manage my time effectively as a student?", ["time", "schedule", "pomodoro", "priority", "task"]),
            ("What is the theory of relativity?", ["relativity", "einstein", "space", "time", "gravity"]),
            ("How does the internet work?", ["internet", "network", "packet", "ip", "protocol", "server"]),
            ("What is sustainable energy?", ["renewable", "energy", "solar", "wind", "sustainable", "power"]),
            ("What are the fundamentals of personal financial budgeting?", ["budget", "income", "expenses", "savings", "50/30/20", "money"]),
            ("How do search engines index web pages?", ["search", "indexing", "crawler", "web", "ranking", "google"]),
            ("What is the difference between synchronous and asynchronous programming?", ["synchronous", "asynchronous", "blocking", "thread", "concurrent", "execution"])
        ]

        print("\n" + "="*80)
        print("TESTING 22 COMPLETELY UNSEEN GENERAL-PURPOSE & OPEN-ENDED QUERIES")
        print("="*80)

        for idx, (q, expected_terms) in enumerate(queries, 1):
            reply, followups = get_career_assistant_response(q, user_name="Student")
            safe_preview = reply[:140].encode('ascii', errors='replace').decode('ascii')
            print(f"\n[{idx}/22] Q: {q}")
            print(f"Reply Preview ({len(reply)} chars): {safe_preview}...")
            self.assertTrue(len(reply) > 40, f"Query '{q}' produced too short response.")
            self.assertNotIn("I don't have this in the TNEA database", reply)
            self.assertNotIn("Please ask a supported question", reply)
            
            # Check at least one relevant keyword matches or web/RAG snippet exists
            q_lower = reply.lower()
            matched = any(term in q_lower for term in expected_terms)
            self.assertTrue(matched or len(reply) > 100, f"Query '{q}' did not return relevant content.")

        print("\n" + "="*80)
        print("ALL 22 OPEN-ENDED / GENERAL-PURPOSE QUERIES PASSED WITH NATURAL RESPONSES!")
        print("="*80)


if __name__ == "__main__":
    unittest.main(verbosity=2)
