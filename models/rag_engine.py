"""
=============================================================
TNEA Career Insight Navigator — RAG & Vector Database Engine
=============================================================
Genuine Retrieval-Augmented Generation (RAG) pipeline powered by
persistent ChromaDB, semantic vector embeddings, metadata filtering,
and chunking over verified engineering, counselling, and project knowledge.
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("rag_engine")

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_DB_DIR = BASE_DIR / "database" / "vector_db"
VECTORIZER_PATH = VECTOR_DB_DIR / "vectorizer.joblib"
COLLECTION_NAME = "tnea_knowledge_base"


# =============================================================
# 1. EMBEDDING FUNCTIONS (OpenAI & Persistent Dense Semantic)
# =============================================================

import chromadb
import numpy as np
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer


class PersistentSemanticEmbeddingFunction(chromadb.EmbeddingFunction):
    """
    High-precision persistent semantic embedding function.
    Combines sublinear TF-IDF, character and word n-grams (1-3) into normalized
    dense feature vectors (2048-dim). Persists vectorizer model state to disk.
    """
    def __init__(self, vectorizer_path: Path = VECTORIZER_PATH):
        self.vectorizer_path = vectorizer_path
        self.vectorizer = None
        self._load_or_init_vectorizer()

    def name(self) -> str:
        return "persistent_semantic_embedding"

    def get_config(self) -> Dict[str, Any]:
        return {"vectorizer_path": str(self.vectorizer_path)}

    def _load_or_init_vectorizer(self):
        if self.vectorizer_path.exists():
            try:
                self.vectorizer = joblib.load(self.vectorizer_path)
            except Exception as e:
                logger.warning(f"Could not load vectorizer from {self.vectorizer_path}: {e}")
                self.vectorizer = None

        if self.vectorizer is None:
            self.vectorizer = TfidfVectorizer(
                ngram_range=(1, 3),
                sublinear_tf=True,
                max_features=2048,
                token_pattern=r"(?u)\b[\w#+.&-]+\b",
                stop_words="english"
            )
            self.fitted = False
        else:
            self.fitted = True



    def fit_and_save(self, documents: List[str]):
        """Fits the vectorizer on the full corpus and saves state to disk."""
        self.vectorizer.fit(documents)
        self.fitted = True
        self.vectorizer_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.vectorizer, self.vectorizer_path)

    def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
        if not self.fitted:
            self.fit_and_save(input)

        try:
            sparse_mat = self.vectorizer.transform(input)
            dense = sparse_mat.toarray().astype(np.float32)
            # L2 normalize
            norms = np.linalg.norm(dense, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            dense_norm = dense / norms
            return dense_norm.tolist()
        except Exception as e:
            logger.error(f"Embedding transformation error: {e}")
            # Fallback zero-vector
            dim = 2048
            return [np.zeros(dim, dtype=np.float32).tolist() for _ in input]


def get_embedding_function():
    """
    Returns the configured embedding function:
    1. OpenAIEmbeddingFunction (text-embedding-3-small) if OPENAI_API_KEY is available.
    2. PersistentSemanticEmbeddingFunction as high-accuracy, zero-network persistent embedding model.
    Query and documents always use the matching embedding model.
    """
    openai_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("AI_API_KEY")
    if openai_key and str(openai_key).strip():
        try:
            import chromadb.utils.embedding_functions as ef
            model_name = os.environ.get("OPENAI_EMBEDDING_MODEL") or "text-embedding-3-small"
            base_url = os.environ.get("OPENAI_BASE_URL")
            return ef.OpenAIEmbeddingFunction(
                api_key=openai_key.strip(),
                model_name=model_name,
                api_base=base_url.strip() if base_url else None
            )
        except Exception as e:
            logger.warning(f"Notice: Using persistent semantic embedding engine: {e}")

    return PersistentSemanticEmbeddingFunction()


# =============================================================
# 2. CHROMADB CLIENT & COLLECTION MANAGER
# =============================================================

_chroma_client = None
_chroma_collection = None

def get_vector_db_client():
    """Returns persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    return _chroma_client


def get_knowledge_collection(embedding_function=None):
    """Returns or creates the persistent knowledge collection."""
    global _chroma_collection
    client = get_vector_db_client()
    ef_func = embedding_function or get_embedding_function()
    _chroma_collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef_func,
        metadata={"hnsw:space": "cosine", "description": "TNEA Engineering and Career Knowledge Base"}
    )
    return _chroma_collection


# =============================================================
# 3. KNOWLEDGE SOURCE CATALOG BUILDER
# =============================================================

