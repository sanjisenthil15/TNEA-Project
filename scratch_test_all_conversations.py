import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.ai_assistant import get_career_assistant_response
from models.entity_resolution import resolve_college_entity

sample_profile = {
    "maths_marks": 98.0,
    "physics_marks": 94.0,
    "chemistry_marks": 92.0,
    "cs_bio_marks": 99.0,
    "cutoff": 191.0,
    "community": "BC",
    "preferred_district": "Coimbatore",
    "school_stream": "Computer Science",
    "interest_scores": {
        "computing": 95,
        "analytical": 92,
        "electronics": 45,
        "mechanical": 30,
        "design": 60,
        "practical": 40
    },
    "top_branches": [
        {
            "branch_code": "CS",
            "branch_name": "Computer Science and Engineering",
            "fit_percentage": 94,
            "why_fit": "Strong match with computing aptitude and problem-solving skills."
        },
        {
            "branch_code": "AD",
            "branch_name": "Artificial Intelligence and Data Science",
            "fit_percentage": 89,
            "why_fit": "High analytical reasoning alignment."
        }
    ]
}

print("==================================================")
print("TESTING 1: COLLEGE ENTITY RESOLUTION & NO CONFUSION")
print("==================================================")
college_queries = [
    "Where is Eshwar College?",
    "Where is Sri Eshwar College?",
    "Tell me about Sri Eshwar",
    "Does Sri Eshwar have hostel?",
    "Prince Shri Venkateshwara Padmavathy",
    "Does Sri Shakthi have transport?",
    "where is PSG Tech?"
]

for q in college_queries:
    resp, followups = get_career_assistant_response(
        user_message=q,
        profile=sample_profile,
        user_name="Vishwa",
        conversation_history=[]
    )
    print(f"\n[USER]: {q}")
    print(f"[ASSISTANT]:\n{resp}")
    if "Eshwar" in q:
        assert "2739" in resp or "Sri Eshwar" in resp, "Failed to resolve Eshwar to Sri Eshwar!"
        assert "Prince" not in resp, "Accidentally returned Prince Shri Venkateshwara for Eshwar!"
    if "Prince" in q:
        assert "1414" in resp or "Prince Shri Venkateshwara" in resp, "Failed to resolve Prince Shri Venkateshwara!"

print("\n==================================================")
print("TESTING 2: EXACT REQUIRED CONVERSATION SEQUENCE")
print("==================================================")
sequence = [
    "hi",
    "whether Sri Shakthi college is located in Coimbatore?",
    "AI&DS what is mean by this",
    "cse",
    "what is cse?",
    "can i get cse?",
    "what is the difference between cse and ai&ds?",
    "which one is suitable for me?",
    "why?",
    "which colleges can I consider?",
    "what should I do for counselling?",
    "what should I do next?"
]

history = []
for q in sequence:
    resp, followups = get_career_assistant_response(
        user_message=q,
        profile=sample_profile,
        user_name="Vishwa",
        conversation_history=history
    )
    history.append({"role": "user", "content": q})
    history.append({"role": "assistant", "content": resp})
    print(f"\n[USER]: {q}")
    print(f"[ASSISTANT]: {resp[:180]}...")

print("\n==================================================")
print("TESTING 3: 20+ UNSEEN GENERAL QUESTIONS (NO WHITELIST)")
print("==================================================")
general_questions = [
    "What is Python?",
    "What is recursion in programming?",
    "Explain how a black hole is formed.",
    "How does photosynthesis work in plants?",
    "What is the theory of relativity in simple terms?",
    "How do I prepare for a technical coding interview?",
    "Can you give me tips to improve English communication?",
    "How should I write an effective resume as a fresher?",
    "What is the difference between SQL and NoSQL databases?",
    "What is blockchain technology?",
    "How does the Internet send data across the world?",
    "What is the difference between RAM and ROM?",
    "How can I manage time effectively for college exams?",
    "What is quantum computing?",
    "What are mutual funds and how do they work?",
    "Why do airplanes fly? (Bernoulli principle)",
    "What is the difference between HTTP and HTTPS?",
    "How do search engines index web pages?",
    "What is machine learning in simple words?",
    "How can I prepare for studying masters abroad?",
    "What is the Pomodoro study technique?",
    "What is Ohm's law in physics?"
]

for idx, gq in enumerate(general_questions, 1):
    resp, followups = get_career_assistant_response(
        user_message=gq,
        profile=None,
        user_name="Student",
        conversation_history=[]
    )
    print(f"{idx}. [Q]: {gq}")
    print(f"   [A]: {resp[:120]}...\n")
    assert len(resp) > 30, f"Response too short for '{gq}'"
    assert "I am only" not in resp, f"Bot restriction detected for '{gq}'"

print("ALL TEST SUITES PASSED SUCCESSFULLY!")
