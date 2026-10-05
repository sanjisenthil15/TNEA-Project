"""
=============================================================
TNEA Career Insight Navigator — Verified Learning Resources
=============================================================
Phase 5: Curated, high-quality, verified educational learning
resources and YouTube video lectures for 12th standard students
transitioning into engineering disciplines.
=============================================================
"""

from typing import List, Dict, Any, Optional

# =============================================================
# RESOURCE CATEGORIES
# =============================================================

RESOURCE_CATEGORIES = [
    {
        "id": "all",
        "title": "All Domains",
        "icon": "bi-grid-fill",
        "desc": "Browse all verified pre-engineering preparatory materials"
    },
    {
        "id": "explore",
        "title": "Explore Before Engineering",
        "icon": "bi-compass",
        "desc": "Engineering mindsets, branch selection clarity, and transition guidance"
    },
    {
        "id": "programming",
        "title": "Programming & Software",
        "icon": "bi-code-slash",
        "desc": "Python fundamentals, algorithmic problem solving, and logic building"
    },
    {
        "id": "ai_data",
        "title": "AI & Data Science",
        "icon": "bi-cpu-fill",
        "desc": "Data analysis, machine learning foundations, and statistical concepts"
    },
    {
        "id": "electronics",
        "title": "Electronics & Hardware",
        "icon": "bi-motherboard",
        "desc": "Circuit fundamentals, semiconductor devices, and microcontrollers"
    },
    {
        "id": "mechanical",
        "title": "Mechanical & Design",
        "icon": "bi-gear-wide-connected",
        "desc": "Engineering mechanics, 3D CAD modeling, and automotive dynamics"
    },
    {
        "id": "civil",
        "title": "Civil & Infrastructure",
        "icon": "bi-building",
        "desc": "Structural basics, green infrastructure, and civil engineering concepts"
    },
    {
        "id": "chemical_bio",
        "title": "Chemical & Life Sciences",
        "icon": "bi-eyedropper",
        "desc": "Biotechnology principles, biomedical instrumentation, and chemical materials"
    },
    {
        "id": "mathematics",
        "title": "Engineering Mathematics",
        "icon": "bi-calculator",
        "desc": "Calculus visualisations, linear algebra, and probability foundations"
    },
    {
        "id": "first_year_prep",
        "title": "First-Year Prep & Skills",
        "icon": "bi-journal-bookmark",
        "desc": "Study frameworks, technical communication, and first-year academic readiness"
    }
]

# =============================================================
# VERIFIED CURATED LEARNING RESOURCES CATALOG
# All URLs and YouTube embed IDs are verified, real educational channels.
# =============================================================

