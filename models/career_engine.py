"""
=============================================================
TNEA Career Insight Navigator — Career Recommendation Engine
=============================================================
Phase 3: Transparent, explainable Career Recommendation Engine
for 12th standard students. Translates school subject performance
and self-assessment responses into validated engineering domain
compatibility scores, personalized explanations, and exploratory guidance.
"""

from typing import Dict, List, Any, Optional

# =============================================================
# 1. ASSESSMENT QUESTION CATALOG (12th Standard Friendly)
# No prior engineering / coding knowledge assumed.
# 16 Practical / Scenario-based questions across 4 intuitive steps.
# =============================================================

ASSESSMENT_QUESTIONS = [
    # ── Step 1: Thinking & Problem Solving ──
    {
        "id": "q1",
        "category": "logic_math",
        "dimension": "analytical",
        "prompt": "I enjoy solving numerical puzzles, Sudoku, algebra riddles, or finding patterns in numbers.",
        "context": "Analytical & Mathematical Reasoning"
    },
    {
        "id": "q2",
        "category": "logic_math",
        "dimension": "computing",
        "prompt": "When faced with a complex task, I like breaking it down into step-by-step clear rules or flowcharts.",
        "context": "Algorithmic & Systematic Thinking"
    },
    {
        "id": "q3",
        "category": "logic_math",
        "dimension": "research",
        "prompt": "I am deeply curious to understand 'why' things happen in nature and science, rather than just memorising formulas.",
        "context": "Curiosity & Scientific Inquiry"
    },
    {
        "id": "q4",
        "category": "logic_math",
        "dimension": "analytical",
        "prompt": "I prefer using charts, graphs, and structured data to make logical decisions rather than guessing.",
        "context": "Data & Quantitative Analysis"
    },

    # ── Step 2: Machines, Hardware & Practical Systems ──
    {
        "id": "q5",
        "category": "hardware_systems",
        "dimension": "mechanical",
        "prompt": "I am fascinated by how physical machines work (cars, bike engines, drone propellers, gears, and motors).",
        "context": "Mechanical & Physical Systems"
    },
    {
        "id": "q6",
        "category": "hardware_systems",
        "dimension": "electronics",
        "prompt": "I like tinkering with electronic gadgets, switches, battery circuits, remote controls, or smartphones.",
        "context": "Electronics & Circuitry"
    },
    {
        "id": "q7",
        "category": "hardware_systems",
        "dimension": "practical",
        "prompt": "I learn better by doing hands-on experiments, assembling models, or fixing broken items than only reading theory.",
        "context": "Hands-on & Experimental Orientation"
    },
    {
        "id": "q8",
        "category": "hardware_systems",
        "dimension": "electronics",
        "prompt": "I find automated devices (like automatic sensor doors, smart bulbs, or robotic toys) exciting to explore.",
        "context": "Robotics & Smart Hardware"
    },

    # ── Step 3: Software, Digital Tools & Technology ──
    {
        "id": "q9",
        "category": "digital_software",
        "dimension": "computing",
        "prompt": "I enjoy exploring computer applications, website features, or automating repetitive tasks with digital tools.",
        "context": "Software & Digital Exploration"
    },
    {
        "id": "q10",
        "category": "digital_software",
        "dimension": "analytical",
        "prompt": "I like games that require strategy, resource planning, and predictive thinking (e.g., Chess, strategy games).",
        "context": "Strategy & Logic Puzzles"
    },
    {
        "id": "q11",
        "category": "digital_software",
        "dimension": "design",
        "prompt": "I care about visual appeal, clean layouts, user-friendly posters, drawing, or 3D visualisations.",
        "context": "Visual Design & Creative Presentation"
    },
    {
        "id": "q12",
        "category": "digital_software",
        "dimension": "computing",
        "prompt": "I am interested in how internet apps connect millions of users and process huge amounts of search results instantly.",
        "context": "Internet & Information Systems"
    },

    # ── Step 4: Structures, Environment, Life Sciences & Impact ──
    {
        "id": "q13",
        "category": "environment_life",
        "dimension": "civil",
        "prompt": "I notice architectural buildings, bridges, metro rails, road planning, and city layouts with keen interest.",
        "context": "Infrastructure & Structural Planning"
    },
    {
        "id": "q14",
        "category": "environment_life",
        "dimension": "chemical_bio",
        "prompt": "I find chemistry lab reactions, medical equipment, biotechnology, or how materials change states intriguing.",
        "context": "Chemical & Life Sciences"
    },
    {
        "id": "q15",
        "category": "environment_life",
        "dimension": "civil",
        "prompt": "I care about solving environmental issues like renewable solar energy, clean water supply, and sustainable construction.",
        "context": "Sustainability & Environmental Engineering"
    },
    {
        "id": "q16",
        "category": "environment_life",
        "dimension": "research",
        "prompt": "I enjoy working on long-term project investigations and creating innovative solutions that help society.",
        "context": "Societal Impact & Innovation"
    },
]


# =============================================================
# 2. ENGINEERING DOMAIN DEFINITIONS & VERIFIED DATABASE BRANCHES
# All branch codes strictly verified against branches table in tnea.db
# =============================================================

