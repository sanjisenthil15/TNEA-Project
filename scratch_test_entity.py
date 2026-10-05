from models.entity_resolution import resolve_college_entity, normalize_branch_query

test_queries = [
    "Where is Eshwar College?",
    "Where is Sri Eshwar College?",
    "Tell me about Sri Eshwar",
    "Does Sri Eshwar have hostel?",
    "Prince Shri Venkateshwara Padmavathy",
    "PSG Tech",
    "SSN",
    "KPR",
    "Sri Shakthi",
    "Thiagarajar",
    "College of Engineering Guindy",
    "MIT"
]

print("=== ENTITY RESOLUTION VERIFICATION ===")
for q in test_queries:
    college, score, amb = resolve_college_entity(q)
    if college:
        print(f"Query: '{q}' -> [{college['college_code']}] {college['college_name']} (Score: {score:.2f}, District: {college.get('district')})")
    else:
        print(f"Query: '{q}' -> NOT FOUND (Ambiguous: {len(amb)})")

print("\n=== BRANCH RESOLUTION VERIFICATION ===")
for b in ["CSE", "cse", "what is cse", "what is AD", "AI&DS", "IT", "ECE", "mech", "civil"]:
    norm = normalize_branch_query(b)
    print(f"Branch query: '{b}' -> {norm}")