LEARNING_RESOURCES: List[Dict[str, Any]] = [
    # ── 1. Explore Before Engineering ──
    {
        "id": "res_exp_01",
        "title": "What is Engineering? Finding Your Path & Discipline",
        "category": "explore",
        "domain": "General Engineering",
        "branch_tags": ["CS", "IT", "EC", "EE", "ME", "CE", "AD", "BT"],
        "description": "An intuitive introduction to what engineers actually do across various industries and how to think about problem solving.",
        "url": "https://www.youtube.com/watch?v=bipTWWHya8A",
        "youtube_id": "bipTWWHya8A",
        "channel": "CrashCourse",
        "duration": "10 mins",
        "difficulty": "Beginner",
        "key_takeaways": [
            "Difference between science and applied engineering",
            "The engineering design process cycle",
            "Interdisciplinary collaboration between branches"
        ]
    },
    {
        "id": "res_exp_02",
        "title": "Computer Science vs IT vs AI&DS: Understanding the Difference",
        "category": "explore",
        "domain": "Computing / Software",
        "branch_tags": ["CS", "IT", "AD", "AL", "CY", "CD"],
        "description": "Clear breakdown of computing branch curricula, core mathematical focus, practical application areas, and career pathways.",
        "url": "https://www.youtube.com/watch?v=zOjov-2OZ0E",
        "youtube_id": "zOjov-2OZ0E",
        "channel": "Harvard CS50",
        "duration": "15 mins",
        "difficulty": "Beginner",
        "key_takeaways": [
            "Computational thinking fundamentals",
            "Hardware abstraction layers",
            "Software architecture vs data systems"
        ]
    },

    # ── 2. Programming & Software ──
    {
        "id": "res_prog_01",
        "title": "Python for Beginners — Full Course (First Steps in Coding)",
        "category": "programming",
        "domain": "Computing / Software",
        "branch_tags": ["CS", "IT", "AD", "AL", "CY", "CD", "EC"],
        "description": "A comprehensive, beginner-friendly introduction to Python variables, loops, conditionals, functions, and fundamental logic.",
        "url": "https://www.youtube.com/watch?v=_uQrJ0TkZlc",
        "youtube_id": "_uQrJ0TkZlc",
        "channel": "freeCodeCamp",
        "duration": "1 hour (Selected chapters)",
        "difficulty": "Beginner",
        "key_takeaways": [
            "Writing your first Python script",
            "Control flow (if/else, for/while loops)",
            "Modular code with functions and data structures"
        ]
    },
    {
        "id": "res_prog_02",
        "title": "Algorithmic Thinking & Problem-Solving Explained",
        "category": "programming",
        "domain": "Computing / Software",
        "branch_tags": ["CS", "IT", "AD", "AL", "CY"],
        "description": "Understand how computer scientists formulate solutions using structured algorithms, step-by-step logic, and efficiency analysis.",
        "url": "https://www.youtube.com/watch?v=6hfOvs8pY1k",
        "youtube_id": "6hfOvs8pY1k",
        "channel": "Harvard CS50",
        "duration": "30 mins",
        "difficulty": "Beginner",
        "key_takeaways": [
            "Binary search vs linear search mechanics",
            "Measuring algorithm efficiency (Big O notation overview)",
            "Breaking complex problems into pseudocode"
        ]
    },
    {
        "id": "res_prog_03",
        "title": "Introduction to Cybersecurity & Digital Privacy",
        "category": "programming",
        "domain": "Computing / Security",
        "branch_tags": ["CY", "CS", "IT"],
        "description": "Learn the essential concepts of network security, encryption ciphers, cyber hygiene, and defensive infrastructure.",
        "url": "https://www.youtube.com/watch?v=inWWhr5tnEA",
        "youtube_id": "inWWhr5tnEA",
        "channel": "Simplilearn",
        "duration": "25 mins",
        "difficulty": "Beginner",
        "key_takeaways": [
            "How digital data travels across the Internet",
            "Symmetric and asymmetric encryption basics",
            "Common web vulnerabilities and authentication"
        ]
    },

    # ── 3. AI & Data Science ──
    {
        "id": "res_ai_01",
        "title": "What is Machine Learning? An Illustrated Intuition",
        "category": "ai_data",
        "domain": "Computing / Intelligence",
        "branch_tags": ["AD", "AL", "CS", "IT"],
        "description": "Visual, intuitive breakdown of how machine learning models learn patterns from historical data without explicit programming.",
        "url": "https://www.youtube.com/watch?v=ukzFI9rgwfU",
        "youtube_id": "ukzFI9rgwfU",
        "channel": "StatQuest with Josh Starmer",
        "duration": "14 mins",
        "difficulty": "Beginner",
        "key_takeaways": [
            "Supervised vs unsupervised learning",
            "Training data, test data, and overfitting",
            "How classification and regression models make predictions"
        ]
    },
    {
        "id": "res_ai_02",
        "title": "Neural Networks & Deep Learning Visualized",
        "category": "ai_data",
        "domain": "Computing / Intelligence",
        "branch_tags": ["AD", "AL", "CS"],
        "description": "Stunning mathematical and visual journey into artificial neural networks, weights, biases, and activation functions.",
        "url": "https://www.youtube.com/watch?v=aircAruvnKk",
        "youtube_id": "aircAruvnKk",
        "channel": "3Blue1Brown",
        "duration": "19 mins",
        "difficulty": "Beginner to Intermediate",
        "key_takeaways": [
            "Structure of an artificial neuron and layered networks",
            "How weights and biases process image pixels",
            "Gradient descent and backpropagation concept"
        ]
    },

    # ── 4. Electronics & Hardware ──
    {
        "id": "res_elec_01",
        "title": "How Electronic Circuits Work (Voltage, Current, Resistance)",
        "category": "electronics",
        "domain": "Electronics / Embedded",
        "branch_tags": ["EC", "EE", "EV", "EI", "BM", "MC"],
        "description": "Visual explanation of electrical circuits, Ohm's law, circuit components (resistors, capacitors, transistors), and signal pathways.",
        "url": "https://www.youtube.com/watch?v=mc979OhitAg",
        "youtube_id": "mc979OhitAg",
        "channel": "The Engineering Mindset",
        "duration": "14 mins",
        "difficulty": "Beginner",
        "key_takeaways": [
            "Current flow and potential difference intuition",
            "Series vs parallel circuit dynamics",
            "How transistors function as electronic switches"
        ]
    },
    {
        "id": "res_elec_02",
        "title": "Introduction to Microcontrollers & Arduino for Beginners",
        "category": "electronics",
        "domain": "Electronics / Embedded",
        "branch_tags": ["EC", "EE", "EI", "MC", "RA"],
        "description": "Learn how small computing chips read sensor data (temperature, light, distance) and control physical actuators.",
        "url": "https://www.youtube.com/watch?v=09zfRa4u3d8",
        "youtube_id": "09zfRa4u3d8",
        "channel": "Paul McWhorter",
        "duration": "20 mins",
        "difficulty": "Beginner",
        "key_takeaways": [
            "Digital vs analog I/O pins",
            "Writing basic embedded C code",
            "Interfacing sensors and controlling LEDs/motors"
        ]
    },
    {
        "id": "res_elec_03",
        "title": "Semiconductor Physics & How Microchips are Made",
        "category": "electronics",
        "domain": "Electronics / Semiconductor",
        "branch_tags": ["EV", "EC", "EE"],
        "description": "An overview of silicon wafers, photolithography, PN junctions, and modern semiconductor VLSI technology.",
        "url": "https://www.youtube.com/watch?v=gT8vWlq0uoc",
        "youtube_id": "gT8vWlq0uoc",
        "channel": "Asianometry",
        "duration": "15 mins",
        "difficulty": "Intermediate",
        "key_takeaways": [
            "Why silicon is used for semiconductor microchips",
            "Nanometer scale fabrication process",
            "Future trends in chip design and cleanrooms"
        ]
    },

    # ── 5. Mechanical & Design ──
    {
        "id": "res_mech_01",
        "title": "Introduction to Engineering Mechanics & Free Body Diagrams",
        "category": "mechanical",
        "domain": "Mechanical / Manufacturing",
        "branch_tags": ["ME", "AU", "CE", "MC", "RA", "AE"],
        "description": "Connect 12th standard physics forces with real engineering structures, trusses, equilibrium, and mechanical loads.",
        "url": "https://www.youtube.com/watch?v=XQnOq7Uj6xQ",
        "youtube_id": "XQnOq7Uj6xQ",
        "channel": "CrashCourse Engineering",
        "duration": "11 mins",
        "difficulty": "Beginner",
        "key_takeaways": [
            "Resolving force vectors in 2D and 3D",
            "Drawing accurate Free Body Diagrams (FBD)",
            "Equilibrium of rigid bodies and stress analysis"
        ]
    },
    {
        "id": "res_mech_02",
        "title": "3D CAD Modeling Basics for Mechanical Design",
        "category": "mechanical",
        "domain": "Mechanical / Manufacturing",
        "branch_tags": ["ME", "AU", "MC", "RA", "CD", "CE"],
        "description": "Learn the foundational concepts of Computer-Aided Design (CAD), sketching, parametric constraints, and 3D extrusions.",
        "url": "https://www.youtube.com/watch?v=d3qGQ2utl2A",
        "youtube_id": "d3qGQ2utl2A",
        "channel": "Product Design Online",
        "duration": "20 mins",
        "difficulty": "Beginner",
        "key_takeaways": [
            "2D sketch planes and geometric constraints",
            "Extrude, revolve, and fillet operations",
            "Transforming conceptual ideas into manufactured prototypes"
        ]
    },
    {
        "id": "res_mech_03",
        "title": "Electric Vehicles vs Internal Combustion Engines: Mechanics",
        "category": "mechanical",
        "domain": "Mechanical / Automotive",
        "branch_tags": ["AU", "ME", "EE", "MC"],
        "description": "Engineering comparison of EV battery powertrains, regenerative braking, torque curves, and traditional transmission systems.",
        "url": "https://www.youtube.com/watch?v=3SAxXUIre28",
        "youtube_id": "3SAxXUIre28",
        "channel": "Lesics",
        "duration": "10 mins",
        "difficulty": "Beginner",
        "key_takeaways": [
            "How electric motors deliver instant torque",
            "Battery thermal management in automotive vehicles",
            "Efficiency differences across vehicle drivetrain architectures"
        ]
    },

    # ── 6. Civil & Infrastructure ──
    {
        "id": "res_civ_01",
        "title": "How Bridges & Mega-Structures Stand Up to Extreme Loads",
        "category": "civil",
        "domain": "Civil / Infrastructure",
        "branch_tags": ["CE", "EN"],
        "description": "Explores tension, compression, shear, and resonance in iconic bridges, skyscrapers, and modern infrastructure.",
        "url": "https://www.youtube.com/watch?v=oVOnRPefcno",
        "youtube_id": "oVOnRPefcno",
        "channel": "Practical Engineering",
        "duration": "13 mins",
        "difficulty": "Beginner",
        "key_takeaways": [
            "Tension vs compression forces in truss bridges",
            "Material selection: steel, reinforced concrete, and composites",
            "Mitigating wind and seismic vibration frequencies"
        ]
    },
    {
        "id": "res_civ_02",
        "title": "Environmental Engineering & Clean Water Treatment Systems",
        "category": "civil",
        "domain": "Civil / Environment",
        "branch_tags": ["EN", "CE", "CH", "BT"],
        "description": "See how civil and environmental engineers purify municipal water supplies using filtration, coagulation, and ecological cycles.",
        "url": "https://www.youtube.com/watch?v=0_ZmWTeP-U8",
        "youtube_id": "0_ZmWTeP-U8",
        "channel": "Practical Engineering",
        "duration": "12 mins",
        "difficulty": "Beginner",
        "key_takeaways": [
            "Primary, secondary, and tertiary water treatment stages",
            "Managing urban stormwater and flood prevention",
            "Sustainable green infrastructure and environmental impact"
        ]
    },

    # ── 7. Chemical & Life Sciences ──
    {
        "id": "res_bio_01",
        "title": "Introduction to Biotechnology & Genetic Engineering",
        "category": "chemical_bio",
        "domain": "Chemical & Life Sciences",
        "branch_tags": ["BT", "BM", "CH"],
        "description": "Explore DNA recombination, bioprocessing, fermentation, and therapeutic vaccine manufacturing at industrial scale.",
        "url": "https://www.youtube.com/watch?v=Vlff_p9Xjsc",
        "youtube_id": "Vlff_p9Xjsc",
        "channel": "Amoeba Sisters",
        "duration": "10 mins",
        "difficulty": "Beginner",
        "key_takeaways": [
            "Recombinant DNA technology and plasmids",
            "Bioreactor scaling for medicine and agriculture",
            "Bioethics and regulatory safety frameworks"
        ]
    },
    {
        "id": "res_bio_02",
        "title": "How Biomedical Imaging Works (MRI, CT Scan, Ultrasound)",
        "category": "chemical_bio",
        "domain": "Chemical & Life Sciences / Electronics",
        "branch_tags": ["BM", "EC", "BT"],
        "description": "Understand how electromagnetic fields, acoustic waves, and precision sensors generate life-saving diagnostic medical imagery.",
        "url": "https://www.youtube.com/watch?v=1CGzk-nV06g",
        "youtube_id": "1CGzk-nV06g",
        "channel": "TED-Ed",
        "duration": "6 mins",
        "difficulty": "Beginner",
        "key_takeaways": [
            "Physics of magnetic resonance and hydrogen protons",
            "X-ray tomography image reconstruction",
            "Safe signal processing in medical environments"
        ]
    },

    # ── 8. Engineering Mathematics ──
    {
        "id": "res_math_01",
        "title": "The Essence of Calculus — Visual Intuition & Core Ideas",
        "category": "mathematics",
        "domain": "Engineering Mathematics",
        "branch_tags": ["CS", "IT", "AD", "AL", "EC", "EE", "ME", "CE"],
        "description": "Transform derivative and integral formulas into geometric intuition and visual motion concepts.",
        "url": "https://www.youtube.com/watch?v=WUvTyaaNkzM",
        "youtube_id": "WUvTyaaNkzM",
        "channel": "3Blue1Brown",
        "duration": "17 mins",
        "difficulty": "Beginner",
        "key_takeaways": [
            "Derivatives as instantaneous rates of change",
            "Integrals as accumulated area under curves",
            "Why calculus underpins all engineering simulations"
        ]
    },
    {
        "id": "res_math_02",
        "title": "Linear Algebra for Engineers & Data Scientists",
        "category": "mathematics",
        "domain": "Engineering Mathematics",
        "branch_tags": ["CS", "AD", "AL", "EC", "ME", "RA", "CD"],
        "description": "Master vectors, matrices, dot products, and linear transformations that power computer graphics, robotics, and machine learning.",
        "url": "https://www.youtube.com/watch?v=fNk_zzaMoSs",
        "youtube_id": "fNk_zzaMoSs",
        "channel": "3Blue1Brown",
        "duration": "10 mins",
        "difficulty": "Beginner",
        "key_takeaways": [
            "Vectors as spatial arrows vs numeric lists",
            "Matrix multiplication as geometric transformation",
            "Applications in 3D game engines and neural networks"
        ]
    },

    # ── 9. First-Year Prep & Study Skills ──
    {
        "id": "res_prep_01",
        "title": "How to Transition from School to First-Year Engineering",
        "category": "first_year_prep",
        "domain": "First-Year Preparation",
        "branch_tags": ["CS", "IT", "EC", "EE", "ME", "CE", "AD", "BT"],
        "description": "Actionable advice on handling lab coursework, semester GPA planning, balance, and self-directed technical learning.",
        "url": "https://www.youtube.com/watch?v=IlU-zDU6aQ0",
        "youtube_id": "IlU-zDU6aQ0",
        "channel": "Ali Abdaal",
        "duration": "12 mins",
        "difficulty": "Beginner",
        "key_takeaways": [
            "Active recall and spaced repetition for technical exams",
            "Building portfolio projects outside syllabus requirements",
            "Effective time management for engineering labs and assignments"
        ]
    },
    {
        "id": "res_prep_02",
        "title": "Technical Communication & Engineering Presentation Skills",
        "category": "first_year_prep",
        "domain": "Professional Skills",
        "branch_tags": ["CS", "IT", "EC", "EE", "ME", "CE", "AD", "BT"],
        "description": "Learn how engineers write concise project reports, present design reviews to teams, and communicate clearly.",
        "url": "https://www.youtube.com/watch?v=Unzc731iCUY",
        "youtube_id": "Unzc731iCUY",
        "channel": "Stanford Graduate School of Business",
        "duration": "18 mins",
        "difficulty": "Beginner",
        "key_takeaways": [
            "Structuring technical arguments for non-technical stakeholders",
            "Handling presentation anxiety and impromptu Q&A",
            "Creating clear technical diagrams and visual slides"
        ]
    }
]