BRANCH_PROFILES = [
    # ── DOMAIN: Computing & Software Systems ──
    {
        "branch_code": "CS",
        "branch_name": "Computer Science & Engineering",
        "domain": "Computing / Software",
        "primary_weights": {
            "computing": 0.40,
            "analytical": 0.30,
            "design": 0.15,
            "research": 0.15
        },
        "subject_weights": {"maths": 0.50, "physics": 0.30, "chemistry": 0.20},
        "description": "Focuses on software architecture, algorithm design, cloud computing, cybersecurity, and digital platforms.",
        "core_focus": ["Software Development", "Algorithm Design", "Operating Systems", "Cloud & Web Architectures"],
        "explore_topics": ["Basic Python/C++ programming", "Data structures & problem solving", "How computer networks and operating systems work"],
        "alternative_reason": "Core foundation for all computational fields; allows flexible pivot into any software specialization."
    },
    {
        "branch_code": "IT",
        "branch_name": "Information Technology",
        "domain": "Computing / Software",
        "primary_weights": {
            "computing": 0.45,
            "analytical": 0.25,
            "practical": 0.15,
            "design": 0.15
        },
        "subject_weights": {"maths": 0.45, "physics": 0.35, "chemistry": 0.20},
        "description": "Deals with applied software systems, networking infrastructure, enterprise databases, and digital security solutions.",
        "core_focus": ["Applied Software Engineering", "Database Systems", "Network Infrastructure", "Enterprise Web Apps"],
        "explore_topics": ["Database management & SQL", "Web application development", "Network security fundamentals"],
        "alternative_reason": "Directly applied software curriculum with strong industry alignment for enterprise systems and networking."
    },
    {
        "branch_code": "AD",
        "branch_name": "Artificial Intelligence & Data Science",
        "domain": "Computing / Intelligence",
        "primary_weights": {
            "analytical": 0.40,
            "computing": 0.35,
            "research": 0.15,
            "design": 0.10
        },
        "subject_weights": {"maths": 0.55, "physics": 0.25, "chemistry": 0.20},
        "description": "Combines mathematical statistics, pattern recognition, and machine learning models to analyze complex datasets.",
        "core_focus": ["Statistical Modeling", "Machine Learning", "Data Mining & Visualization", "Predictive Analytics"],
        "explore_topics": ["Statistical math & probability", "Data visualization with Python/Excel", "Introductory machine learning concepts"],
        "alternative_reason": "Excels for students with high mathematical curiosity wanting to specialize in predictive data algorithms."
    },
    {
        "branch_code": "AL",
        "branch_name": "Artificial Intelligence & Machine Learning",
        "domain": "Computing / Intelligence",
        "primary_weights": {
            "computing": 0.40,
            "analytical": 0.35,
            "research": 0.15,
            "electronics": 0.10
        },
        "subject_weights": {"maths": 0.55, "physics": 0.30, "chemistry": 0.15},
        "description": "Specialized curriculum on autonomous algorithms, neural networks, computer vision, and intelligent decision systems.",
        "core_focus": ["Neural Networks", "Computer Vision", "Natural Language Processing", "Autonomous Systems"],
        "explore_topics": ["Linear algebra & calculus", "Logic optimization algorithms", "Computer vision basics"],
        "alternative_reason": "High-growth specialized intelligence branch bridging mathematical optimization with autonomous agents."
    },
    {
        "branch_code": "CY",
        "branch_name": "Cyber Security",
        "domain": "Computing / Security",
        "primary_weights": {
            "computing": 0.40,
            "analytical": 0.30,
            "research": 0.15,
            "practical": 0.15
        },
        "subject_weights": {"maths": 0.50, "physics": 0.30, "chemistry": 0.20},
        "description": "Protects digital networks, cryptography, ethical hacking, digital forensics, and cloud infrastructure.",
        "core_focus": ["Network Defense", "Cryptography & Ciphers", "Vulnerability Analysis", "Security Protocols"],
        "explore_topics": ["Linux system operations", "Networking protocols (TCP/IP)", "Cryptography basics and puzzles"],
        "alternative_reason": "Essential specialization for analytical thinkers interested in defensive digital infrastructure."
    },
    {
        "branch_code": "CD",
        "branch_name": "Computer Science & Design",
        "domain": "Computing / Design",
        "primary_weights": {
            "design": 0.35,
            "computing": 0.35,
            "analytical": 0.15,
            "practical": 0.15
        },
        "subject_weights": {"maths": 0.45, "physics": 0.30, "chemistry": 0.25},
        "description": "Bridges core computer science algorithms with user experience (UX) design, 3D graphics, and digital media.",
        "core_focus": ["UI/UX Design Systems", "Front-end Architecture", "Interactive Graphics", "Human-Computer Interaction"],
        "explore_topics": ["UI wireframing & Figma basics", "Interactive web frontends (HTML/CSS/JS)", "Digital typography & visual balance"],
        "alternative_reason": "Ideal hybrid branch merging technical programming with creative visual presentation."
    },

    # ── DOMAIN: Electronics & Embedded Systems ──
    {
        "branch_code": "EC",
        "branch_name": "Electronics & Communication Engineering",
        "domain": "Electronics / Embedded",
        "primary_weights": {
            "electronics": 0.40,
            "analytical": 0.25,
            "practical": 0.20,
            "computing": 0.15
        },
        "subject_weights": {"physics": 0.45, "maths": 0.40, "chemistry": 0.15},
        "description": "Covers semiconductor microchips, wireless communication, microcontrollers, IoT devices, and signal processing.",
        "core_focus": ["VLSI Microchip Design", "Wireless & 5G Communications", "Embedded IoT Systems", "Digital Signal Processing"],
        "explore_topics": ["Arduino / Microcontroller basics", "Semiconductor physics & diodes", "Signal frequency and wave transmission"],
        "alternative_reason": "Versatile core branch spanning both physical hardware chips and embedded software programming."
    },
    {
        "branch_code": "EE",
        "branch_name": "Electrical & Electronics Engineering",
        "domain": "Electrical / Power Systems",
        "primary_weights": {
            "electronics": 0.35,
            "mechanical": 0.25,
            "practical": 0.20,
            "analytical": 0.20
        },
        "subject_weights": {"physics": 0.50, "maths": 0.35, "chemistry": 0.15},
        "description": "Focuses on electrical power generation, electric vehicles (EV), renewable smart grids, motors, and power electronics.",
        "core_focus": ["Electric Vehicle Powertrains", "Renewable Solar & Wind Grids", "Power Systems", "Industrial Drives & Control"],
        "explore_topics": ["Electric motors & transformers", "Battery storage & EV systems", "Renewable power grid concepts"],
        "alternative_reason": "High demand in EV and green energy transition; provides solid foundation in large-scale electrical power."
    },
    {
        "branch_code": "EV",
        "branch_name": "Electronics Engineering (VLSI Design & Technology)",
        "domain": "Electronics / Semiconductor",
        "primary_weights": {
            "electronics": 0.45,
            "analytical": 0.25,
            "computing": 0.20,
            "research": 0.10
        },
        "subject_weights": {"physics": 0.45, "maths": 0.40, "chemistry": 0.15},
        "description": "Deep-dive specialization into semiconductor fabrication, microchip architecture, and integrated circuit design.",
        "core_focus": ["Chip Architecture", "Digital IC Design", "Semiconductor Physics", "Hardware Description Languages"],
        "explore_topics": ["Logic gates and Boolean algebra", "Microchip fabrication overview", "Verilog/VHDL introduction"],
        "alternative_reason": "Strategic national semiconductor focus area for students passionate about microchip hardware design."
    },
    {
        "branch_code": "EI",
        "branch_name": "Electronics & Instrumentation Engineering",
        "domain": "Electronics / Automation",
        "primary_weights": {
            "electronics": 0.35,
            "practical": 0.25,
            "analytical": 0.20,
            "mechanical": 0.20
        },
        "subject_weights": {"physics": 0.45, "maths": 0.35, "chemistry": 0.20},
        "description": "Deals with precision sensors, industrial process control, automated measurement, and calibration instruments.",
        "core_focus": ["Industrial Sensor Systems", "PLC & SCADA Automation", "Biomedical Instrumentation", "Process Control"],
        "explore_topics": ["Sensor types (temperature, pressure, optical)", "Feedback control loops", "Automation in manufacturing plants"],
        "alternative_reason": "Connects electronic sensing with industrial manufacturing automation across energy and pharma plants."
    },

    # ── DOMAIN: Mechanical & Industrial Systems ──
    {
        "branch_code": "ME",
        "branch_name": "Mechanical Engineering",
        "domain": "Mechanical / Manufacturing",
        "primary_weights": {
            "mechanical": 0.45,
            "practical": 0.25,
            "design": 0.15,
            "analytical": 0.15
        },
        "subject_weights": {"physics": 0.50, "maths": 0.35, "chemistry": 0.15},
        "description": "Foundation of physical machinery, thermodynamics, aerodynamics, 3D CAD manufacturing, and robotics.",
        "core_focus": ["Thermodynamics & Heat Power", "Machine Design & Mechanics", "CAD/CAM Simulation", "Materials Engineering"],
        "explore_topics": ["Basic 3D CAD modeling software", "Internal combustion engines vs electric motors", "Fluid dynamics and strength of materials"],
        "alternative_reason": "Core foundational discipline with vast application in aerospace, automotive, energy, and defense."
    },
    {
        "branch_code": "MC",
        "branch_name": "Mechatronics Engineering",
        "domain": "Mechanical / Electronics Hybrid",
        "primary_weights": {
            "mechanical": 0.30,
            "electronics": 0.30,
            "computing": 0.25,
            "practical": 0.15
        },
        "subject_weights": {"physics": 0.45, "maths": 0.40, "chemistry": 0.15},
        "description": "Synergizes mechanical motion, electronic actuators, and computer programming to design automated robotic machines.",
        "core_focus": ["Robotic Kinematics", "Microcontroller Actuation", "Electro-Pneumatic Systems", "Smart Automation"],
        "explore_topics": ["Building simple robotic kits", "Combining servo motors with sensor inputs", "PLC programming basics"],
        "alternative_reason": "Seamless cross-disciplinary branch for students who enjoy both mechanical hardware and software control."
    },
    {
        "branch_code": "RA",
        "branch_name": "Robotics & Automation",
        "domain": "Mechanical / Robotics",
        "primary_weights": {
            "mechanical": 0.30,
            "computing": 0.30,
            "electronics": 0.25,
            "practical": 0.15
        },
        "subject_weights": {"physics": 0.45, "maths": 0.40, "chemistry": 0.15},
        "description": "Focuses on industrial robotic arms, autonomous mobile robots (AMR), computer vision control, and smart factories.",
        "core_focus": ["Industrial Robotics", "Autonomous Navigation", "Sensors & Actuators", "Computer Vision Integration"],
        "explore_topics": ["Robot kinematics & degrees of freedom", "Path planning algorithms", "ROS (Robot Operating System) overview"],
        "alternative_reason": "High-demand modern specialization modernizing factory assembly lines and automated logistics."
    },
    {
        "branch_code": "AU",
        "branch_name": "Automobile Engineering",
        "domain": "Mechanical / Automotive",
        "primary_weights": {
            "mechanical": 0.40,
            "practical": 0.25,
            "electronics": 0.20,
            "design": 0.15
        },
        "subject_weights": {"physics": 0.50, "maths": 0.35, "chemistry": 0.15},
        "description": "Dedicated to vehicle chassis design, aerodynamics, powertrain engineering, transmission systems, and EV battery packs.",
        "core_focus": ["Vehicle Dynamics", "Automotive Powertrains", "Chassis & Aerodynamics", "EV Battery & Motor Integration"],
        "explore_topics": ["Automotive aerodynamics", "Electric vs Hybrid drivetrain mechanics", "Vehicle suspension and brake systems"],
        "alternative_reason": "Specialized passion track for students focused specifically on motor vehicles, racing, and EV transportation."
    },

    # ── DOMAIN: Civil & Infrastructure Systems ──
    {
        "branch_code": "CE",
        "branch_name": "Civil Engineering",
        "domain": "Civil / Infrastructure",
        "primary_weights": {
            "civil": 0.50,
            "practical": 0.20,
            "design": 0.15,
            "analytical": 0.15
        },
        "subject_weights": {"physics": 0.45, "maths": 0.35, "chemistry": 0.20},
        "description": "Covers structural analysis, mega-transportation networks, smart city planning, geotechnical engineering, and construction.",
        "core_focus": ["Structural Design & Analysis", "Geotechnical Engineering", "Transportation & Highway Planning", "Construction Management"],
        "explore_topics": ["Structural load calculations & bridges", "Surveying & GIS mapping tools", "Sustainable building materials (green concrete)"],
        "alternative_reason": "Enduring core discipline driving national infrastructure, smart cities, and government engineering services."
    },
    {
        "branch_code": "EN",
        "branch_name": "Environmental Engineering",
        "domain": "Civil / Environment",
        "primary_weights": {
            "civil": 0.40,
            "chemical_bio": 0.25,
            "research": 0.20,
            "practical": 0.15
        },
        "subject_weights": {"chemistry": 0.40, "physics": 0.35, "maths": 0.25},
        "description": "Addresses water purification systems, air pollution control, solid waste recycling, and ecological sustainability.",
        "core_focus": ["Water Treatment Systems", "Air Quality Monitoring", "Waste-to-Energy Processing", "Environmental Impact Assessment"],
        "explore_topics": ["Water filtration chemistry", "Renewable eco-engineering solutions", "Climate impact mitigation strategies"],
        "alternative_reason": "High societal impact branch focusing on sustainability, clean water, and global green technologies."
    },

    # ── DOMAIN: Chemical & Life Sciences ──
    {
        "branch_code": "BT",
        "branch_name": "Biotechnology",
        "domain": "Chemical & Life Sciences",
        "primary_weights": {
            "chemical_bio": 0.50,
            "research": 0.25,
            "analytical": 0.15,
            "electronics": 0.10
        },
        "subject_weights": {"chemistry": 0.45, "physics": 0.30, "maths": 0.25},
        "description": "Applies biological principles, genetic engineering, molecular diagnostics, and bioprocess technology to medicine and agriculture.",
        "core_focus": ["Bioprocess Engineering", "Genetic & Molecular Biology", "Immunology & Vaccine Development", "Agricultural Biotech"],
        "explore_topics": ["DNA structure & gene editing basics", "Fermentation & enzyme processes", "Bioinformatics data analysis"],
        "alternative_reason": "Excellent pathway for students with strong chemistry/biology curiosity to engineer life science solutions."
    },
    {
        "branch_code": "BM",
        "branch_name": "Biomedical Engineering",
        "domain": "Chemical & Life Sciences / Electronics",
        "primary_weights": {
            "chemical_bio": 0.35,
            "electronics": 0.30,
            "research": 0.20,
            "analytical": 0.15
        },
        "subject_weights": {"physics": 0.40, "chemistry": 0.35, "maths": 0.25},
        "description": "Integrates medical imaging (MRI/CT), bio-sensors, prosthetic limbs, and hospital healthcare equipment with engineering design.",
        "core_focus": ["Medical Imaging Systems", "Biosensors & Implants", "Prosthetics & Biomechanics", "Clinical Healthcare Instrumentation"],
        "explore_topics": ["ECG / EEG bio-signal processing", "Biomechanics of artificial limbs", "Medical scanning technologies"],
        "alternative_reason": "Inspiring intersection of electronics and human healthcare aiding doctors with life-saving equipment."
    },
    {
        "branch_code": "CH",
        "branch_name": "Chemical Engineering",
        "domain": "Process & Materials",
        "primary_weights": {
            "chemical_bio": 0.45,
            "analytical": 0.25,
            "practical": 0.15,
            "research": 0.15
        },
        "subject_weights": {"chemistry": 0.50, "maths": 0.30, "physics": 0.20},
        "description": "Focuses on industrial chemical synthesis, refinery processes, polymer materials, energy storage batteries, and process optimization.",
        "core_focus": ["Chemical Reaction Engineering", "Mass & Heat Transfer", "Process Simulation", "Petrochemicals & Green Materials"],
        "explore_topics": ["Thermodynamic chemical cycles", "Battery chemistry for EVs", "Industrial distillation and separation"],
        "alternative_reason": "Core process engineering discipline powering pharmaceutical production, materials science, and energy storage."
    },

    # ── DOMAIN: Design & Creative Technology ──
    {
        "branch_code": "DA",
        "branch_name": "Bachelor of Design",
        "domain": "Design / Creative Engineering",
        "primary_weights": {
            "design": 0.50,
            "practical": 0.25,
            "computing": 0.15,
            "research": 0.10
        },
        "subject_weights": {"maths": 0.35, "physics": 0.35, "chemistry": 0.30},
        "description": "Emphasizes product aesthetics, ergonomic design, industrial styling, visual communication, and user research.",
        "core_focus": ["Industrial Product Design", "Ergonomics & Styling", "Human-Centered Design", "Digital Media & Prototyping"],
        "explore_topics": ["Design sketching and rapid prototyping", "Ergonomics and physical product usability", "Design thinking methodology"],
        "alternative_reason": "Direct creative engineering path focusing on physical and digital product form, feel, and function."
    }
]