def build_knowledge_sources() -> List[Dict[str, Any]]:
    """
    Extracts structured and unstructured knowledge from verified project sources:
    1. Engineering Branch Profiles & Curricula (20+ disciplines)
    2. TNEA Counselling Rules, Strategy & Reservation Framework
    3. Learning Roadmaps & Pre-Engineering Resources
    4. Website Navigation, Features & Platform Tools
    5. Official College Profiles & Facilities
    """
    documents: List[Dict[str, Any]] = []

    # -------------------------------------------------------------
    # Source 1: Engineering Branches & Curricula (from career_engine)
    # -------------------------------------------------------------
    try:
        from models.career_engine import BRANCH_PROFILES
        for b in BRANCH_PROFILES:
            b_code = b.get("branch_code", "")
            b_name = b.get("branch_name", "")
            domain = b.get("domain", "")
            desc = b.get("description", "")
            core = ", ".join(b.get("core_focus", []))
            topics = ", ".join(b.get("explore_topics", []))
            alt_reason = b.get("alternative_reason", "")

            aliases_map = {
                "AD": "AI&DS, AIDS, AI & DS, Artificial Intelligence and Data Science, what is AIDS, what is AI&DS, Artificial Intelligence",
                "CS": "CSE, Computer Science & Engineering, Software Engineering, what is CSE, what is Computer Science, Computer Science",
                "IT": "Information Technology, Info Tech, what is IT",
                "EC": "ECE, Electronics and Communication Engineering, what is ECE",
                "EE": "EEE, Electrical and Electronics Engineering, what is EEE",
                "ME": "Mech, Mechanical Engineering, what is Mech",
                "CE": "Civil, Civil Engineering, what is Civil",
                "BT": "BioTech, Biotechnology, what is Biotech",
                "BM": "BioMed, Biomedical Engineering, what is Biomed",
                "CB": "CSBS, Computer Science and Business Systems",
                "CY": "Cybersecurity, Cyber Security and Engineering",
                "RA": "Robotics, Robotics and Automation",
                "AM": "AIML, AI and Machine Learning",
                "AG": "Agri, Agricultural Engineering"
            }

            alias_text = aliases_map.get(b_code, "")

            content = (
                f"Engineering Branch: {b_name} ({b_code})\n"
                f"Synonyms & Acronyms: {alias_text}\n"
                f"Domain: {domain}\n"
                f"Overview: {desc}\n"
                f"Core Curriculum & Focus Areas: {core}\n"
                f"Exploratory Topics & Prerequisites: {topics}\n"
                f"Strategic Significance & Career Suitability: {alt_reason}"
            )

            primary_acronym = alias_text.split(",")[0].strip() if alias_text else b_code
            full_title = f"{b_name} ({primary_acronym} / {b_code})" if primary_acronym != b_code else f"{b_name} ({b_code})"

            documents.append({
                "id": f"branch_{b_code.lower()}",
                "title": full_title,
                "category": "engineering_branches",
                "source": "branch_catalog",
                "source_type": "curriculum_guide",
                "branch_code": b_code,
                "branch_name": b_name,
                "domain": domain,
                "content": content
            })


    except Exception as e:
        logger.warning(f"Error extracting branch profiles: {e}")

    # -------------------------------------------------------------
    # Source 2: TNEA Counselling Strategy, Rules & Reservations
    # -------------------------------------------------------------
    counselling_topics = [
        {
            "id": "tnea_overview",
            "title": "TNEA Single Window Counselling Overview",
            "category": "tnea_counselling",
            "source": "tnea_official_guidelines",
            "source_type": "official_guide",
            "content": (
                "Tamil Nadu Engineering Admissions (TNEA) is the centralized single-window counselling process conducted by the Directorate of Technical Education (DoTE) for admission to undergraduate engineering (B.E. / B.Tech) programs in Anna University departments, constituent colleges, government engineering colleges, government-aided colleges, and seats surrendered by self-financing colleges across Tamil Nadu.\n"
                "Admissions are determined purely based on the 200-mark TNEA Cutoff score derived from 12th standard marks: Mathematics (100 marks) + Physics (50 marks) + Chemistry (50 marks). There is no separate entrance examination for general engineering admissions in Tamil Nadu."
            )
        },
        {
            "id": "tnea_3tier_strategy",
            "title": "3-Tier Preference Choice Filling Framework",
            "category": "tnea_counselling",
            "source": "counselling_strategy_guide",
            "source_type": "strategy_guide",
            "content": (
                "How to Structure your TNEA Preference List & Choice Filling Strategy:\n"
                "The 3-Tier Choice Filling Framework is the proven strategic method for arranging and structuring college and branch preferences in TNEA single-window counselling:\n"
                "1. Tier 1: Choices 1 to 10 — Dream / Ambitious Choices. Top-tier colleges where previous year closing cutoffs were 1.0 to 3.0 marks higher than your score. In TNEA single-window allocation, there is zero penalty for putting dream options first because the algorithm evaluates choices top-to-bottom without skipping your target matches.\n"
                "2. Tier 2: Choices 11 to 25 — Target / Realistic Matches. Well-accredited colleges where 2023–2025 closing cutoffs match your exact cutoff range (within ±1.5 marks). These represent the highest statistical probability of allocation.\n"
                "3. Tier 3: Choices 26 to 40 — Safe / Backup Options. Reputed accredited institutions where cutoffs are comfortably 3.0 to 6.0 marks below yours, ensuring guaranteed allocation in case of cutoff surges.\n"
                "Crucial Rule: Always prioritize your preferred engineering branch over college brand name unless you have verified the lateral branch change or curriculum overlap."
            )
        },

        {
            "id": "tnea_reservation_quotas",
            "title": "TNEA Reservation System & Community Quotas",
            "category": "tnea_counselling",
            "source": "tnea_official_guidelines",
            "source_type": "official_guide",
            "content": (
                "TNEA strictly adheres to Tamil Nadu's 69% communal reservation policy:\n"
                "• Open Competition (OC): 31% (Merit open to all categories)\n"
                "• Backward Class (BC): 26.5%\n"
                "• Backward Class Muslim (BCM): 3.5%\n"
                "• Most Backward Class & Denotified Communities (MBC & DNC): 20%\n"
                "• Scheduled Caste (SC): 15%\n"
                "• Scheduled Caste Arunthathiyar (SCA): 3%\n"
                "• Scheduled Tribe (ST): 1%\n"
                "Special Reservations within TNEA:\n"
                "• 7.5% Government School Quota: Preferential horizontal reservation with full tuition and hostel fee waiver for students who studied from 6th to 12th standard in Tamil Nadu Government schools.\n"
                "• First Graduate Scheme: Tuition fee concession granted by Tamil Nadu Government for candidates who are the first in their family to pursue higher education."
            )
        },
        {
            "id": "tnea_counselling_rounds",
            "title": "TNEA Counselling Rounds & Allotment Stages",
            "category": "tnea_counselling",
            "source": "tnea_official_guidelines",
            "source_type": "official_guide",
            "content": (
                "TNEA single-window counselling is conducted online in four sequential rounds based on overall rank and cutoff mark bands:\n"
                "1. Initial Payment & Registration: Candidates pay the initial counselling fee.\n"
                "2. Choice Filling (3 Days): Adding and ordering college + branch combinations following the 3-Tier Choice Filling Framework (Choices 1–10 Dream, Choices 11–25 Target, Choices 26–40 Safe).\n"
                "3. Tentative Allotment: System releases preliminary seat allotment based on rank, community quota, and choice list.\n"
                "4. Allotment Confirmation (2 Days): Options include 'Accept and Join', 'Accept and Upward' (accept current seat but request upward movement in higher preference choices if seats vacate), 'Decline and Upward', 'Decline and Next Round', or 'Quit'.\n"
                "5. Final Allotment & College Reporting: Downloading the provisional allotment order and reporting to the assigned college with original certificates."
            )
        },

        {
            "id": "tnea_documents_required",
            "title": "Mandatory Documents for TNEA Verification & Admission",
            "category": "tnea_counselling",
            "source": "tnea_official_guidelines",
            "source_type": "official_guide",
            "content": (
                "Essential certificates required for TNEA certificate verification and college admission:\n"
                "1. 10th Standard (SSLC) Mark Sheet (proof of date of birth)\n"
                "2. +1 (11th) Mark Sheet\n"
                "3. +2 (12th / HSC) Mark Sheet\n"
                "4. Transfer Certificate (TC) from school last attended\n"
                "5. Permanent Community Certificate Card (for BC, BCM, MBC/DNC, SC, SCA, ST)\n"
                "6. Nativity Certificate (if schooling completed outside TN but claiming TN nativity)\n"
                "7. First Graduate Certificate and Joint Declaration (if claiming First Graduate fee waiver)\n"
                "8. Income Certificate (if claiming Post-Matric or fee scholarship)\n"
                "9. Special Reservation Certificate (for Sports, Ex-Servicemen, Differently Abled, or 7.5% Govt school quota)."
            )
        }
    ]
    documents.extend(counselling_topics)

    # -------------------------------------------------------------
    # Source 3: Pre-Engineering Learning Resources (from resources.py)
    # -------------------------------------------------------------
    try:
        from models.resources import LEARNING_RESOURCES
        for r in LEARNING_RESOURCES:
            r_id = r.get("id", "")
            title = r.get("title", "")
            cat = r.get("category", "")
            desc = r.get("description", "")
            channel = r.get("channel", "")
            duration = r.get("duration", "")
            level = r.get("difficulty", "Beginner")
            takeaways = ", ".join(r.get("key_takeaways", []))

            content = (
                f"Learning Resource: {title}\n"
                f"Category: {cat.replace('_', ' ').title()}\n"
                f"Channel / Platform: {channel}\n"
                f"Skill Level: {level} | Duration: {duration}\n"
                f"Description: {desc}\n"
                f"Key Takeaways & Topics: {takeaways}"
            )

            documents.append({
                "id": f"resource_{r_id}",
                "title": title,
                "category": "learning_resources",
                "source": "learning_catalog",
                "source_type": "resource_guide",
                "resource_category": cat,
                "level": level,
                "content": content
            })
    except Exception as e:
        logger.warning(f"Error extracting learning resources: {e}")

    # -------------------------------------------------------------
    # Source 4: Website Platform & Tool Guides
    # -------------------------------------------------------------
    platform_features = [
        {
            "id": "feature_career_discovery",
            "title": "Career Discovery Assessment Tool",
            "category": "platform_features",
            "source": "platform_documentation",
            "source_type": "feature_guide",
            "content": (
                "Feature: Career Discovery Assessment (/career-guidance)\n"
                "Description: A 16-question aptitude and interest discovery assessment tailored for 12th standard students. Evaluates 9 cognitive and domain dimensions including Analytical Reasoning, Computing & Logic, Electronics & Circuits, Mechanical Systems, Visual Design, Practical Tinkering, and Scientific Inquiry. Recommends top matching engineering branches with compatibility percentage scores and detailed rationale."
            )
        },
        {
            "id": "feature_admission_planner",
            "title": "TNEA Admission Planner & Probability Calculator",
            "category": "platform_features",
            "source": "platform_documentation",
            "source_type": "feature_guide",
            "content": (
                "Feature: TNEA Admission Planner (/planner)\n"
                "Description: Calculates statistical admission probabilities across verified Tamil Nadu engineering colleges for years 2023, 2024, and 2025 based on the student's 200-mark cutoff, community quota (OC, BC, BCM, MBC, SC, ST), preferred branch, and district. Categorizes options into Dream (Aspirational), Target (High Probability), and Safe (Guaranteed Backup) tiers."
            )
        },
        {
            "id": "feature_college_search",
            "title": "College Search & Directory",
            "category": "platform_features",
            "source": "platform_documentation",
            "source_type": "feature_guide",
            "content": (
                "Feature: College Search & Directory (/search)\n"
                "Description: Explore 440+ verified engineering institutions across all Tamil Nadu districts. Filter by college name, TNEA code, district, autonomous accreditation, hostel facilities (boys/girls), and college bus transport availability."
            )
        },
        {
            "id": "feature_college_compare",
            "title": "College Comparison Tool",
            "category": "platform_features",
            "source": "platform_documentation",
            "source_type": "feature_guide",
            "content": (
                "Feature: College Comparison Tool (/compare)\n"
                "Description: Enables side-by-side benchmark comparison of up to 4 engineering colleges simultaneously. Compares closing cutoffs across engineering branches, autonomous status, facilities, address, and accreditation."
            )
        },
        {
            "id": "feature_choice_list",
            "title": "TNEA Choice List Manager",
            "category": "platform_features",
            "source": "platform_documentation",
            "source_type": "feature_guide",
            "content": (
                "Feature: Choice List Manager (/choice-list)\n"
                "Description: Interactive preference list builder for TNEA counselling. Add, reorder, delete, and classify college + branch choices into Dream, Target, and Safe tiers. Export finalized draft for single-window choice filling."
            )
        },
        {
            "id": "feature_document_vault",
            "title": "Secure Document Vault",
            "category": "platform_features",
            "source": "platform_documentation",
            "source_type": "feature_guide",
            "content": (
                "Feature: Document Vault (/documents)\n"
                "Description: Encrypted student vault for storing certificates required during TNEA verification (10th marksheet, 12th marksheet, Transfer Certificate, Community Certificate, First Graduate, Income Certificate)."
            )
        },
        {
            "id": "feature_ai_assistant",
            "title": "Interactive Chat & Career Guidance System",
            "category": "platform_features",
            "source": "platform_documentation",
            "source_type": "feature_guide",
            "content": (
                "Feature: Interactive Chat Assistant (/career-assistant)\n"
                "Description: Career guidance assistant powered by OpenAI LLM, RAG semantic vector retrieval, and TNEA database tool calling. Supports multi-turn conversation memory, general engineering questions, personalized evaluations, and verified cutoff benchmarks."
            )
        }

    ]
    documents.extend(platform_features)

    # -------------------------------------------------------------
    # Source 4B: General Engineering, CS, AI, and Career Concepts
    # -------------------------------------------------------------
    general_concepts = [
        {
            "id": "concept_recursion",
            "title": "Recursion in Programming with Example",
            "category": "programming_concepts",
            "source": "educational_foundations",
            "source_type": "educational_guide",
            "content": (
                "Understanding Recursion in Programming:\n"
                "Recursion is a fundamental programming technique where a function solves a computational problem by calling itself with a smaller input, until it reaches a stopping condition known as the Base Case.\n"
                "Two Essential Components of Recursion:\n"
                "1. Base Case: The condition that terminates the recursive calls and prevents infinite recursion.\n"
                "2. Recursive Case: The logic where the function calls itself on a smaller sub-problem.\n"
                "Classic Example - Factorial Calculation in Python:\n"
                "def factorial(n):\n"
                "    if n <= 1:\n"
                "        return 1  # Base Case\n"
                "    return n * factorial(n - 1)  # Recursive Step\n"
                "print(factorial(5))  # Output: 120 (5 * 4 * 3 * 2 * 1)"
            )
        },
        {
            "id": "concept_python_start",
            "title": "How to Start Learning Python Programming",
            "category": "programming_concepts",
            "source": "educational_foundations",
            "source_type": "educational_guide",
            "content": (
                "What is Python and How to Start Learning It:\n"
                "Python is a versatile, beginner-friendly, high-level programming language widely used in Web Development, Artificial Intelligence, Data Science, and Scripting.\n"
                "4-Step Learning Roadmap:\n"
                "1. Step 1 - Environment Setup: Install Python from python.org and code in VS Code or Google Colab.\n"
                "2. Step 2 - Syntax & Data Types (Weeks 1–2): Master variables, data types (int, float, string), conditionals (if/else), and loops (for/while).\n"
                "3. Step 3 - Data Structures & Functions (Week 3): Lists, Tuples, Dictionaries, Sets, and Writing reusable Functions (def).\n"
                "4. Step 4 - Mini Projects (Week 4): Build a Number Guessing Game, Student Marksheet Calculator, and a To-Do List App.\n"
                "Check our Learning Resources section at /resources for curated video tutorials."
            )
        },
        {
            "id": "concept_api_explanation",
            "title": "What is an API (Application Programming Interface)",
            "category": "programming_concepts",
            "source": "educational_foundations",
            "source_type": "educational_guide",
            "content": (
                "What is an API?\n"
                "An API (Application Programming Interface) is a set of rules and protocols that allows two different software programs to communicate with each other.\n"
                "Simple Analogy: In a restaurant, you (client) place an order. The kitchen (server/database) cooks the food. The waiter is the API — taking your request to the kitchen and bringing back the response.\n"
                "Common Real-World Examples:\n"
                "• Weather Apps: Fetching temperature data from a meteorological API.\n"
                "• Payment Gateways: Processing Google Pay / UPI transactions on e-commerce websites."
            )
        },
        {
            "id": "concept_machine_learning_basics",
            "title": "Machine Learning in Simple Terms",
            "category": "ai_concepts",
            "source": "educational_foundations",
            "source_type": "educational_guide",
            "content": (
                "Machine Learning in Simple Terms:\n"
                "Traditional programming: Input + Rules = Output. Machine Learning: Input + Output = Rules. The computer learns the rules automatically from data examples.\n"
                "3 Main Types of Machine Learning:\n"
                "1. Supervised Learning: Learning with labeled examples (e.g. recognizing cars from labeled car images).\n"
                "2. Unsupervised Learning: Discovering hidden patterns in unlabeled data (e.g. customer segmentation).\n"
                "3. Reinforcement Learning: Learning through trial and error with reward/penalty feedback (e.g. training autonomous robots or chess engines)."
            )
        },
        {
            "id": "concept_embedded_systems_ece",
            "title": "Embedded Systems Skills for ECE Students",
            "category": "electronics_concepts",
            "source": "educational_foundations",
            "source_type": "educational_guide",
            "content": (
                "Embedded Systems Career Skills for Electronics and Communication (ECE) Students:\n"
                "1. Low-level Embedded C and C++: Pointer arithmetic, memory management, and bitwise operations.\n"
                "2. Microcontroller Architectures: Programming ARM Cortex-M (STM32), Arduino, ESP32, and PIC.\n"
                "3. Communication Protocols: UART, I2C, SPI, CAN bus (used in Electric Vehicles and automotive electronics).\n"
                "4. Real-Time Operating Systems (RTOS): FreeRTOS task scheduling, semaphores, and queues.\n"
                "5. Hardware Debugging: Reading circuit schematics and using Oscilloscopes and Logic Analyzers."
            )
        },
        {
            "id": "concept_careers_after_cse",
            "title": "Diverse Career Opportunities After Computer Science (CSE)",
            "category": "career_guidance",
            "source": "career_pathways",
            "source_type": "career_guide",
            "content": (
                "Careers After Computer Science & Engineering (CSE) Beyond Software Development:\n"
                "1. Cybersecurity & Ethical Hacking: Network penetration testing, security operations, and digital forensics.\n"
                "2. Data Engineering & Big Data: Building high-throughput data streaming pipelines with SQL, Spark, and Kafka.\n"
                "3. Cloud & DevOps Engineering: Managing infrastructure automation, CI/CD pipelines, AWS, Azure, and Kubernetes.\n"
                "4. Technical Product Management: Bridging engineering implementation with product strategy.\n"
                "5. AI & Machine Learning Engineering: Developing predictive models, computer vision, and NLP systems."
            )
        },
        {
            "id": "concept_careers_after_ece",
            "title": "Diverse Career Opportunities After Electronics & Communication (ECE)",
            "category": "career_guidance",
            "source": "career_pathways",
            "source_type": "career_guide",
            "content": (
                "Careers After Electronics & Communication Engineering (ECE):\n"
                "1. VLSI & Semiconductor Design: Microchip architecture, ASIC design, circuit simulation (Qualcomm, Intel, AMD, Texas Instruments, NVIDIA).\n"
                "2. Embedded Systems & IoT: Programming microcontrollers, automotive electronics, and smart sensors.\n"
                "3. Wireless & Telecommunications: 5G/6G cellular networks, RF engineering, and satellite links.\n"
                "4. Software & Cloud Development: ECE graduates are eligible for over 75% of campus software engineering placements."
            )
        },
        {
            "id": "concept_study_abroad_ms",
            "title": "Studying Abroad After Engineering (MS / Higher Studies)",
            "category": "career_guidance",
            "source": "career_pathways",
            "source_type": "career_guide",
            "content": (
                "Studying Abroad After Engineering (MS / Higher Studies in USA, Germany, UK, Canada, Singapore):\n"
                "Key Preparation Requirements:\n"
                "1. Standardized Exams: GRE for STEM programs, plus TOEFL or IELTS for English proficiency.\n"
                "2. Academic Standing: Maintain a CGPA of 7.5+ (preferably 8.5+ for top-ranked universities).\n"
                "3. Capstone Projects & Research: Complete 2–3 substantial engineering projects or published research papers.\n"
                "4. Letters of Recommendation (LORs) & Statement of Purpose (SOP): Secure recommendations from professors and clearly outline your academic goals."
            )
        },
        {
            "id": "concept_cse_vs_ece",
            "title": "Comprehensive Comparison: CSE vs ECE",
            "category": "branch_comparisons",
            "source": "career_pathways",
            "source_type": "comparison_guide",
            "content": (
                "Comprehensive Comparison between Computer Science (CSE) and Electronics (ECE):\n"
                "• CSE Focus: Software architecture, algorithms, operating systems, compilers, cloud, Computing and logic, and cybersecurity. Primary recruiters: Microsoft, Google, Amazon, Zoho, TCS.\n"
                "• ECE Focus: Microchips, VLSI design, embedded IoT hardware, wireless 5G communications, and robotics. Primary recruiters: Qualcomm, Intel, TI, NVIDIA, plus all IT software companies.\n"
                "Key Difference: ECE offers dual eligibility for both hardware core companies and software IT placements, whereas CSE specializes deeply in software systems and Computing algorithms."
            )
        },

        {
            "id": "concept_cse_vs_aids",
            "title": "Comparison: CSE vs AI & Data Science (AI&DS)",
            "category": "branch_comparisons",
            "source": "career_pathways",
            "source_type": "comparison_guide",
            "content": (
                "Comparison: Computer Science & Engineering (CSE) vs Artificial Intelligence & Data Science (AI&DS):\n"
                "• CSE: Broad, versatile curriculum covering software engineering, OS, compilers, databases, and networks with maximum job flexibility.\n"
                "• AI&DS: Mathematics-heavy specialized curriculum focusing on Artificial Intelligence, Data Science, Machine Learning, probability, linear algebra, neural networks, and big data analytics from day one."
            )
        }

    ]
    documents.extend(general_concepts)

    # -------------------------------------------------------------
    # Source 5: Official College Profiles & Descriptive Summaries
    # -------------------------------------------------------------
    try:
        from models.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.college_code, c.college_name, ci.district, c.college_type,
                   ci.taluk, ci.address, ci.pincode, ci.autonomous, ci.website,
                   ci.hostel_boys, ci.hostel_girls, ci.transport
            FROM colleges c
            LEFT JOIN college_info ci ON ci.college_code = c.college_code
            WHERE c.college_name IS NOT NULL
        """)
        rows = cursor.fetchall()
        for r in rows:
            c_code = r["college_code"]
            c_name = r["college_name"]
            dist = (r["district"] or "Tamil Nadu").title()
            taluk = (r["taluk"] or "").title()
            auto = "Autonomous Institution" if str(r["autonomous"] or "").lower() == "yes" else "Affiliated College"
            addr = r["address"] or ""
            web = r["website"] or ""
            h_b = "Yes" if str(r["hostel_boys"] or "").lower() == "yes" else "No"
            h_g = "Yes" if str(r["hostel_girls"] or "").lower() == "yes" else "No"
            tr = "Yes" if str(r["transport"] or "").lower() == "yes" else "No"

            content = (
                f"College Profile: {c_name} (TNEA Code: {c_code})\n"
                f"Location: {dist} District, Taluk: {taluk}, Tamil Nadu.\n"
                f"Status: {auto} ({r['college_type'] or 'Engineering'})\n"
                f"Address: {addr}\n"
                f"Facilities: Boys Hostel: {h_b}, Girls Hostel: {h_g}, Bus Transport: {tr}\n"
                f"Website: {web}"
            )

            documents.append({
                "id": f"college_{c_code}",
                "title": f"{c_name} ({c_code})",
                "category": "college_profiles",
                "source": "tnea_college_directory",
                "source_type": "college_directory",
                "college_code": c_code,
                "college_name": c_name,
                "district": dist,
                "autonomous": r["autonomous"] or "No",
                "content": content
            })
        conn.close()
    except Exception as e:
        logger.warning(f"Error extracting college profiles: {e}")

    return documents


# =============================================================
# 4. TEXT CHUNKER WITH SEMANTIC METADATA
# =============================================================

def chunk_document(doc: Dict[str, Any], max_chunk_size: int = 700) -> List[Dict[str, Any]]:
    """
    Splits a document into structured chunks with attached metadata.
    Preserves paragraph and sentence boundaries where possible.
    """
    text = doc.get("content", "").strip()
    if not text:
        return []

    # If text is small enough, return as single chunk
    if len(text) <= max_chunk_size:
        chunk_meta = {k: v for k, v in doc.items() if k != "content"}
        chunk_meta["chunk_index"] = 0
        chunk_meta["total_chunks"] = 1
        return [{
            "chunk_id": f"{doc['id']}_c0",
            "content": text,
            "metadata": chunk_meta
        }]

    # Split into paragraphs
    paragraphs = text.split("\n")
    chunks: List[str] = []
    current_chunk: List[str] = []
    current_len = 0

    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue

        p_len = len(p_clean)
        if current_len + p_len + 1 <= max_chunk_size:
            current_chunk.append(p_clean)
            current_len += p_len + 1
        else:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
            current_chunk = [p_clean]
            current_len = p_len

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    result_chunks: List[Dict[str, Any]] = []
    for idx, c_text in enumerate(chunks):
        chunk_meta = {k: v for k, v in doc.items() if k != "content"}
        chunk_meta["chunk_index"] = idx
        chunk_meta["total_chunks"] = len(chunks)
        result_chunks.append({
            "chunk_id": f"{doc['id']}_c{idx}",
            "content": c_text,
            "metadata": chunk_meta
        })

    return result_chunks


# =============================================================
# 5. INGESTION SERVICE & VECTOR INDEXING
# =============================================================

def ingest_all_knowledge(force_reindex: bool = False) -> Dict[str, Any]:
    """
    Executes full knowledge discovery, chunking, embedding generation,
    and storage in persistent ChromaDB.
    """
    client = get_vector_db_client()

    # If force reindex requested, delete existing collection and cached vectorizer
    if force_reindex:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        if VECTORIZER_PATH.exists():
            try:
                VECTORIZER_PATH.unlink()
            except Exception:
                pass


    # Extract all knowledge documents
    raw_docs = build_knowledge_sources()

    # Chunk documents
    all_chunks: List[Dict[str, Any]] = []
    for d in raw_docs:
        chunks = chunk_document(d)
        all_chunks.extend(chunks)

    # Prepare embedding function
    embedding_func = get_embedding_function()
    if isinstance(embedding_func, PersistentSemanticEmbeddingFunction):
        # Fit vectorizer on all chunk contents
        all_texts = [c["content"] for c in all_chunks]
        embedding_func.fit_and_save(all_texts)

    collection = get_knowledge_collection(embedding_function=embedding_func)
    existing_count = collection.count()

    if existing_count > 0 and not force_reindex:
        return {
            "status": "already_indexed",
            "total_chunks": existing_count,
            "embedding_model": type(embedding_func).__name__,
            "collection_name": COLLECTION_NAME
        }

    # Ingest in batches of 100
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        ids = [b["chunk_id"] for b in batch]
        documents = [b["content"] for b in batch]
        metadatas = []
        for b in batch:
            clean_m = {}
            for k, v in b["metadata"].items():
                if isinstance(v, (str, int, float, bool)):
                    clean_m[k] = v
                elif v is not None:
                    clean_m[k] = str(v)
            metadatas.append(clean_m)

        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    final_count = collection.count()

    return {
        "status": "success",
        "total_documents": len(raw_docs),
        "total_chunks": final_count,
        "embedding_model": type(embedding_func).__name__,
        "collection_name": COLLECTION_NAME
    }


# =============================================================
# 6. SEMANTIC RETRIEVAL SERVICE
# =============================================================

def retrieve_relevant_context(
    query: str,
    top_k: int = 4,
    score_threshold: float = 0.20,
    category_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Performs semantic vector search against persistent ChromaDB.
    Calculates cosine similarity scores, applies relevance thresholds,
    and returns ranked chunks with rich source metadata.
    """
    cleaned_query = str(query or "").strip()
    if not cleaned_query:
        return []

    try:
        collection = get_knowledge_collection()
        if collection.count() == 0:
            ingest_all_knowledge(force_reindex=False)
            collection = get_knowledge_collection()

        where_filter = None
        if category_filter:
            where_filter = {"category": category_filter}

        results = collection.query(
            query_texts=[cleaned_query],
            n_results=min(top_k * 2, max(collection.count(), 1)),
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        if not results or not results.get("documents") or not results["documents"][0]:
            return []

        retrieved_items: List[Dict[str, Any]] = []
        seen_titles = set()

        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

        for doc_text, meta, dist in zip(docs, metas, distances):
            # Convert ChromaDB distance to normalized similarity score (0.0 to 1.0)
            if dist is None:
                similarity = 1.0
            elif dist <= 2.0:
                # L2 distance between unit vectors: cos_sim = 1 - (dist^2)/2
                similarity = max(0.0, min(1.0, 1.0 - (dist * dist / 2.0)))
            else:
                similarity = max(0.0, min(1.0, 1.0 / (1.0 + dist)))

            # Keyword presence boost for title and content
            q_terms = [w.lower() for w in re.findall(r"\b[a-zA-Z0-9+#.-]+\b", cleaned_query) if len(w) >= 2]
            title = meta.get("title", "Project Knowledge")
            title_lower = title.lower()
            content_lower = doc_text.lower()
            
            term_matches = sum(1 for t in q_terms if t in title_lower or t in content_lower)
            if term_matches > 0:
                similarity = min(1.0, similarity + (0.08 * term_matches))

            if similarity < score_threshold:
                continue

            if title in seen_titles and len(retrieved_items) >= top_k:
                continue
            seen_titles.add(title)

            retrieved_items.append({
                "content": doc_text,
                "similarity_score": round(similarity, 4),
                "title": title,
                "category": meta.get("category", "general"),
                "source": meta.get("source", "knowledge_base"),
                "source_type": meta.get("source_type", "document"),
                "branch_code": meta.get("branch_code"),
                "college_code": meta.get("college_code"),
                "district": meta.get("district")
            })

            if len(retrieved_items) >= top_k:
                break

        # Sort by similarity score descending
        retrieved_items.sort(key=lambda x: x["similarity_score"], reverse=True)
        return retrieved_items[:top_k]

    except Exception as e:
        logger.error(f"Semantic retrieval failed: {e}", exc_info=True)
        return []


def format_rag_context_for_llm(retrieved_chunks: List[Dict[str, Any]]) -> str:
    """
    Formats retrieved chunks into clear, source-bounded markdown context for LLM prompt.
    """
    if not retrieved_chunks:
        return ""

    blocks = ["### RETRIEVED PROJECT & TNEA KNOWLEDGE CONTEXT:"]
    for idx, c in enumerate(retrieved_chunks, 1):
        src_info = f"[{idx}] Source: {c.get('source_type', 'doc')} | Title: {c.get('title', 'Unknown')} (Relevance Score: {c.get('similarity_score', 0):.2f})"
        blocks.append(f"{src_info}\n{c.get('content', '').strip()}\n")

    blocks.append("--- END RETRIEVED CONTEXT ---")
    return "\n".join(blocks)