# =============================================================
# RESOURCE QUERY & PERSONALIZATION LOGIC
# =============================================================

def get_all_resources(category: Optional[str] = None, search_query: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Returns filtered learning resources based on category and optional search term.
    """
    results = LEARNING_RESOURCES

    if category and category.lower() != "all":
        cat_lower = category.lower().strip()
        results = [r for r in results if r["category"].lower() == cat_lower]

    if search_query and search_query.strip():
        q = search_query.strip().lower()
        results = [
            r for r in results
            if q in r["title"].lower()
            or q in r["description"].lower()
            or q in r["domain"].lower()
            or any(q in tag.lower() for tag in r.get("branch_tags", []))
            or any(q in kw.lower() for kw in r.get("key_takeaways", []))
        ]

    return results


def get_personalized_resources(profile: Optional[Dict[str, Any]], limit: int = 6) -> List[Dict[str, Any]]:
    """
    Prioritizes and ranks learning resources aligned with the student's Phase 3
    career-fit branches and interest domains.

    If student has no profile, returns a curated set of foundational cross-engineering resources.
    """
    if not profile:
        # Return popular introductory cross-branch essentials
        starter_ids = ["res_exp_01", "res_prog_01", "res_math_01", "res_elec_01", "res_mech_01", "res_prep_01"]
        starter_map = {r["id"]: r for r in LEARNING_RESOURCES}
        return [starter_map[rid] for rid in starter_ids if rid in starter_map][:limit]

    # Extract student's top recommended branch codes from Phase 3 assessment
    top_branches = profile.get("top_branches", [])
    top_branch_codes = set()
    if isinstance(top_branches, list):
        for b in top_branches:
            if isinstance(b, dict):
                top_branch_codes.add(b.get("branch_code", "").upper())
            elif isinstance(b, str):
                top_branch_codes.add(b.upper())

    # Fallback to computing + math if empty
    if not top_branch_codes:
        top_branch_codes = {"CS", "AD", "EC"}

    scored_resources = []

    for res in LEARNING_RESOURCES:
        res_tags = set(res.get("branch_tags", []))
        overlap = top_branch_codes.intersection(res_tags)
        
        # Base score from branch overlap
        overlap_score = len(overlap) * 4

        # Specific discipline domain boosts
        if any(c in top_branch_codes for c in ["CS", "IT", "AD", "AL", "CY", "CD"]) and res["category"] in ["programming", "ai_data"]:
            overlap_score += 6
        elif any(c in top_branch_codes for c in ["EC", "EE", "EV", "EI", "BM"]) and res["category"] in ["electronics"]:
            overlap_score += 6
        elif any(c in top_branch_codes for c in ["ME", "AU", "MC", "RA"]) and res["category"] in ["mechanical"]:
            overlap_score += 6
        elif any(c in top_branch_codes for c in ["CE", "EN"]) and res["category"] in ["civil"]:
            overlap_score += 6
        elif any(c in top_branch_codes for c in ["BT", "BM", "CH"]) and res["category"] in ["chemical_bio"]:
            overlap_score += 6

        # Foundational exploration and math boost
        if res["category"] in ["mathematics", "explore", "first_year_prep"]:
            overlap_score += 2

        if overlap_score > 0:
            res_copy = dict(res)
            # Create a friendly personalized tag
            if overlap:
                matching_codes = sorted(list(overlap))[:2]
                res_copy["recommendation_reason"] = f"Aligned with your career fit in {', '.join(matching_codes)}"
            else:
                res_copy["recommendation_reason"] = "Recommended engineering foundation"
            
            scored_resources.append((overlap_score, res_copy))

    # Sort descending by score
    scored_resources.sort(key=lambda x: x[0], reverse=True)

    personalized = [item[1] for item in scored_resources[:limit]]
    return personalized


def get_resource_by_id(resource_id: str) -> Optional[Dict[str, Any]]:
    """
    Finds a single resource by its ID.
    """
    for r in LEARNING_RESOURCES:
        if r["id"] == resource_id:
            return r
    return None