# =============================================================
# 3. CALCULATION & SCORING HELPERS
# =============================================================

def calculate_tnea_cutoff(maths: float, physics: float, chemistry: float) -> float:
    """
    Standard TNEA Cutoff Formula:
    Cutoff = Maths + (Physics / 2) + (Chemistry / 2)
    Maximum score = 100 + 50 + 50 = 200.00
    """
    m = max(0.0, min(100.0, float(maths)))
    p = max(0.0, min(100.0, float(physics)))
    c = max(0.0, min(100.0, float(chemistry)))
    cutoff = m + (p / 2.0) + (c / 2.0)
    return round(cutoff, 2)


def compute_subject_strengths(maths: float, physics: float, chemistry: float, cs_bio: Optional[float] = None) -> Dict[str, Any]:
    """
    Categorizes subject performance into intuitive strength tiers.
    """
    def categorize(score):
        if score is None:
            return {"score": None, "level": "Not Specified", "badge": "secondary"}
        s = float(score)
        if s >= 85:
            return {"score": s, "level": "Strong Foundation", "badge": "success"}
        elif s >= 65:
            return {"score": s, "level": "Solid Understanding", "badge": "primary"}
        elif s >= 45:
            return {"score": s, "level": "Developing", "badge": "warning"}
        else:
            return {"score": s, "level": "Foundational", "badge": "secondary"}

    return {
        "maths": categorize(maths),
        "physics": categorize(physics),
        "chemistry": categorize(chemistry),
        "cs_bio": categorize(cs_bio) if cs_bio is not None else None
    }


def compute_interest_dimensions(answers: Dict[str, int]) -> Dict[str, int]:
    """
    Computes normalized percentage scores (0 - 100%) for 9 core dimensions.
    """
    dimension_totals: Dict[str, float] = {
        "analytical": 0.0,
        "computing": 0.0,
        "electronics": 0.0,
        "mechanical": 0.0,
        "civil": 0.0,
        "chemical_bio": 0.0,
        "design": 0.0,
        "research": 0.0,
        "practical": 0.0
    }
    dimension_counts: Dict[str, int] = {k: 0 for k in dimension_totals}

    for q in ASSESSMENT_QUESTIONS:
        qid = q["id"]
        dim = q["dimension"]
        # Score is 1 to 5 (default 3)
        val = int(answers.get(qid, 3))
        val = max(1, min(5, val))
        dimension_totals[dim] += val
        dimension_counts[dim] += 1

    normalized: Dict[str, int] = {}
    for dim, total in dimension_totals.items():
        count = dimension_counts[dim]
        if count > 0:
            # Convert 1-5 scale average into 0-100%
            avg = total / count
            pct = int(round(((avg - 1.0) / 4.0) * 100.0))
            normalized[dim] = max(10, min(100, pct))
        else:
            normalized[dim] = 50

    return normalized


# =============================================================
# 4. EXPLAINABILITY & DYNAMIC REASONING ENGINE
# Generates personalized explanations based on ACTUAL student scores
# =============================================================

def get_dimension_level(score: int) -> str:
    """Returns qualitative rating for dimension scores."""
    if score >= 75:
        return "Strong"
    elif score >= 55:
        return "High"
    elif score >= 40:
        return "Moderate"
    else:
        return "Developing"


def generate_career_profile_summary(interest_scores: Dict[str, int]) -> Dict[str, Any]:
    """
    Generates structured trait summaries and personalized 'Things you may enjoy'
    derived from student's top scoring dimensions.
    """
    # Trait ratings
    traits = [
        {"name": "Analytical Thinking & Logic", "score": interest_scores.get("analytical", 50), "level": get_dimension_level(interest_scores.get("analytical", 50))},
        {"name": "Algorithmic & Problem Solving", "score": interest_scores.get("computing", 50), "level": get_dimension_level(interest_scores.get("computing", 50))},
        {"name": "Hardware & Electronics Interest", "score": interest_scores.get("electronics", 50), "level": get_dimension_level(interest_scores.get("electronics", 50))},
        {"name": "Mechanical & Systems Thinking", "score": interest_scores.get("mechanical", 50), "level": get_dimension_level(interest_scores.get("mechanical", 50))},
        {"name": "Design & Visual Creativity", "score": interest_scores.get("design", 50), "level": get_dimension_level(interest_scores.get("design", 50))},
        {"name": "Hands-on & Practical Building", "score": interest_scores.get("practical", 50), "level": get_dimension_level(interest_scores.get("practical", 50))},
        {"name": "Scientific Inquiry & Research", "score": interest_scores.get("research", 50), "level": get_dimension_level(interest_scores.get("research", 50))},
        {"name": "Infrastructure & Environment", "score": interest_scores.get("civil", 50), "level": get_dimension_level(interest_scores.get("civil", 50))},
        {"name": "Chemical & Life Sciences", "score": interest_scores.get("chemical_bio", 50), "level": get_dimension_level(interest_scores.get("chemical_bio", 50))},
    ]

    # Dynamic Things You May Enjoy
    activities_map = {
        "computing": [
            "Deconstructing complex problems into step-by-step logical algorithms",
            "Building software tools, web apps, or automating repetitive tasks"
        ],
        "analytical": [
            "Solving quantitative puzzles and finding structured patterns in data",
            "Making reasoned decisions using facts, charts, and logical deductions"
        ],
        "electronics": [
            "Tinkering with electronic circuits, smart sensors, and microcontrollers",
            "Understanding wireless communications, robotics, and smart automation"
        ],
        "mechanical": [
            "Exploring moving mechanisms, vehicle engines, gears, and machinery",
            "Assembling physical prototypes and 3D modeling functional parts"
        ],
        "design": [
            "Creating clean visual layouts, interactive UI screens, and user aesthetics",
            "Synthesizing visual appeal with functional everyday usability"
        ],
        "practical": [
            "Hands-on experimental learning and building physical working projects",
            "Testing and troubleshooting how real-world devices function"
        ],
        "research": [
            "Investigating the scientific 'why' behind natural and technical phenomena",
            "Conducting in-depth project investigations to solve real-world challenges"
        ],
        "civil": [
            "Planning sustainable structures, smart city layouts, and transport networks",
            "Working on eco-friendly environmental solutions and sustainable materials"
        ],
        "chemical_bio": [
            "Analyzing chemical processes, laboratory experiments, and biotechnology",
            "Developing healthcare solutions, pharmaceuticals, and green materials"
        ]
    }

    # Sort dimensions by score descending
    sorted_dims = sorted(interest_scores.items(), key=lambda x: x[1], reverse=True)
    enjoy_list: List[str] = []
    
    # Pick from top dimensions (scores >= 50, or top 3)
    for dim, score in sorted_dims[:3]:
        if dim in activities_map:
            enjoy_list.extend(activities_map[dim])
            
    # Deduplicate and cap to 4-5 items
    unique_enjoy = []
    for item in enjoy_list:
        if item not in unique_enjoy:
            unique_enjoy.append(item)
    
    return {
        "traits": traits,
        "things_you_may_enjoy": unique_enjoy[:5]
    }


def generate_branch_explanation(
    branch: Dict[str, Any],
    interest_scores: Dict[str, int],
    maths: float,
    physics: float,
    chemistry: float,
    fit_percentage: int
) -> Dict[str, Any]:
    """
    Generates a personalized, transparent explanation strictly based on
    the student's ACTUAL scores, highlighting contributing strengths and nuances.
    """
    code = branch["branch_code"]
    p_weights = branch["primary_weights"]
    
    # Identify student's top scoring dimensions relevant to this branch
    relevant_dims = []
    for dim, weight in sorted(p_weights.items(), key=lambda x: x[1], reverse=True):
        score = interest_scores.get(dim, 50)
        level = get_dimension_level(score)
        dim_label = dim.replace("_", " ").title()
        relevant_dims.append({"dim": dim, "label": dim_label, "score": score, "level": level, "weight": weight})

    top_dim = relevant_dims[0]
    second_dim = relevant_dims[1] if len(relevant_dims) > 1 else relevant_dims[0]

    # Key strengths contributing to the score
    contributing_strengths = []
    for rd in relevant_dims:
        if rd["score"] >= 60:
            if rd["dim"] == "computing":
                contributing_strengths.append("Algorithmic & Systematic Thinking")
            elif rd["dim"] == "analytical":
                contributing_strengths.append("Quantitative & Logical Reasoning")
            elif rd["dim"] == "electronics":
                contributing_strengths.append("Hardware & Circuit Curiosity")
            elif rd["dim"] == "mechanical":
                contributing_strengths.append("Physical Machinery & Mechanical Aptitude")
            elif rd["dim"] == "practical":
                contributing_strengths.append("Hands-on & Experimental Inclination")
            elif rd["dim"] == "design":
                contributing_strengths.append("Creative & Visual Design Thinking")
            elif rd["dim"] == "research":
                contributing_strengths.append("Scientific Curiosity & Analytical Inquiry")
            elif rd["dim"] == "civil":
                contributing_strengths.append("Structural Planning & Sustainability Interest")
            elif rd["dim"] == "chemical_bio":
                contributing_strengths.append("Chemical & Life Sciences Affinity")

    # Subject mark signals
    if maths >= 80:
        contributing_strengths.append("Strong Mathematics Foundation")
    if physics >= 80 and ("physics" in branch["subject_weights"] and branch["subject_weights"]["physics"] >= 0.35):
        contributing_strengths.append("Strong Physics Foundation")
    if chemistry >= 80 and ("chemistry" in branch["subject_weights"] and branch["subject_weights"]["chemistry"] >= 0.35):
        contributing_strengths.append("Strong Chemistry Foundation")

    if not contributing_strengths:
        contributing_strengths = ["Balanced General Aptitude", "Adaptable Learning Curiosity"]

    # Deduplicate and keep top 3-4 strengths
    contributing_strengths = list(dict.fromkeys(contributing_strengths))[:4]

    # Dynamic explanation generation reflecting nuances & mixed profiles
    explanation_parts = []
    
    comp_score = interest_scores.get("computing", 50)
    anal_score = interest_scores.get("analytical", 50)
    elec_score = interest_scores.get("electronics", 50)
    mech_score = interest_scores.get("mechanical", 50)
    des_score = interest_scores.get("design", 50)
    prac_score = interest_scores.get("practical", 50)
    res_score = interest_scores.get("research", 50)
    civ_score = interest_scores.get("civil", 50)
    chem_score = interest_scores.get("chemical_bio", 50)

    # Contextual tailoring by branch code and student's profile
    if code in ["CS", "IT"]:
        if comp_score >= 70 and anal_score >= 70:
            explanation_parts.append(
                f"Your assessment reflects high interest in step-by-step logic ({comp_score}%) and analytical problem solving ({anal_score}%). "
                "These characteristics align strongly with software development and computational algorithms."
            )
        elif anal_score >= 75 and comp_score < 60:
            explanation_parts.append(
                f"Your profile exhibits strong quantitative and logical thinking ({anal_score}%) with moderate computing affinity ({comp_score}%). "
                f"{branch['branch_name']} is worth exploring for its structured logic, though analytical data tracks or hardware branches could also be considered."
            )
        elif comp_score >= 70:
            explanation_parts.append(
                f"Your high affinity for digital technologies and systematic problem solving ({comp_score}%) provides a natural starting point for {branch['branch_name']}."
            )
        else:
            explanation_parts.append(
                f"Your balanced profile indicates moderate compatibility ({fit_percentage}%) with software systems. "
                "Explore introductory programming concepts to evaluate your practical enjoyment of code."
            )

    elif code in ["AD", "AL"]:
        if anal_score >= 70 and maths >= 75:
            explanation_parts.append(
                f"Your strong mathematical foundation ({maths}/100) paired with high analytical thinking ({anal_score}%) aligns exceptionally well with statistical modeling and intelligent data systems."
            )
        elif comp_score >= 70 and anal_score < 65:
            explanation_parts.append(
                f"Your interest in digital software ({comp_score}%) connects well with AI applications, though building a stronger foundation in statistics and probability will further enhance your journey."
            )
        else:
            explanation_parts.append(
                f"Your responses demonstrate curiosity for automated intelligence ({fit_percentage}% Interest Fit). This emerging branch combines computer science with mathematical data analysis."
            )

    elif code == "CY":
        if anal_score >= 70 and comp_score >= 60:
            explanation_parts.append(
                f"Your affinity for strategic thinking ({anal_score}%) and computer systems ({comp_score}%) aligns naturally with digital network defense and security protocols."
            )
        else:
            explanation_parts.append(
                f"Your analytical profile indicates good alignment ({fit_percentage}%) with cyber defense, where structured investigations and rule-based system security are essential."
            )

    elif code == "CD":
        if des_score >= 65 and comp_score >= 60:
            explanation_parts.append(
                f"Your dual interest in visual design ({des_score}%) and computing tools ({comp_score}%) makes you an ideal candidate for human-computer interaction and user experience software design."
            )
        else:
            explanation_parts.append(
                f"Your creative curiosity and digital orientation ({fit_percentage}% Interest Fit) align well with modern software product design and interactive frontends."
            )

    elif code in ["EC", "EV"]:
        if elec_score >= 70 and physics >= 70:
            explanation_parts.append(
                f"Your strong interest in electronic gadgets and circuitry ({elec_score}%), backed by solid physics understanding ({physics}/100), strongly supports studies in microchips and communication networks."
            )
        elif anal_score >= 70 and elec_score >= 60:
            explanation_parts.append(
                f"Your profile combines analytical reasoning ({anal_score}%) with hardware curiosity ({elec_score}%), bridging the gap between signal hardware and embedded microcontrollers."
            )
        else:
            explanation_parts.append(
                f"Your assessment responses indicate potential alignment ({fit_percentage}%) with electronics and communication, where physical circuits meet digital signal processing."
            )

    elif code == "EE":
        if (elec_score >= 65 or mech_score >= 65) and physics >= 70:
            explanation_parts.append(
                f"Your curiosity regarding electrical circuits and power mechanisms, supported by physics marks ({physics}/100), offers a strong foundation for electric vehicles and renewable grid engineering."
            )
        else:
            explanation_parts.append(
                f"Your practical and hardware inclinations ({fit_percentage}% Interest Fit) align with power systems, electric machinery, and automation."
            )

    elif code == "EI":
        if elec_score >= 60 and prac_score >= 60:
            explanation_parts.append(
                f"Your practical hands-on mindset ({prac_score}%) and electronic curiosity ({elec_score}%) match well with industrial sensor technologies and automated instrumentation."
            )
        else:
            explanation_parts.append(
                f"Your responses demonstrate good alignment ({fit_percentage}%) with sensor design and industrial process automation across modern manufacturing."
            )

    elif code in ["ME", "AU"]:
        if mech_score >= 70 and prac_score >= 65:
            explanation_parts.append(
                f"Your keen interest in moving machines and physical mechanisms ({mech_score}%), paired with hands-on experimentation ({prac_score}%), matches the core curriculum of {branch['branch_name']}."
            )
        elif mech_score >= 65 and physics >= 70:
            explanation_parts.append(
                f"Your enthusiasm for physical systems and solid physics foundation ({physics}/100) provides a sound base for mechanical thermodynamics and machine design."
            )
        else:
            explanation_parts.append(
                f"Your profile shows moderate compatibility ({fit_percentage}%) with mechanical engineering. Hands-on modeling and CAD experimentation are recommended to explore this field further."
            )

    elif code in ["MC", "RA"]:
        if (mech_score >= 60 and elec_score >= 60) or (comp_score >= 60 and mech_score >= 60):
            explanation_parts.append(
                f"Your versatile curiosity spanning machines ({mech_score}%), circuits ({elec_score}%), and software ({comp_score}%) makes you exceptionally well-suited for interdisciplinary robotics and mechatronics."
            )
        else:
            explanation_parts.append(
                f"Your cross-disciplinary interests ({fit_percentage}% Interest Fit) align with modern smart automation, where mechanical parts are guided by software intelligence."
            )

    elif code in ["CE", "EN"]:
        if civ_score >= 65:
            explanation_parts.append(
                f"Your keen awareness of buildings, structural infrastructure, and sustainability ({civ_score}%) creates a clear connection to {branch['branch_name']}."
            )
        else:
            explanation_parts.append(
                f"Your assessment responses indicate interest ({fit_percentage}%) in public infrastructure, sustainable planning, and structural analysis."
            )

    elif code in ["BT", "BM", "CH"]:
        if chem_score >= 65 or res_score >= 65:
            explanation_parts.append(
                f"Your curiosity regarding chemical transformations and scientific investigation ({chem_score}%) provides a strong base for laboratory research and process engineering."
            )
        else:
            explanation_parts.append(
                f"Your profile shows potential alignment ({fit_percentage}%) with life science technologies and industrial process design."
            )

    elif code == "DA":
        if des_score >= 65:
            explanation_parts.append(
                f"Your strong appreciation for visual balance, user ergonomics, and layout design ({des_score}%) directly powers product styling and functional industrial design."
            )
        else:
            explanation_parts.append(
                f"Your creative and visual tendencies ({fit_percentage}% Interest Fit) align with human-centered product and industrial design."
            )

    else:
        explanation_parts.append(
            f"Your assessment responses show {get_dimension_level(top_dim['score']).lower()} alignment with {top_dim['label']} ({top_dim['score']}%), indicating solid suitability for {branch['branch_name']}."
        )

    # If student's profile is mixed/balanced across branches, add an insightful note
    dim_scores = [interest_scores.get(k, 50) for k in ["computing", "electronics", "mechanical", "analytical"]]
    if max(dim_scores) - min(dim_scores) <= 15:
        explanation_parts.append(
            "Note: Your assessment reveals balanced interests across both computational and physical engineering domains. Exploring interdisciplinary tracks (such as Mechatronics, AI, or ECE) can help you utilize multiple strengths."
        )

    full_explanation = " ".join(explanation_parts)

    return {
        "explanation": full_explanation,
        "contributing_strengths": contributing_strengths,
        "explore_topics": branch.get("explore_topics", []),
        "alternative_reason": branch.get("alternative_reason", "")
    }


# =============================================================
# 5. BRANCH FIT EVALUATION ENGINE
# Normalizes scores to 0-100 range and assigns alignment levels
# =============================================================

def evaluate_branch_fits(
    interest_scores: Dict[str, int],
    maths: float,
    physics: float,
    chemistry: float
) -> Dict[str, Any]:
    """
    Calculates transparent Interest Fit score (0-100%) for all candidate engineering branches.
    Separates Interest Fit from admission cutoff probability.
    Returns:
      - top_recommendations: Top 3-5 strongest matches
      - alternative_options: Next 2-3 branches worth exploring
      - all_branches: Complete evaluated catalog
    """
    m_norm = max(0.0, min(100.0, float(maths)))
    p_norm = max(0.0, min(100.0, float(physics)))
    c_norm = max(0.0, min(100.0, float(chemistry)))

    evaluated = []

    for branch in BRANCH_PROFILES:
        # 1. Interest Match Component (70% weight)
        interest_match = 0.0
        for dim, weight in branch["primary_weights"].items():
            dim_score = interest_scores.get(dim, 50)
            interest_match += dim_score * weight

        # 2. Subject Affinity Component (30% weight)
        sub_w = branch["subject_weights"]
        subject_match = (
            (m_norm * sub_w.get("maths", 0.33)) +
            (p_norm * sub_w.get("physics", 0.33)) +
            (c_norm * sub_w.get("chemistry", 0.33))
        )

        # Composite Interest-Fit score (0-100%)
        total_fit = (interest_match * 0.70) + (subject_match * 0.30)
        fit_percentage = int(round(total_fit))
        fit_percentage = max(10, min(98, fit_percentage))

        # Alignment Levels (Strictly Non-overconfident language)
        if fit_percentage >= 80:
            alignment_level = "Strong alignment"
            tier_badge = "success"
        elif fit_percentage >= 65:
            alignment_level = "Good alignment"
            tier_badge = "primary"
        elif fit_percentage >= 50:
            alignment_level = "Potential match"
            tier_badge = "info"
        else:
            alignment_level = "Consider exploring"
            tier_badge = "secondary"

        # Generate dynamic explanation
        exp_data = generate_branch_explanation(
            branch=branch,
            interest_scores=interest_scores,
            maths=m_norm,
            physics=p_norm,
            chemistry=c_norm,
            fit_percentage=fit_percentage
        )

        evaluated.append({
            "branch_code": branch["branch_code"],
            "branch_name": branch["branch_name"],
            "domain": branch["domain"],
            "fit_percentage": fit_percentage,
            "alignment_level": alignment_level,
            "tier_badge": tier_badge,
            "description": branch["description"],
            "why_fit": exp_data["explanation"],
            "contributing_strengths": exp_data["contributing_strengths"],
            "explore_topics": exp_data["explore_topics"],
            "alternative_reason": exp_data["alternative_reason"],
            "core_focus": branch.get("core_focus", [])
        })

    # Sort descending by fit percentage
    evaluated.sort(key=lambda x: x["fit_percentage"], reverse=True)

    # Top recommendations: top 4 (or up to 5 if scores are high/close)
    top_recs = evaluated[:4]
    
    # Alternative options: next 2-3 branches with distinct domain perspectives
    alternatives = evaluated[4:7]

    return {
        "top_recommendations": top_recs,
        "alternative_options": alternatives,
        "all_branches": evaluated
    }


# =============================================================
# 6. ORCHESTRATION FUNCTION
# =============================================================

def process_full_assessment(form_data: dict) -> dict:
    """
    Main orchestration function: processes raw form submission,
    computes dimensions, subject strengths, branch fits, and explanations.
    """
    try:
        maths = float(form_data.get("maths_marks", 0))
    except (ValueError, TypeError):
        maths = 0.0

    try:
        physics = float(form_data.get("physics_marks", 0))
    except (ValueError, TypeError):
        physics = 0.0

    try:
        chemistry = float(form_data.get("chemistry_marks", 0))
    except (ValueError, TypeError):
        chemistry = 0.0

    cs_bio_raw = form_data.get("cs_bio_marks")
    cs_bio = None
    if cs_bio_raw is not None and str(cs_bio_raw).strip() != "":
        try:
            cs_bio = float(cs_bio_raw)
        except (ValueError, TypeError):
            cs_bio = None

    cutoff = calculate_tnea_cutoff(maths, physics, chemistry)
    subject_strengths = compute_subject_strengths(maths, physics, chemistry, cs_bio)

    # Extract question answers
    answers = {}
    for q in ASSESSMENT_QUESTIONS:
        qid = q["id"]
        val = form_data.get(qid)
        if val is not None:
            try:
                answers[qid] = int(val)
            except (ValueError, TypeError):
                answers[qid] = 3
        else:
            answers[qid] = 3

    interest_scores = compute_interest_dimensions(answers)
    branch_fit_result = evaluate_branch_fits(interest_scores, maths, physics, chemistry)
    profile_summary = generate_career_profile_summary(interest_scores)

    # For backward compatibility with database top_branches field,
    # top_branches is stored as the full sorted evaluated list or top recommendations.
    # We will include all branches in top_branches list so any legacy view or template works cleanly.
    return {
        "maths_marks": maths,
        "physics_marks": physics,
        "chemistry_marks": chemistry,
        "cs_bio_marks": cs_bio,
        "cutoff": cutoff,
        "community": form_data.get("community", "OC"),
        "preferred_district": form_data.get("preferred_district", "").strip(),
        "school_stream": form_data.get("school_stream", "General Science"),
        "assessment_answers": answers,
        "interest_scores": interest_scores,
        "top_branches": branch_fit_result["all_branches"],
        "top_recommendations": branch_fit_result["top_recommendations"],
        "alternative_options": branch_fit_result["alternative_options"],
        "subject_strengths": subject_strengths,
        "career_profile_summary": profile_summary
    }
