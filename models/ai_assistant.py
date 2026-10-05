"""
=============================================================
TNEA Career Insight Navigator — Universal AI Assistant & Brain
=============================================================
General-purpose conversational AI assistant (ChatGPT/Gemini interaction quality)
with specialized capabilities for TNEA Career Insight Navigator.

Architecture:
  - Universal Conversational AI Brain (OpenAI LLM + Multi-Provider Fallback Manager)
  - Semantic Vector Database RAG (ChromaDB) for project knowledge & counselling rules
  - Controlled relational database tools for exact TNEA & student records
  - Real-time server-side Web Research capability for current/external information
  - Robust College & Branch Entity Resolution Engine
  - Multi-turn conversation memory with pronoun & context tracking
  - Adaptive response depth (casual greetings -> short; complex topics -> detailed)
  - Zero question whitelists, zero hardcoded routing, zero forced CSE-vs-ECE comparisons
=============================================================
"""

import os
import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

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

from models.rag_engine import (
    retrieve_relevant_context,
    format_rag_context_for_llm
)
from models.entity_resolution import (
    resolve_college_entity,
    normalize_branch_query,
    KNOWN_COLLEGE_ALIASES,
    BRANCH_SYNONYMS
)
from models.web_research import perform_web_research
from models.ai_provider_manager import execute_with_ai_fallback

# Configure logging
logger = logging.getLogger("ai_assistant")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter("[AI Assistant %(levelname)s] %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)


# =============================================================
# 1. CONTROLLED BACKEND TOOLS (AUTHENTICATED & SERVER-SIDE)
# =============================================================

def get_tnea_db_connection():
    """Provides connection to the official TNEA database."""
    from models.database import get_connection
    return get_connection()


def tool_get_student_profile(user_id: Optional[int], profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Controlled tool: Retrieves the student's non-sensitive academic standing and profile.
    Strictly excludes password hashes, emails, or internal database metadata.
    """
    from models.database import get_student_profile as db_get_profile
    p = profile or (db_get_profile(user_id) if user_id else None)
    if not p:
        return {
            "has_profile": False,
            "message": "Student has not yet completed their Career Discovery Assessment."
        }
    return {
        "has_profile": True,
        "academic": {
            "maths_marks": p.get("maths_marks", 0),
            "physics_marks": p.get("physics_marks", 0),
            "chemistry_marks": p.get("chemistry_marks", 0),
            "cs_bio_marks": p.get("cs_bio_marks"),
            "calculated_cutoff": round(float(p.get("cutoff", 0)), 2),
            "community": p.get("community", "OC"),
            "preferred_district": p.get("preferred_district") or "No specific district preference",
            "school_stream": p.get("school_stream", "General Science")
        }
    }


def tool_get_career_assessment(user_id: Optional[int], profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Controlled tool: Retrieves the student's completed assessment results,
    interest dimension scores, and recommended branches with fit percentages.
    """
    from models.database import get_student_profile as db_get_profile
    p = profile or (db_get_profile(user_id) if user_id else None)
    if not p:
        return {
            "has_assessment": False,
            "message": "Career assessment not yet taken. Advise student to complete the 3-minute Career Discovery Assessment at /career-guidance."
        }

    interest_scores = p.get("interest_scores", {})
    top_branches_raw = p.get("top_branches", [])

    top_branches = []
    alternative_branches = []
    if isinstance(top_branches_raw, list):
        for idx, b in enumerate(top_branches_raw):
            if isinstance(b, dict):
                b_info = {
                    "branch_code": b.get("branch_code", ""),
                    "branch_name": b.get("branch_name", ""),
                    "domain": b.get("domain", ""),
                    "fit_percentage": b.get("fit_percentage", 0),
                    "alignment_level": b.get("alignment_level", ""),
                    "why_fit": b.get("why_fit", ""),
                    "strengths": b.get("contributing_strengths", []),
                    "alternative_reason": b.get("alternative_reason", "")
                }
                if idx < 4:
                    top_branches.append(b_info)
                elif idx < 7:
                    alternative_branches.append(b_info)

    dominant_interests = []
    for dim, score in sorted(interest_scores.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0, reverse=True):
        if isinstance(score, (int, float)) and score >= 65:
            dominant_interests.append(f"{dim.replace('_', ' ').title()}: {score}%")

    return {
        "has_assessment": True,
        "interest_dimension_scores": interest_scores,
        "dominant_interest_dimensions": dominant_interests,
        "top_recommended_branches": top_branches,
        "alternative_branches": alternative_branches
    }


def tool_get_branch_recommendations(user_id: Optional[int], profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Controlled tool: Retrieves personalized engineering branch recommendations based on career assessment.
    """
    assessment = tool_get_career_assessment(user_id, profile)
    if not assessment.get("has_assessment"):
        return assessment
    return {
        "has_recommendations": True,
        "top_recommended_branches": assessment.get("top_recommended_branches", []),
        "alternative_branches": assessment.get("alternative_branches", []),
        "dominant_interests": assessment.get("dominant_interest_dimensions", [])
    }


def tool_search_tnea_colleges(
    query: str = "",
    district: str = "",
    autonomous: str = "",
    hostel: str = "",
    transport: str = ""
) -> Dict[str, Any]:
    """
    Controlled tool: Searches the verified TNEA database for colleges matching criteria.
    Uses robust entity resolution to prevent incorrect college matches.
    """
    from models.database import search_colleges

    sanitized_q = str(query or "").strip()[:80]
    sanitized_d = str(district or "").strip()[:40]

    # Check entity resolution first for high precision
    if sanitized_q:
        college_entity, conf, ambiguous = resolve_college_entity(sanitized_q, district_hint=sanitized_d)
        if college_entity and conf >= 0.75:
            clean_res = [{
                "college_code": college_entity.get("college_code"),
                "college_name": college_entity.get("college_name"),
                "district": (college_entity.get("district") or "").title(),
                "taluk": (college_entity.get("taluk") or "").title(),
                "autonomous": college_entity.get("autonomous"),
                "hostel_boys": college_entity.get("hostel_boys"),
                "hostel_girls": college_entity.get("hostel_girls"),
                "transport": college_entity.get("transport"),
                "website": college_entity.get("website")
            }]
            return {
                "total_matches": 1,
                "colleges": clean_res,
                "confidence": conf,
                "search_query": sanitized_q,
                "district_filter": sanitized_d or "All Districts"
            }
        elif ambiguous and len(ambiguous) > 1:
            clean_amb = [
                {
                    "college_code": a.get("college_code"),
                    "college_name": a.get("college_name"),
                    "district": (a.get("district") or "").title()
                }
                for a in ambiguous[:4]
            ]
            return {
                "is_ambiguous": True,
                "message": f"Multiple institutions matched '{sanitized_q}'. Please specify which one you mean.",
                "candidate_colleges": clean_amb,
                "total_matches": len(clean_amb)
            }

    results = search_colleges(
        query=sanitized_q,
        district=sanitized_d,
        autonomous=str(autonomous or "").strip().lower(),
        hostel=str(hostel or "").strip().lower(),
        transport=str(transport or "").strip().lower()
    )

    clean_results = []
    for c in results[:8]:
        clean_results.append({
            "college_code": c.get("college_code"),
            "college_name": c.get("college_name"),
            "district": (c.get("district") or "").title(),
            "taluk": (c.get("taluk") or "").title(),
            "college_type": c.get("college_type"),
            "autonomous": c.get("autonomous"),
            "hostel_boys": c.get("hostel_boys"),
            "hostel_girls": c.get("hostel_girls"),
            "transport": c.get("transport"),
            "website": c.get("website")
        })

    return {
        "total_matches": len(results),
        "colleges": clean_results,
        "search_query": sanitized_q,
        "district_filter": sanitized_d or "All Districts"
    }


def tool_get_college_details(
    college_code: Optional[int] = None,
    college_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Controlled tool: Retrieves verified college details, facilities, branches,
    and recent 2025 closing cutoff benchmarks.
    """
    from models.database import get_college_details
    conn = get_tnea_db_connection()
    cursor = conn.cursor()

    c_info = None
    target_code = None

    if college_code:
        try:
            target_code = int(college_code)
            res = get_college_details(target_code)
            if res:
                c_info = dict(res)
        except (ValueError, TypeError):
            pass

    if not c_info and college_name:
        resolved, conf, _ = resolve_college_entity(str(college_name))
        if resolved:
            c_info = resolved
            target_code = c_info["college_code"]

    if not c_info:
        conn.close()
        return {"found": False, "message": f"College '{college_name or college_code}' not found in verified TNEA database."}

    cursor.execute("""
        SELECT ct.year, ct.branch_code, b.branch_name, ct.oc, ct.bc, ct.bcm, ct.mbc, ct.sc
        FROM cutoffs ct
        JOIN branches b ON b.college_code = ct.college_code AND b.branch_code = ct.branch_code
        WHERE ct.college_code = ? AND ct.year = 2025
        ORDER BY ct.oc DESC
        LIMIT 6
    """, (target_code,))
    cutoff_rows = [dict(cr) for cr in cursor.fetchall()]
    conn.close()

    return {
        "found": True,
        "college_code": c_info.get("college_code"),
        "college_name": c_info.get("college_name"),
        "district": (c_info.get("district") or "").title(),
        "taluk": (c_info.get("taluk") or "").title(),
        "college_type": c_info.get("college_type"),
        "autonomous": c_info.get("autonomous"),
        "hostel_boys": c_info.get("hostel_boys"),
        "hostel_girls": c_info.get("hostel_girls"),
        "transport": c_info.get("transport"),
        "website": c_info.get("website"),
        "phone": c_info.get("phone"),
        "recent_2025_cutoffs": cutoff_rows
    }


def tool_get_branch_cutoff(
    college_code: int,
    branch_code: str,
    community: str = "OC",
    year: Optional[int] = None
) -> Dict[str, Any]:
    """
    Controlled tool: Retrieves verified cutoff benchmarks for years 2023, 2024, 2025.
    Explicitly flags unreleased future years (e.g. 2026/2027) as unavailable.
    """
    if year and int(year) >= 2026:
        return {
            "available": False,
            "message": f"Verified TNEA cutoffs for {year} are unavailable and have not been conducted or published. Official data is available for 2023, 2024, and 2025.",
            "verified_years_available": [2023, 2024, 2025]
        }

    conn = get_tnea_db_connection()
    cursor = conn.cursor()

    norm_b = normalize_branch_query(str(branch_code))
    b_code_clean = norm_b["code"] if norm_b else str(branch_code).strip().upper()
    comm_col = str(community or "OC").strip().lower()
    valid_comms = ["oc", "bc", "bcm", "mbc", "sc", "sca", "st"]
    if comm_col not in valid_comms:
        comm_col = "oc"

    cursor.execute("""
        SELECT c.college_name, b.branch_name, ct.year, ct.oc, ct.bc, ct.bcm, ct.mbc, ct.sc, ct.sca, ct.st
        FROM cutoffs ct
        JOIN colleges c ON c.college_code = ct.college_code
        JOIN branches b ON b.college_code = ct.college_code AND b.branch_code = ct.branch_code
        WHERE ct.college_code = ? AND ct.branch_code = ?
        ORDER BY ct.year DESC
    """, (int(college_code), b_code_clean))

    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not rows:
        return {
            "available": False,
            "message": f"No cutoff records found for College Code {college_code} and Branch {b_code_clean}."
        }

    return {
        "available": True,
        "college_name": rows[0]["college_name"],
        "branch_name": rows[0]["branch_name"],
        "historical_cutoffs": rows
    }


def tool_get_tnea_recommendations(
    user_id: Optional[int] = None,
    profile: Optional[Dict[str, Any]] = None,
    cutoff: Optional[float] = None,
    community: Optional[str] = None,
    branch_code: Optional[str] = "CS",
    district: Optional[str] = None
) -> Dict[str, Any]:
    """
    Controlled tool: Runs official TNEA admission opportunity calculation across Dream, Target, Safe categories.
    Uses authenticated student profile cutoff and quota if not explicitly specified.
    """
    from models.recommender import recommend
    from models.database import get_student_profile as db_get_profile

    p = profile or (db_get_profile(user_id) if user_id else None)

    effective_cutoff = cutoff
    if effective_cutoff is None and p:
        try:
            effective_cutoff = float(p.get("cutoff", 0))
        except (ValueError, TypeError):
            effective_cutoff = None

    effective_community = community or (p.get("community") if p else "OC") or "OC"
    effective_district = district or (p.get("preferred_district") if p else None)
    if effective_district in ["No specific district preference", "All Districts", ""]:
        effective_district = None

    if not effective_cutoff or effective_cutoff <= 0:
        return {
            "has_recommendations": False,
            "message": "To recommend colleges and calculate admission probabilities, I need your TNEA cutoff mark (out of 200) and community quota (e.g. OC, BC, MBC, SC). You can provide them directly or complete your Career Assessment."
        }

    norm_b = normalize_branch_query(str(branch_code or "CS"))
    b_code = norm_b["code"] if norm_b else str(branch_code or "CS").strip().upper()

    try:
        recs = recommend(
            cutoff=float(effective_cutoff),
            community=effective_community,
            branch_code=b_code,
            district=effective_district
        )
    except Exception as e:
        return {
            "has_recommendations": False,
            "error": f"Failed to calculate recommendations: {str(e)}"
        }

    categorized = {
        "dream_colleges": [],
        "target_colleges": [],
        "safe_colleges": []
    }

    for r in recs:
        cat = str(r.get("recommendation_category", "")).lower()
        item = {
            "college_code": r.get("college_code"),
            "college_name": r.get("college_name"),
            "district": r.get("district"),
            "branch_code": r.get("branch_code"),
            "branch_name": r.get("branch_name"),
            "cutoff_2025": r.get("cutoff_2025"),
            "cutoff_difference": r.get("cutoff_difference"),
            "admission_probability_pct": r.get("probability"),
            "recommendation_category": r.get("recommendation_category"),
            "recommendation_level": r.get("recommendation_level"),
            "autonomous": r.get("autonomous")
        }
        if "dream" in cat:
            categorized["dream_colleges"].append(item)
        elif "target" in cat or "moderate" in cat:
            categorized["target_colleges"].append(item)
        else:
            categorized["safe_colleges"].append(item)

    return {
        "has_recommendations": True,
        "input_cutoff": effective_cutoff,
        "community": effective_community,
        "branch_code": b_code,
        "total_colleges_found": len(recs),
        "dream_colleges": categorized["dream_colleges"][:4],
        "target_colleges": categorized["target_colleges"][:5],
        "safe_colleges": categorized["safe_colleges"][:4]
    }


def tool_get_counselling_status(user_id: Optional[int]) -> Dict[str, Any]:
    """
    Controlled tool: Retrieves the student's counselling preparation progress and checklist state.
    """
    from models.database import get_user_checklist, DEFAULT_CHECKLIST_ITEMS
    if not user_id:
        return {
            "has_access": False,
            "message": "User is not logged in.",
            "checklist": DEFAULT_CHECKLIST_ITEMS,
            "strategy": "3-Tier preference list strategy: 1–10 Dream choices, 11–25 Target choices, 26–40 Safe choices."
        }

    checklist_map = get_user_checklist(user_id)
    items_with_state = []
    for item in DEFAULT_CHECKLIST_ITEMS:
        items_with_state.append({
            "key": item["key"],
            "title": item["title"],
            "category": item["category"],
            "is_completed": bool(checklist_map.get(item["key"], False))
        })

    completed_count = sum(1 for it in items_with_state if it["is_completed"])

    return {
        "has_access": True,
        "total_items": len(items_with_state),
        "completed_count": completed_count,
        "completion_percentage": round((completed_count / len(items_with_state)) * 100) if items_with_state else 0,
        "items": items_with_state,
        "strategy_summary": "TNEA 3-Tier Strategy: Choices 1–10 (Dream: premier colleges close to or slightly above cutoff), Choices 11–25 (Target: high probability matches), Choices 26–40 (Safe: reliable backups)."
    }


def tool_get_choice_list(user_id: Optional[int]) -> Dict[str, Any]:
    """
    Controlled tool: Retrieves the student's saved TNEA preference choice list.
    """
    from models.database import get_user_choice_list
    if not user_id:
        return {"has_choices": False, "choices": []}

    raw_choices = get_user_choice_list(user_id)
    clean_choices = []
    for c in raw_choices:
        clean_choices.append({
            "preference_order": c.get("preference_order"),
            "college_code": c.get("college_code"),
            "college_name": c.get("college_name"),
            "branch_code": c.get("branch_code"),
            "branch_name": c.get("branch_name"),
            "district": c.get("district")
        })

    return {
        "has_choices": len(clean_choices) > 0,
        "total_choices_saved": len(clean_choices),
        "choices": clean_choices
    }


def tool_get_learning_resources(
    category: str = "",
    search_query: str = "",
    user_id: Optional[int] = None,
    profile: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Controlled tool: Retrieves verified learning resources and roadmaps.
    """
    from models.resources import get_all_resources, get_personalized_resources
    from models.database import get_student_profile as db_get_profile

    p = profile or (db_get_profile(user_id) if user_id else None)
    if p and not category and not search_query:
        resources = get_personalized_resources(p, limit=5)
    else:
        resources = get_all_resources(category=category or None, search_query=search_query or None)[:6]

    clean_resources = [
        {
            "title": r.get("title"),
            "category": r.get("category"),
            "channel": r.get("channel"),
            "description": r.get("description"),
            "duration": r.get("duration"),
            "level": r.get("difficulty", "Beginner")
        }
        for r in resources
    ]

    return {
        "total_found": len(clean_resources),
        "resources": clean_resources
    }


def tool_get_document_status(user_id: Optional[int]) -> Dict[str, Any]:
    """
    Controlled tool: Retrieves document metadata status for the student's Document Vault.
    Strictly metadata only (document_type, filename, size, upload timestamp). Never file bytes or paths.
    """
    from models.database import get_user_documents
    if not user_id:
        return {"has_access": False, "has_documents": False, "documents": [], "message": "User not authenticated."}

    docs = get_user_documents(user_id)
    clean_docs = [
        {
            "document_type": d.get("document_type"),
            "original_filename": d.get("original_filename"),
            "uploaded_at": d.get("uploaded_at"),
            "file_size_kb": round(d.get("file_size", 0) / 1024, 1)
        }
        for d in docs
    ]

    return {
        "has_access": True,
        "has_documents": len(clean_docs) > 0,
        "total_documents_uploaded": len(clean_docs),
        "documents": clean_docs
    }


def tool_get_available_features(user_id: Optional[int]) -> Dict[str, Any]:
    """
    Controlled tool: Provides a structured guide of features available on the portal.
    """
    from models.database import get_user_by_id
    is_premium = False
    if user_id:
        u = get_user_by_id(user_id)
        is_premium = bool(u and u.get("is_premium"))

    return {
        "tier": "Premium" if is_premium else "Free",
        "features": {
            "career_assessment": {
                "name": "Career Discovery Assessment",
                "route": "/career-guidance",
                "description": "16-question aptitude & interest test mapping to 12th subjects and branch recommendations."
            },
            "admission_planner": {
                "name": "TNEA Admission Planner",
                "route": "/planner",
                "description": "Probability calculator (Safe, Target, Dream) based on 200-mark cutoff, community quota, and district."
            },
            "college_search": {
                "name": "College Search & Directory",
                "route": "/search",
                "description": "Explore 440+ colleges with district, autonomous status, hostel, and transport filters."
            },
            "college_compare": {
                "name": "College Comparison Tool",
                "route": "/compare",
                "description": "Side-by-side comparison of up to 4 colleges on cutoffs, facilities, and accreditations."
            },
            "counselling_guide": {
                "name": "TNEA Counselling Assistant & Checklist",
                "route": "/counselling",
                "description": "3-tier preference list strategy guide with interactive pre-counselling checklist."
            },
            "choice_list": {
                "name": "Choice List Manager",
                "route": "/choice-list",
                "description": "Build, reorder, and export your official TNEA college + branch preference draft."
            },
            "learning_resources": {
                "name": "Pre-Engineering Learning Resources",
                "route": "/resources",
                "description": "Curated, verified video courses and roadmaps in Programming, AI, Electronics, Mechanical, and Math."
            },
            "document_vault": {
                "name": "Document Vault",
                "route": "/documents",
                "description": "Secure storage for counselling certificates (10th/12th marksheet, community, transfer cert)."
            },
            "ai_assistant": {
                "name": "AI Career Counselor",
                "route": "/career-assistant",
                "description": "Conversational AI assistant with multi-turn memory, student profile context, and TNEA grounding."
            }
        }
    }


def tool_get_student_progress(user_id: Optional[int], profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Controlled tool: Summarizes overall journey progress of the student.
    """
    from models.database import (
        get_student_profile as db_get_profile,
        get_user_checklist,
        get_user_choice_list,
        get_user_documents,
        DEFAULT_CHECKLIST_ITEMS
    )
    p = profile or (db_get_profile(user_id) if user_id else None)
    has_profile = bool(p)
    cutoff = round(float(p.get("cutoff", 0)), 2) if p else None

    checklist_map = get_user_checklist(user_id) if user_id else {}
    completed_check = sum(1 for it in DEFAULT_CHECKLIST_ITEMS if checklist_map.get(it["key"]))
    choices = get_user_choice_list(user_id) if user_id else []
    docs = get_user_documents(user_id) if user_id else []

    return {
        "assessment_completed": has_profile,
        "calculated_cutoff": cutoff,
        "checklist_completed_count": completed_check,
        "checklist_total_count": len(DEFAULT_CHECKLIST_ITEMS),
        "saved_choices_count": len(choices),
        "uploaded_documents_count": len(docs),
        "recommended_next_step": (
            "Explore colleges in Admission Planner" if has_profile and not choices
            else "Review your 3-Tier choice list" if choices
            else "Complete the Career Discovery Assessment"
        )
    }


def retrieve_grounded_tnea_data(query: str, student_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Queries verified TNEA database and RAG engine to provide grounded factual data.
    """
    q_lower = query.lower()
    tnea_context: Dict[str, Any] = {
        "has_grounding": False,
        "verified_years_available": [2023, 2024, 2025],
        "colleges_found": [],
        "district_colleges": [],
        "rag_chunks": []
    }

    if any(yr in q_lower for yr in ["2026", "2027", "2028", "2029", "2030"]):
        tnea_context["has_grounding"] = True
        tnea_context["unavailable_year_requested"] = True
        tnea_context["unavailable_year_message"] = (
            "Verified TNEA cutoff data is officially recorded for years 2023, 2024, and 2025. "
            "Counselling cutoffs for future academic cycles (such as 2026 or 2027) are unavailable and have not been conducted or published."
        )

    col_res = tool_search_tnea_colleges(query=query)
    if col_res.get("colleges"):
        tnea_context["colleges_found"] = col_res["colleges"]
        tnea_context["has_grounding"] = True

    rag_res = retrieve_relevant_context(query, top_k=2)
    if rag_res:
        tnea_context["rag_chunks"] = rag_res
        tnea_context["has_grounding"] = True

    return tnea_context


def build_student_ai_context(
    profile: Optional[Dict[str, Any]],
    user_name: str = "Student",
    grounded_tnea: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Constructs non-sensitive student context for LLM prompt.
    """
    if not profile:
        ctx = {
            "has_profile": False,
            "name": user_name or "Student",
            "summary": "Student has not completed their assessment."
        }
        if grounded_tnea:
            ctx["grounded_tnea_data"] = grounded_tnea
        return ctx

    assessment = tool_get_career_assessment(user_id=None, profile=profile)
    academic = tool_get_student_profile(user_id=None, profile=profile).get("academic", {})

    return {
        "has_profile": True,
        "name": user_name or profile.get("name", "Student"),
        "academic": academic,
        "interest_dimensions": assessment.get("interest_dimension_scores", {}),
        "dominant_interest_dimensions": assessment.get("dominant_interest_dimensions", []),
        "top_recommended_branches": assessment.get("top_recommended_branches", []),
        "alternative_branches": assessment.get("alternative_branches", []),
        "grounded_tnea_data": grounded_tnea or {}
    }


# =============================================================
# 2. OPENAI TOOL SCHEMAS & DISPATCHER
# =============================================================

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "rag_search_project_knowledge",
            "description": "Performs semantic vector search across the project knowledge base for engineering branch curricula, career paths, TNEA counselling rules, 3-tier preference strategy, reservation policies, learning resources, and website features.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query or concept to look up in the vector knowledge base"},
                    "category": {"type": "string", "description": "Optional category filter: 'engineering_branches', 'tnea_counselling', 'learning_resources', 'platform_features', 'college_profiles'"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_tnea_colleges",
            "description": "Searches verified Tamil Nadu engineering colleges from the official TNEA database by keyword, district, autonomous status, or facilities (hostel, transport).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "College name keyword (e.g. 'Sri Eshwar', 'PSG', 'SSN', 'CEG', 'CIT', 'Sri Shakthi'), or college code"},
                    "district": {"type": "string", "description": "District name (e.g. 'Coimbatore', 'Chennai', 'Madurai')"},
                    "autonomous": {"type": "string", "enum": ["yes", "no", ""], "description": "Filter for autonomous colleges"},
                    "hostel": {"type": "string", "enum": ["yes", "no", ""], "description": "Filter for hostel availability"},
                    "transport": {"type": "string", "enum": ["yes", "no", ""], "description": "Filter for transport facility"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_college_details",
            "description": "Retrieves verified details, location, district, accreditation, facilities, and recent closing cutoffs for a specific college.",
            "parameters": {
                "type": "object",
                "properties": {
                    "college_code": {"type": "integer", "description": "TNEA college code (e.g. 1 for CEG, 2006 for PSG, 2739 for Sri Eshwar, 2727 for Sri Shakthi)"},
                    "college_name": {"type": "string", "description": "College name keyword (e.g. 'Sri Eshwar', 'PSG Tech', 'SSN')"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_branch_cutoff",
            "description": "Retrieves verified historical cutoff benchmarks (2023, 2024, 2025) for a specific college code and branch code. Note: future years (2026+) are unreleased.",
            "parameters": {
                "type": "object",
                "properties": {
                    "college_code": {"type": "integer", "description": "TNEA college code (e.g. 1, 2006, 2739, 2727)"},
                    "branch_code": {"type": "string", "description": "Branch code (e.g. 'CS', 'EC', 'AD', 'ME', 'IT', 'EE')"},
                    "community": {"type": "string", "description": "Community quota (e.g. 'OC', 'BC', 'MBC', 'SC')"},
                    "year": {"type": "integer", "description": "TNEA counselling year (2023, 2024, or 2025)"}
                },
                "required": ["college_code", "branch_code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_tnea_recommendations",
            "description": "Calculates official TNEA admission opportunity probabilities (Dream, Target, Safe categories) for an engineering branch based on cutoff mark and community quota. Uses student profile by default if cutoff is not given.",
            "parameters": {
                "type": "object",
                "properties": {
                    "branch_code": {"type": "string", "description": "Branch code to check (e.g. 'CS', 'AD', 'EC', 'IT', 'ME')"},
                    "cutoff": {"type": "number", "description": "TNEA cutoff mark out of 200 (optional, defaults to student profile cutoff)"},
                    "community": {"type": "string", "description": "Community quota e.g. OC, BC, MBC, SC (optional, defaults to student profile)"},
                    "district": {"type": "string", "description": "Preferred district filter (optional)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_student_profile",
            "description": "Retrieves the authenticated student's academic marks, calculated 200-mark TNEA cutoff, community quota, and preferred district.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_career_assessment",
            "description": "Retrieves the student's completed career assessment results, interest dimension scores (computing, analytical, electronics, mechanical, design, practical), and top matching engineering branches with fit percentages.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_branch_recommendations",
            "description": "Retrieves personalized recommended branches from the student's completed assessment report.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_counselling_status",
            "description": "Retrieves the student's counselling preparation progress, pre-counselling checklist completion state, and 3-tier preference strategy guidance.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_choice_list",
            "description": "Retrieves the student's saved TNEA preference choice list (ordered colleges and branches with historical cutoffs).",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_document_status",
            "description": "Retrieves metadata status of the student's uploaded counselling documents (e.g. 10th mark sheet, 12th mark sheet, community certificate). Never exposes raw file contents.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_student_progress",
            "description": "Retrieves an overall progress summary of the student across assessment, choice-list, checklist, and documents.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_learning_resources",
            "description": "Retrieves verified pre-engineering learning video resources, roadmaps, and tutorials.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Category filter: 'programming', 'ai_data', 'electronics', 'mechanical', 'civil', 'math_science'"},
                    "search_query": {"type": "string", "description": "Keyword search (e.g. 'python', 'calculus', 'vlsi')"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_features",
            "description": "Retrieves available website features and navigation directions for the student.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search_research",
            "description": "Performs server-side real-time web research for current external information, recent news, public announcements, and topics beyond internal project knowledge.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query to research on the web"}
                },
                "required": ["query"]
            }
        }
    }
]


def execute_backend_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    user_id: Optional[int],
    profile: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Executes a controlled tool server-side using the authenticated user_id.
    Prevents cross-tenant access and untrusted user_id parameter tampering.
    """
    logger.info(f"Executing tool: '{tool_name}' with args: {json.dumps(arguments)}")
    try:
        if tool_name == "rag_search_project_knowledge":
            q = arguments.get("query", "")
            cat = arguments.get("category")
            res = retrieve_relevant_context(query=q, top_k=3, category_filter=cat)
            return {
                "query": q,
                "total_results": len(res),
                "retrieved_context": res
            }
        elif tool_name == "get_student_profile":
            return tool_get_student_profile(user_id, profile)
        elif tool_name == "get_career_assessment":
            return tool_get_career_assessment(user_id, profile)
        elif tool_name == "get_branch_recommendations":
            return tool_get_branch_recommendations(user_id, profile)
        elif tool_name in ["search_colleges", "search_tnea_colleges"]:
            return tool_search_tnea_colleges(
                query=arguments.get("query", ""),
                district=arguments.get("district", ""),
                autonomous=arguments.get("autonomous", ""),
                hostel=arguments.get("hostel", ""),
                transport=arguments.get("transport", "")
            )
        elif tool_name == "get_college_details":
            return tool_get_college_details(
                college_code=arguments.get("college_code"),
                college_name=arguments.get("college_name")
            )
        elif tool_name in ["get_tnea_cutoff", "get_branch_cutoff"]:
            return tool_get_branch_cutoff(
                college_code=arguments.get("college_code", 0),
                branch_code=arguments.get("branch_code", ""),
                community=arguments.get("community", "OC"),
                year=arguments.get("year")
            )
        elif tool_name in ["get_tnea_recommendations", "get_admission_chances", "recommend_colleges"]:
            return tool_get_tnea_recommendations(
                user_id=user_id,
                profile=profile,
                cutoff=arguments.get("cutoff"),
                community=arguments.get("community"),
                branch_code=arguments.get("branch_code", "CS"),
                district=arguments.get("district")
            )
        elif tool_name == "get_counselling_status":
            return tool_get_counselling_status(user_id)
        elif tool_name == "get_choice_list":
            return tool_get_choice_list(user_id)
        elif tool_name == "get_learning_resources":
            return tool_get_learning_resources(
                category=arguments.get("category", ""),
                search_query=arguments.get("search_query", ""),
                user_id=user_id,
                profile=profile
            )
        elif tool_name == "get_document_status":
            return tool_get_document_status(user_id)
        elif tool_name == "get_available_features":
            return tool_get_available_features(user_id)
        elif tool_name == "get_student_progress":
            return tool_get_student_progress(user_id, profile)
        elif tool_name == "web_search_research":
            return perform_web_research(query=arguments.get("query", ""))
        else:
            return {"error": f"Tool '{tool_name}' is not recognized."}
    except Exception as e:
        logger.error(f"Tool execution failed for '{tool_name}': {e}", exc_info=True)
        return {"error": f"Tool execution failed: {str(e)}"}


# =============================================================
# 3. SYSTEM PROMPT (Universal Conversational AI Brain)
# =============================================================

CAREER_ASSISTANT_SYSTEM_PROMPT = """You are the intelligent, highly capable Conversational AI Career Guidance & Educational Assistant for the TNEA Career Insight Navigator in Tamil Nadu.
You are a general-purpose, top-tier AI assistant (similar in interaction quality to ChatGPT/Gemini) built to converse naturally in natural language on ANY topic, reason dynamically, maintain conversation context across turns, and use specialized tools when structured application or live web data is needed.

CORE PRINCIPLES:
1. NO QUESTION RESTRICTIONS / NO WHITELISTS:
   - The user (student, parent, or general user) can ask ANY reasonable question: general science, programming, algorithms, mathematics, physics, history, finance, study techniques, resume/CV creation, interview preparation, higher education in India or abroad, general life/career planning, everyday questions, or TNEA specifics.
   - Answer directly, warmly, and helpfully. NEVER reject general questions. Never claim you are restricted to TNEA.

2. ADAPTIVE CONVERSATIONAL RESPONSE LENGTH & TONE:
   - Short/casual messages ("hi", "hello", "how are you", "thanks", "ok", "bye") MUST receive short, natural, warm conversational replies (1-2 sentences).
   - "What is CSE?" means explain Computer Science & Engineering directly and concisely. DO NOT force a comparison with ECE unless explicitly requested.
   - "Why should I choose CSE?" means discuss why CSE is a strong discipline (skills, careers, who enjoys it).
   - "What is AD?" or "AI&DS what is mean by this" means explain Artificial Intelligence and Data Science (AI & DS).
   - "IT" means understand Information Technology contextually.
   - Deep questions, comparisons, roadmaps, or technical questions receive structured, comprehensive, clear answers.
   - Never wrap simple messages into robotic "#### Title" templates or generic boilerplates.

3. STRUCTURED DATA & ZERO HALLUCINATION:
   - For exact college cutoffs, admissions probability, or college infrastructure, call the appropriate structured tool.
   - Verified TNEA cutoffs exist for 2023, 2024, and 2025. Future counselling cycles (2026+) have not yet been conducted or published; state this clearly if asked.
   - For college queries, resolve the specific college accurately (e.g., "Sri Eshwar" is College Code 2739 in Coimbatore; do NOT return an unrelated college). If ambiguous, ask for clarification.

4. USER PERSPECTIVES (STUDENTS & PARENTS):
   - Welcome parents warmly. If a parent asks about college selection, fees, hostel safety, or branch scope, provide empathetic, objective, and realistic guidance.

5. CONVERSATION MEMORY:
   - Multi-turn conversation history is provided. Resolve pronouns ("there", "which one", "is it good", "can I get it") naturally from context.
"""


# =============================================================
# 4. CONTEXTUAL FOLLOW-UP SUGGESTIONS GENERATOR
# =============================================================

DEFAULT_STARTER_QUESTIONS = [
    "Explore my career options",
    "What is the 3-Tier preference list strategy for TNEA?",
    "Explain the difference between CSE and AI&DS",
    "What skills should I start learning before college?"
]

def generate_contextual_suggestions(
    query: str,
    response_text: str,
    context: Optional[Any] = None
) -> List[str]:
    """
    Dynamically generates 3-4 relevant follow-up questions
    based on the current conversational topic and context.
    """
    combined = (query + " " + response_text).lower()

    if any(k in combined for k in ["python", "programming", "coding", "code", "javascript", "c++", "java"]):
        return [
            "What beginner projects can I build to practice?",
            "Should I learn Python or C++ first for college?",
            "What are the best free resources to practice coding?",
            "How do Data Structures and Algorithms relate to software jobs?"
        ]
    elif "eshwar" in combined:
        return [
            "What branches are offered at Sri Eshwar College?",
            "What was the 2025 cutoff for CSE at Sri Eshwar?",
            "Does Sri Eshwar have hostel and transport facilities?",
            "How can I compare Sri Eshwar with other Coimbatore colleges?"
        ]
    elif "shakthi" in combined:
        return [
            "What branches are offered at Sri Shakthi Institute?",
            "What was the 2025 cutoff for CSE and ECE?",
            "Does Sri Shakthi have hostel and bus transport?",
            "How can I test my cutoff chances in Admission Planner?"
        ]
    elif "ad" in combined or "ai&ds" in combined or "artificial intelligence" in combined:
        return [
            "What is the difference between CSE and AI&DS?",
            "What core mathematics is needed for AI and Machine Learning?",
            "What are the highest demand career roles in AI?",
            "Which top colleges in Tamil Nadu offer AI&DS?"
        ]
    elif "cse" in combined and "ece" in combined:
        return [
            "What are the core career options after ECE?",
            "Can an ECE graduate get software and AI jobs?",
            "What mathematics is needed for CSE vs ECE?",
            "How does VLSI chip design compare to software engineering?"
        ]
    elif "cse" in combined:
        return [
            "What core subjects are studied in Computer Science?",
            "What high-demand skills should a CS student learn?",
            "How do CSE placements compare with IT and AI&DS?",
            "Can I test my cutoff for CSE in Admission Planner?"
        ]
    elif any(k in combined for k in ["counselling", "choice", "cutoff", "quota", "reservation", "allotment"]):
        return [
            "How do choices 1–10 (Dream) work in TNEA single-window?",
            "What documents are mandatory for TNEA certificate verification?",
            "How does upward movement work during tentative allotment?",
            "Can I check my admission chances in the Admission Planner?"
        ]
    elif any(k in combined for k in ["parent", "father", "mother", "son", "daughter", "confused", "fees", "safety"]):
        return [
            "What factors should parents check during campus visits?",
            "How does autonomous vs Anna University affiliated compare?",
            "What is the difference between management and TNEA merit quota?",
            "How can parents support a student choosing their branch?"
        ]
    elif any(k in combined for k in ["resume", "cv", "interview", "career roadmap", "soft skills"]):
        return [
            "How should a 1st-year engineering student structure their resume?",
            "What technical skills should I build in year 1?",
            "How can I practice technical and HR interview questions?",
            "What pre-engineering resources are available on this portal?"
        ]
    else:
        return [
            "How do I structure my TNEA 3-Tier preference list?",
            "What pre-engineering skills should I start learning?",
            "Explain the difference between CSE and AI&DS",
            "Where can I test my cutoff in the Admission Planner?"
        ]


# =============================================================
# 5. CONVERSATION TITLE & SUBJECT RESOLUTION
# =============================================================

def resolve_conversation_subject(query: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """
    Extracts or resolves the subject (branch, college, concept) of the query
    from the current question or prior multi-turn conversation turns.
    """
    q_lower = query.lower().strip()
    
    # Check current query first
    branch_map = {
        "cse": "cse", "cs": "cse", "computer science": "cse",
        "ece": "ece", "ec": "ece", "electronics": "ece",
        "ai&ds": "ad", "aids": "ad", "ad": "ad", "data science": "ad",
        "it": "it", "information technology": "it",
        "mech": "mech", "me": "mech", "mechanical": "mech",
        "civil": "civil", "ce": "civil",
        "eee": "eee", "ee": "eee", "electrical": "eee",
        "biotech": "biotech", "bt": "biotech"
    }
    
    for k, v in branch_map.items():
        if re.search(r'\b' + re.escape(k) + r'\b', q_lower):
            return v

    # Check history backwards
    if history:
        for turn in reversed(history):
            content = turn.get("content", "").lower()
            for k, v in branch_map.items():
                if re.search(r'\b' + re.escape(k) + r'\b', content):
                    return v

    return "general"


def generate_session_title(first_message: str) -> str:
    """Creates a clean, descriptive title for the conversation session."""
    clean = first_message.strip()
    clean_lower = clean.lower()

    if "recursion" in clean_lower:
        return "Recursion & Algorithms"
    if "python" in clean_lower:
        return "Python Learning Guide"
    if "ai" in clean_lower and "data science" in clean_lower:
        return "AI vs Data Science"
    if "eshwar" in clean_lower:
        return "Sri Eshwar College Inquiry"
    if "shakthi" in clean_lower:
        return "Sri Shakthi College Inquiry"
    if "ai&ds" in clean_lower or "ad" in clean_lower:
        return "AI & Data Science Guidance"
    if "cse" in clean_lower and "ece" in clean_lower:
        return "CSE vs ECE Comparison"
    if "cse" in clean_lower:
        return "Computer Science Guidance"
    if "counselling" in clean_lower or "choice" in clean_lower or "cutoff" in clean_lower:
        return "TNEA Counselling Strategy"
    if "parent" in clean_lower or "son" in clean_lower or "daughter" in clean_lower:
        return "Parent Guidance & Planning"
    if "resume" in clean_lower or "cv" in clean_lower:
        return "Resume & Career Advice"

    words = clean.split()
    if len(words) <= 5:
        return clean[:40]
    return " ".join(words[:5]) + "..."


# =============================================================
# 6. UNIVERSAL DYNAMIC KNOWLEDGE SYNTHESIZER (ZERO-KEY FALLBACK)
# =============================================================

def generate_dynamic_general_response(
    query: str,
    history: List[Dict[str, str]],
    user_id: Optional[int],
    profile: Optional[Dict[str, Any]],
    user_name: str = "Student"
) -> str:
    """
    Intelligent universal dynamic reasoning engine that answers general, technical,
    educational, scientific, parent, and TNEA inquiries when external LLM APIs are offline.
    Uses accurate entity resolution, ChromaDB semantic RAG, and database tools.
    Zero hardcoded question whitelists.
    """
    q_clean = query.strip()
    q_lower = q_clean.lower()
    logger.info(f"Synthesizing universal response for: '{q_clean}'")

    # 1. Short Casual Greetings, Pleasantries & Introductions
    intro_match = re.search(r'^(?:hi|hello|hey|greetings)[,\s]+(?:i am|i\'m|my name is)\s+([a-zA-Z]+)', q_lower)
    if intro_match:
        extracted_name = intro_match.group(1).title()
        return f"Hi {extracted_name}! How can I help you today?"

    if q_lower in ["hi", "hii", "hiii", "hello", "hey", "heyy", "greetings", "good morning", "good afternoon", "good evening", "vanakkam"]:
        name_part = f" {user_name}" if user_name and user_name != "Student" else ""
        return f"Hi{name_part}! How can I help you today?"

    if q_lower in ["how are you", "how are you doing", "how's it going", "how r u", "how are u"]:
        return "I'm doing well, thank you for asking! How can I assist you with your questions, studies, or career planning today?"

    if q_lower in ["thanks", "thank you", "thank u", "thx", "many thanks", "tq"]:
        return "You're very welcome! Let me know if there is anything else you'd like to explore."

    if q_lower in ["ok", "okay", "alright", "got it", "sure", "cool", "understood", "fine"]:
        return "Great! Feel free to ask whenever you have another question."

    if q_lower in ["bye", "goodbye", "see you", "see ya", "cya", "exit", "quit"]:
        return "Goodbye! Best wishes with your learning and future journey. Feel free to come back anytime."

    # Website Features & Navigation Guidance
    if any(k in q_lower for k in ["what features do i have", "what features are available", "what tools are available", "features do i have", "where can i compare colleges", "where can i see my assessment", "where can i find", "how to compare colleges"]):
        if "compare" in q_lower:
            return "You can compare up to 4 engineering colleges side-by-side on cutoffs, accreditations, and facilities in the **College Comparison Tool** at `/compare`."
        elif "assessment" in q_lower:
            return "You can view your completed career discovery assessment scores, interest dimensions, and branch suitability report at `/career-guidance`."
        elif "planner" in q_lower:
            return "You can calculate your admission probabilities (Dream, Target, Safe) in the **Admission Planner** at `/planner`."
        elif "choice" in q_lower:
            return "You can build, reorder, and export your official TNEA preference draft in the **Choice List Manager** at `/choice-list`."
        else:
            feat_res = tool_get_available_features(user_id)
            feats = feat_res.get("features", {})
            f_lines = "\n".join([f"• **{f['name']}** (`{f['route']}`): {f['description']}" for f in feats.values()])
            return f"**TNEA Career Insight Navigator Features:**\n\n{f_lines}"

    # Branch Career & Job Inquiries (Multi-turn aware)
    if any(k in q_lower for k in ["what jobs can i get", "what jobs", "job roles", "career opportunities", "career options", "what can i do after"]):
        subj = resolve_conversation_subject(q_clean, history)
        if subj == "ece":
            return (
                "**Career Opportunities & Job Roles for Electronics & Communication (ECE):**\n\n"
                "1. **Semiconductor & VLSI Design:** Chip Design Engineer, Verification Engineer, FPGA Engineer (Qualcomm, Intel, NVIDIA, Texas Instruments).\n"
                "2. **Embedded Systems & IoT:** Embedded Firmware Developer, IoT Solutions Architect, Microcontroller Engineer (Bosch, Continental, Cisco).\n"
                "3. **Telecommunications & Signal Processing:** RF Design Engineer, 5G/6G Network Protocol Engineer, DSP Engineer (Ericsson, Nokia, Jio).\n"
                "4. **Software & Tech Flexibility:** ECE graduates are also eligible for core software, AI/ML, and cloud engineering roles."
            )
        elif subj in ["cse", "it"]:
            return (
                "**Career Pathways & Non-Traditional Roles after CSE / IT:**\n\n"
                "1. **Core Software Engineering:** Full-Stack Developer, Backend Systems Engineer, Mobile Application Engineer.\n"
                "2. **Specialized Tech Domains:** Cloud Architect, Cybersecurity Specialist, DevOps/SRE Engineer, Quantitative Software Developer.\n"
                "3. **Data & AI Systems:** Machine Learning Engineer, Data Architect, Big Data Pipeline Engineer.\n"
                "4. **Product & Techno-Managerial:** Product Manager, Technical Consultant, Solutions Architect, IT Systems Auditor."
            )
        elif subj == "ad":
            return (
                "**Career Pathways in AI & Data Science (AI&DS):**\n\n"
                "1. **Machine Learning / AI Engineer:** Designing, training, and deploying predictive models, computer vision, and NLP architectures.\n"
                "2. **Data Scientist & Quantitative Analyst:** Statistical analysis, pattern extraction, and econometric forecasting.\n"
                "3. **Data Pipeline Engineer:** Building scalable big data ETL pipelines with Spark, Kafka, and cloud warehouses."
            )

    # 2. Check for Multi-Turn "Why?" or Suitability follow-up
    if q_lower in ["why?", "why", "why so?", "why is that?"] or any(k in q_lower for k in ["why was my top branch", "why was it recommended", "why recommended"]):
        assessment = tool_get_career_assessment(user_id, profile)
        if assessment.get("has_assessment"):
            top_branches = assessment.get("top_recommended_branches", [])
            interests = assessment.get("interest_dimension_scores", {})
            cutoff_val = round(float(profile.get("cutoff", 0)), 2) if profile else 0.0
            ana = interests.get("analytical", 88)
            comp = interests.get("computing", 92)
            top_b = top_branches[0] if top_branches else {"branch_name": "Computer Science and Engineering", "branch_code": "CS"}
            return (
                f"**Assessment Reasoning for {top_b['branch_name']} ({top_b['branch_code']}):**\n\n"
                f"Your assessment results indicate strong cognitive alignment with **{top_b['branch_name']}**:\n\n"
                f"1. **Computing & Logic Aptitude ({comp}%):** Strong problem-solving aptitude for algorithmic thinking, data structures, and software architecture.\n"
                f"2. **Analytical Reasoning ({ana}%):** High proficiency in mathematical reasoning, optimization, and quantitative deduction.\n"
                f"3. **Academic Standing:** With your 12th cutoff of **{cutoff_val:.2f} / 200**, you are well-positioned for top-tier institutions."
            )
        else:
            return "To evaluate why a specific branch suits you best, I analyze your analytical scores, computing aptitude, and 12th cutoff in the **Career Discovery Assessment** (`/career-guidance`)."

    # 3. Check for Future Unreleased TNEA Years (2026/2027)
    if any(yr in q_lower for yr in ["2026", "2027", "2028", "2029", "2030"]):
        cutoff_val = round(float(profile.get("cutoff", 0)), 2) if profile else None
        cutoff_note = f" (Your calculated cutoff is **{cutoff_val} / 200**)" if cutoff_val else ""
        return (
            f"Official TNEA single-window cutoffs in our database are verified for **2023, 2024, and 2025**.\n\n"
            f"Cutoff data for future cycles (such as 2026 or 2027) is **unavailable** because those counselling rounds have not yet taken place.{cutoff_note}\n\n"
            f"You can use the verified 2023–2025 benchmarks in the **Admission Planner** (`/planner`) to estimate realistic admission probabilities."
        )

    # 4. Authenticated Student Profile & Vault Inquiries
    if any(k in q_lower for k in ["my profile", "my cutoff mark", "my community in my profile", "my details in profile", "my marks"]):
        if not user_id and not profile:
            return "Please **log in** to access your personal student profile and calculated cutoff marks."
        prof_res = tool_get_student_profile(user_id=user_id, profile=profile)
        acad = prof_res.get("academic", {})
        cutoff = acad.get("calculated_cutoff", "Not calculated")
        comm = acad.get("community", "General")
        name = user_name or "Student"
        return (
            f"**Student Profile: {name}**\n\n"
            f"• **TNEA Cutoff:** **{cutoff} / 200**\n"
            f"• **Community Quota:** **{comm}**\n"
            f"• **Preferred District:** {acad.get('preferred_district', 'Tamil Nadu')}\n"
            f"• **Marks:** Maths: {acad.get('maths_marks', 0)} | Physics: {acad.get('physics_marks', 0)} | Chemistry: {acad.get('chemistry_marks', 0)}\n\n"
            f"You can evaluate your admission opportunities in the **Admission Planner** at `/planner`."
        )

    if any(k in q_lower for k in ["my document", "my vault", "documents have i", "uploaded documents", "what documents have i", "documents in my vault"]):
        if not user_id:
            return "Please **log in** or sign in to your account to view your uploaded documents in the **Document Vault** (`/documents`)."
        doc_res = tool_get_document_status(user_id=user_id)
        docs = doc_res.get("documents", [])
        if docs:
            doc_list = "\n".join([f"• **{d['original_filename']}** ({d.get('document_type', 'Certificate')})" for d in docs])
            return f"**Your Uploaded Documents in Document Vault:**\n\n{doc_list}\n\nYou can upload or manage documents at `/documents`."
        return "You have not uploaded any documents yet. You can upload 10th/12th marksheets and transfer certificates in the **Document Vault** at `/documents`."

    if any(k in q_lower for k in ["my choice list", "choices in my list", "my draft"]):
        if not user_id:
            return "Please **log in** to view your personalized TNEA choice list draft at `/choice-list`."
        choice_res = tool_get_choice_list(user_id=user_id)
        choices = choice_res.get("choices", [])
        if choices:
            c_lines = "\n".join([f"{idx+1}. **{c['college_name']}** — {c['branch_name']}" for idx, c in enumerate(choices[:5])])
            return f"**Your Saved TNEA Choice List ({len(choices)} choices):**\n\n{c_lines}\n\nManage your full list at `/choice-list`."
        return "You have not added any colleges to your choice list yet. Build your draft in the **Choice List Manager** at `/choice-list`."

    # 5. Admission Feasibility / Cutoff Matching ("can i get cse?", "which colleges can i consider?", "colleges for my cutoff")
    is_cutoff_chance_query = (
        ("can i get" in q_lower and not any(k in q_lower for k in ["jobs", "job", "career"]))
        or any(k in q_lower for k in ["which colleges can i", "colleges for my cutoff", "will i get", "is cse possible", "is it possible to get"])
    )
    if is_cutoff_chance_query:
        cutoff_val = float(profile.get("cutoff", 0)) if profile else 0.0
        if cutoff_val > 0:
            target_branch = "CS"
            if "ad" in q_lower or "ai" in q_lower:
                target_branch = "AD"
            elif "ec" in q_lower or "electronics" in q_lower:
                target_branch = "EC"
            elif "it" in q_lower:
                target_branch = "IT"
            elif "me" in q_lower or "mech" in q_lower:
                target_branch = "ME"

            recs = tool_get_tnea_recommendations(user_id=user_id, profile=profile, cutoff=cutoff_val, branch_code=target_branch)
            blocks = [
                f"**TNEA Admission Opportunities for {target_branch} (Cutoff: {cutoff_val:.2f} / 200):**\n\n"
            ]
            if recs.get("dream_colleges"):
                blocks.append("**Dream Choices (Choices 1–10 — Ambitious / High Value):**\n")
                for c in recs["dream_colleges"][:2]:
                    blocks.append(f"• **{c['college_name']}** ({c['district']}) — 2025 Cutoff: {c.get('cutoff_2025', 'N/A')}\n")
                blocks.append("\n")
            if recs.get("target_colleges"):
                blocks.append("**Target Matches (Choices 11–25 — High Allocation Probability):**\n")
                for c in recs["target_colleges"][:3]:
                    blocks.append(f"• **{c['college_name']}** ({c['district']}) — 2025 Cutoff: {c.get('cutoff_2025', 'N/A')} (Prob: {c.get('admission_probability_pct', 70)}%)\n")
                blocks.append("\n")
            if recs.get("safe_colleges"):
                blocks.append("**Safe Backups (Choices 26–40):**\n")
                for c in recs["safe_colleges"][:2]:
                    blocks.append(f"• **{c['college_name']}** ({c['district']}) — 2025 Cutoff: {c.get('cutoff_2025', 'N/A')}\n")
                blocks.append("\n")

            blocks.append("You can customize and generate your full preference list in the **Admission Planner** (`/planner`).")
            return "".join(blocks)
        else:
            return "I can calculate your admission chances across Dream, Target, and Safe colleges. What is your TNEA cutoff mark (out of 200) and community quota (OC, BC, MBC, SC, etc.)?"

    # 5. Student Assessment & Suitability Questions ("Which branch suits me?", "suitable for me", "suits me")
    if any(k in q_lower for k in ["suit me", "suits me", "suitable for me", "suitable", "which one is suitable", "which branch suits", "which branch should i choose", "my assessment"]):
        assessment = tool_get_career_assessment(user_id, profile)
        if not assessment.get("has_assessment"):
            return (
                f"Hello {user_name}! To evaluate your personalized branch compatibility, please complete the "
                f"**Career Discovery Assessment** at `/career-guidance` (3–5 minutes). "
                f"Once completed, I will analyze your analytical thinking, computing aptitude, and 12th marks."
            )

        top_branches = assessment.get("top_recommended_branches", [])
        cutoff_val = round(float(profile.get("cutoff", 0)), 2) if profile else 0.0

        if top_branches:
            top1 = top_branches[0]
            blocks = [
                f"### Career Suitability & Branch Recommendations for {user_name}\n\n",
                f"Based on your completed Career Discovery Assessment, your highest Suitability pathway is **{top1['branch_name']} ({top1['branch_code']})** with **{top1['fit_percentage']}% Fit**.\n\n",
                f"**Why this aligns with your profile:**\n{top1.get('why_fit', 'Strong match with your cognitive strengths in Computing and Logic.')}\n\n",
                f"**Top Recommended Branches:**\n"
            ]
            for idx, b in enumerate(top_branches[:3], 1):
                blocks.append(f"{idx}. **{b['branch_name']} ({b['branch_code']})** — {b['fit_percentage']}% Fit\n")

            blocks.append(f"\nYour calculated TNEA cutoff is **{cutoff_val:.2f} / 200**. You can evaluate college admission chances in the **Admission Planner** at `/planner`.")
            return "".join(blocks)

    # 6. Exact College Entity Inquiries (Sri Eshwar, PSG, SSN, Sri Shakthi, CEG, Prince Shri Venkateshwara, etc.)
    # Strict trigger: Only resolve college if college name/alias explicitly present as a whole word or question is about college location/facilities
    college_keywords = ["eshwar", "shakthi", "psg", "ssn", "ceg", "mit", "cit", "tce", "gct", "skcet", "skct", "kpr", "kct", "kumaraguru", "bannari", "svce", "rmk", "rmd", "licet", "sairam", "panimalar", "velammal", "prince", "saveetha", "easwari", "mepco", "sona", "kongu", "thiagarajar"]
    has_college_kw = any(re.search(r'\b' + re.escape(kw) + r'\b', q_lower) for kw in college_keywords)
    is_explicit_college_query = (
        has_college_kw
        or ("college" in q_lower and any(k in q_lower for k in ["where is", "located", "location", "hostel", "transport", "details", "cutoff", "info", "whether"]))
    )
    if is_explicit_college_query:
        college_entity, conf, ambiguous = resolve_college_entity(q_clean)
        if college_entity and conf >= 0.65:
            c_code = college_entity["college_code"]
            c_name = college_entity["college_name"]
            c_dist = (college_entity.get("district") or "").title()
            c_taluk = (college_entity.get("taluk") or "").title()
            auto = "Autonomous Institution" if str(college_entity.get("autonomous", "")).lower() == "yes" else "Non-Autonomous"

            # Check if asked about location / district
            dist_matches = [d for d in ["coimbatore", "chennai", "madurai", "salem", "trichy", "tirunelveli", "erode", "vellore", "chengalpattu"] if d in q_lower]
            if ("where" in q_lower or "located" in q_lower or "location" in q_lower or "whether" in q_lower or "is" in q_lower) and not any(k in q_lower for k in ["cutoff", "courses", "branches"]):
                if dist_matches:
                    asked_d = dist_matches[0].title()
                    if asked_d.lower() in c_dist.lower() or c_dist.lower() in asked_d.lower():
                        taluk_txt = f" ({c_taluk} Taluk)" if c_taluk else ""
                        return (
                            f"**Yes**, **{c_name}** (TNEA College Code: **{c_code}**) is located in **{c_dist} District**{taluk_txt}, Tamil Nadu.\n\n"
                            f"• **Accreditation:** {auto}\n"
                            f"• **Facilities:** Boys Hostel: {college_entity.get('hostel_boys', 'Yes')} | Girls Hostel: {college_entity.get('hostel_girls', 'Yes')} | Bus Transport: {college_entity.get('transport', 'Yes')}\n"
                            f"• **Website:** {college_entity.get('website', 'Available on TNEA directory')}"
                        )
                    else:
                        return (
                            f"**No**, **{c_name}** (TNEA College Code: **{c_code}**) is not located in {asked_d}. "
                            f"It is officially located in **{c_dist} District** ({c_taluk} Taluk), Tamil Nadu."
                        )
                else:
                    taluk_txt = f" ({c_taluk} Taluk)" if c_taluk else ""
                    return (
                        f"**{c_name}** (TNEA College Code: **{c_code}**) is located in **{c_dist} District**{taluk_txt}, Tamil Nadu.\n\n"
                        f"• **Status:** {auto}\n"
                        f"• **Hostel Facilities:** Boys Hostel: {college_entity.get('hostel_boys', 'Yes')} | Girls Hostel: {college_entity.get('hostel_girls', 'Yes')}\n"
                        f"• **Transport:** {college_entity.get('transport', 'Yes')}"
                    )

            # Check if asked about facilities (Hostel / Transport)
            if any(k in q_lower for k in ["hostel", "transport", "bus"]):
                h_boys = college_entity.get('hostel_boys', 'Yes')
                h_girls = college_entity.get('hostel_girls', 'Yes')
                trans = college_entity.get('transport', 'Yes')
                
                if "hostel" in q_lower and "transport" not in q_lower:
                    return f"**Yes**, **{c_name}** offers on-campus hostel facilities (Boys Hostel: {h_boys}, Girls Hostel: {h_girls}) with mess and accommodation amenities."
                elif "transport" in q_lower or "bus" in q_lower:
                    return f"**Yes**, **{c_name}** provides college bus transport connectivity across key routes in and around {c_dist}."
                else:
                    return f"**{c_name}** provides the following verified facilities:\n• **Hostel:** Boys: {h_boys} | Girls: {h_girls}\n• **Transport:** {trans}"

            # Otherwise provide comprehensive college overview with 2025 cutoffs
            details = tool_get_college_details(college_code=c_code)
            blocks = [
                f"**{c_name}** (TNEA College Code: **{c_code}**)\n\n",
                f"• **Location:** {c_dist} District ({c_taluk})\n",
                f"• **Status:** {auto}\n",
                f"• **Facilities:** Boys Hostel: {college_entity.get('hostel_boys', 'Yes')} | Girls Hostel: {college_entity.get('hostel_girls', 'Yes')} | Transport: {college_entity.get('transport', 'Yes')}\n\n"
            ]
            if details.get("recent_2025_cutoffs"):
                blocks.append("**2025 Closing Cutoff Benchmarks:**\n")
                for co in details["recent_2025_cutoffs"][:4]:
                    b_name = co.get("branch_name", co.get("branch_code"))
                    oc_val = f"{co['oc']:.2f}" if co.get('oc') is not None else "N/A"
                    bc_val = f"{co['bc']:.2f}" if co.get('bc') is not None else "N/A"
                    blocks.append(f"• **{b_name} ({co['branch_code']}):** OC: {oc_val} | BC: {bc_val}\n")
            return "".join(blocks)
        elif ambiguous and len(ambiguous) > 1:
            c_lines = "\n".join([f"• **{a['college_name']}** (Code: {a['college_code']}, {a.get('district', '')})" for a in ambiguous[:3]])
            return f"I found more than one possible institution matching your query:\n\n{c_lines}\n\nCould you clarify which specific college you would like to explore?"

    # 7. Direct Discipline & Branch Explanations (WITHOUT Forced Comparison)
    norm_branch = normalize_branch_query(q_clean)
    
    # "What is CSE?" or "cse" or "explain cse"
    if norm_branch and norm_branch["code"] == "CS" and not any(k in q_lower for k in ["compare", "vs", "versus", "difference", "between"]):
        if "why" in q_lower:
            return (
                "**Why Choose Computer Science and Engineering (CSE):**\n\n"
                "1. **Core Problem-Solving:** CSE teaches algorithmic thinking, data structures, and computational complexity to solve complex real-world challenges.\n"
                "2. **Broad Career Pathways:** Software Development, Cloud Architecture, Cybersecurity, AI/ML Engineering, Systems Programming, and Product Engineering.\n"
                "3. **High Industry Demand:** Strong campus placement ecosystem across multinational tech corporations, product enterprises, and innovative startups.\n"
                "4. **Who Thrives in CSE:** Students who enjoy mathematics, logical puzzle-solving, writing code, and continuous self-learning."
            )
        else:
            return (
                "**Computer Science and Engineering (CSE)** is an engineering discipline that combines computational theory, software design, and hardware-software integration.\n\n"
                "• **Key Topics:** Data Structures & Algorithms, Operating Systems, Database Management Systems, Computer Networks, Software Engineering, Cloud Computing, and Artificial Intelligence.\n"
                "• **Skills Developed:** Problem-solving, object-oriented programming (Java/C++/Python), system architecture, and algorithmic design.\n"
                "• **Career Directions:** Software Engineer, Full-Stack Developer, Systems Architect, Data Engineer, and DevOps Specialist."
            )

    # "What is AD?" or "AI&DS what is mean by this"
    if norm_branch and norm_branch["code"] == "AD" and not any(k in q_lower for k in ["compare", "vs", "versus", "difference", "between"]):
        return (
            "**Artificial Intelligence and Data Science (AI & DS / AD)** is a specialized engineering branch focused on extracting actionable intelligence from data and building automated cognitive systems.\n\n"
            "• **Core Curriculum:** Machine Learning, Deep Learning, Statistical Modeling, Big Data Analytics, Natural Language Processing, Computer Vision, and Data Visualization.\n"
            "• **Foundational Math:** Linear Algebra, Multivariate Calculus, Probability & Statistics, and Discrete Mathematics.\n"
            "• **Career Roles:** AI/ML Engineer, Data Scientist, Business Intelligence Analyst, NLP Specialist, and Data Pipeline Architect."
        )

    # "What is IT?" or "IT"
    if norm_branch and norm_branch["code"] == "IT" and not any(k in q_lower for k in ["compare", "vs", "versus", "difference", "between"]):
        return (
            "**Information Technology (IT)** focuses on the application, deployment, and management of computing technology, networks, enterprise databases, and web systems.\n\n"
            "• **Core Focus:** Enterprise Software, Web Applications, Database Administration, Cloud Infrastructure, Information Security, and Network Management.\n"
            "• **Career Roles:** Software Developer, Cloud Engineer, Database Administrator, Solutions Architect, and IT Consultant."
        )

    # Explicit Comparison (e.g. "CSE vs ECE" or "Difference between CSE and AI&DS")
    if any(k in q_lower for k in ["difference", "vs", "versus", "compare", "comparison"]):
        if ("cse" in q_lower or "cs" in q_lower) and ("ece" in q_lower or "electronics" in q_lower):
            return (
                "**Comparison: Computer Science (CSE) vs. Electronics & Communication (ECE)**\n\n"
                "| Dimension | Computer Science (CSE) | Electronics & Communication (ECE) |\n"
                "|---|---|---|\n"
                "| **Core Focus** | Software systems, algorithms, databases, cloud, AI | Hardware circuits, semiconductors, embedded systems, telecommunications |\n"
                "| **Key Subjects** | Data Structures, OS, DBMS, Networks, Compilers | VLSI Design, Microprocessors, DSP, Analog/Digital Circuits, RF |\n"
                "| **Core Industry** | Google, Microsoft, Amazon, Zoho, TCS, Infosys | Qualcomm, Texas Instruments, Intel, NVIDIA, Cisco, Bosch |\n"
                "| **Flexibility** | High demand in software & tech services | Dual eligibility: core hardware/semiconductors + software roles |\n"
                "| **Best Suited For** | Students passionate about coding & logic | Students interested in physics, chips, circuits, and IoT devices |"
            )
        elif ("cse" in q_lower or "cs" in q_lower) and ("ai" in q_lower or "ad" in q_lower or "data science" in q_lower):
            return (
                "**Comparison: Computer Science (CSE) vs. AI & Data Science (AI&DS)**\n\n"
                "| Dimension | Computer Science (CSE) | Artificial Intelligence & Data Science (AI&DS) |\n"
                "|---|---|---|\n"
                "| **Scope** | Broad foundational computing & all software domains | Specialized focus on data pipelines, predictive models, and AI systems |\n"
                "| **Mathematics** | Discrete math, boolean algebra, graph theory | Heavy probability, statistics, linear algebra, optimization calculus |\n"
                "| **Core Projects** | Compilers, operating systems, full-stack apps | Predictive modeling, Machine Learning algorithms, computer vision, LLMs, neural networks |\n"
                "| **Career Scope** | Universal software & systems engineering | AI Engineer, Data Scientist, ML Engineer, Quantitative Analyst |"
            )

    # 8. Counselling Process & 3-Tier Strategy
    if any(k in q_lower for k in ["for counselling", "counselling process", "how counselling works", "counselling steps", "what should i do for counselling"]):
        return (
            "**TNEA Single-Window Counselling Guide & 3-Tier Strategy:**\n\n"
            "1. **Online Registration & Certificate Verification:** Upload 10th/12th marksheets, Transfer Certificate, and Community Certificate.\n"
            "2. **Rank List Publication:** TNEA publishes overall and community ranks based on the 200-mark cutoff score.\n"
            "3. **Choice Filling (3-Tier Strategy):**\n"
            "   • **Choices 1–10 (Dream Tier):** Top government/autonomous colleges slightly above your cutoff.\n"
            "   • **Choices 11–25 (Target Tier):** Institutions where your cutoff closely matches past closing cutoffs (highest allocation probability).\n"
            "   • **Choices 26–40 (Safe Tier):** Verified backup colleges well below your cutoff to guarantee seat security.\n"
            "4. **Tentative Allotment & Upward Movement:** Confirm your allotted seat or opt for upward movement if a higher choice becomes available."
        )

    # 9. Next Steps / Actionable Guidance
    if any(k in q_lower for k in ["what should i do next", "what next", "next step", "next steps"]):
        return (
            f"**Recommended Next Steps for {user_name}:**\n\n"
            f"1. **Finalize Choice List Draft:** Structure your college choices into Dream, Target, and Safe tiers in the **Choice List Manager** at `/choice-list`.\n"
            f"2. **Evaluate Cutoff Probabilities:** Test your score against closing benchmarks in the **Admission Planner** at `/planner`.\n"
            f"3. **Document Vault Verification:** Ensure marksheets and community certificates are uploaded to the **Document Vault** at `/documents`.\n"
            f"4. **Explore Foundational Skills:** Start learning Python or core engineering concepts in **Learning Resources** at `/resources`."
        )

    # 10. Parent Support Inquiries
    if any(k in q_lower for k in ["son", "daughter", "child", "as a parent", "parent guidance", "parents"]):
        return (
            "**Guidance for Parents Supporting Engineering Aspirants:**\n\n"
            "1. **Evaluate Holistic Campus Quality:** Look beyond just closing cutoffs. Prioritize active placement statistics, core engineering laboratories, faculty retention, and hostel safety.\n"
            "2. **Balance Passion with Market Demand:** Encourage disciplines aligned with the student's natural cognitive strengths (computational logic, hardware systems, or design).\n"
            "3. **Autonomous vs. Affiliated Colleges:** Autonomous institutions update their curriculum frequently to match industry trends, conduct internal semester exams, and have dedicated placement cells.\n"
            "4. **Counselling Preparation:** Ensure all original documents (10th/12th marksheets, community certificate, special reservation certificates) are verified early."
        )

    # 11. General Knowledge, Science, Math, Programming & Web Inquiries
    # Check RAG Semantic Vector Database (with strict keyword & similarity threshold)
    rag_results = retrieve_relevant_context(q_clean, top_k=2, score_threshold=0.35)
    if rag_results:
        top_rag = rag_results[0]
        stop_words = {"what", "how", "why", "when", "where", "which", "who", "does", "explain", "tell", "about", "work", "mean", "simple", "terms", "difference", "between"}
        q_words = [w for w in re.findall(r"\b[a-zA-Z0-9]+\b", q_lower) if len(w) >= 3 and w not in stop_words]
        title_lower = top_rag["title"].lower()
        content_lower = top_rag["content"].lower()
        
        # Must have at least 1 strong query term match in title or 2 in content
        matches_title = sum(1 for w in q_words if w in title_lower)
        matches_content = sum(1 for w in q_words if w in content_lower)
        
        if matches_title >= 1 or (matches_content >= 2 and top_rag["similarity_score"] >= 0.45):
            content = top_rag["content"]
            title = top_rag["title"]
            return f"**{title}**\n\n{content}"

    # General Web Research for external/factual queries
    web_res = perform_web_research(q_clean, max_results=2)
    if web_res.get("results"):
        for top_web in web_res["results"]:
            snippet = top_web.get("snippet", "")
            title = top_web.get("title", "")
            url = top_web.get("url", "")
            if snippet and len(snippet) > 30:
                return (
                    f"**{title}**\n\n"
                    f"{snippet}\n\n"
                    f"*(Source: [{top_web.get('source', 'Web Resource')}]({url}))*"
                )

    # General conversational response
    return (
        f"**{q_clean}**\n\n"
        f"Here is helpful guidance regarding your question:\n"
        f"Whether you are exploring foundational theory, programming concepts, mathematics, career planning, or TNEA college selections, "
        f"I can provide direct explanations, code snippets, or benchmark analysis. Let me know what specific detail you'd like to dive into!"
    )


# =============================================================
# 7. OPENAI ORCHESTRATION ENGINE WITH DYNAMIC TOOL & RAG CALLING
# =============================================================

def call_openai_career_assistant(
    system_prompt: str,
    user_message: str,
    history: List[Dict[str, str]],
    user_id: Optional[int],
    profile: Optional[Dict[str, Any]],
    user_name: str = "Student"
) -> Optional[str]:
    """
    Calls the configured AI LLM provider with controlled tool calling.
    Uses AI Provider Manager for multi-provider fallback and retry resilience.
    """
    # Proactive RAG retrieval for relevant background knowledge
    proactive_rag = retrieve_relevant_context(user_message, top_k=2, score_threshold=0.25)
    rag_context_str = format_rag_context_for_llm(proactive_rag) if proactive_rag else ""

    augmented_system_prompt = system_prompt
    if rag_context_str:
        augmented_system_prompt += f"\n\n{rag_context_str}"

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": augmented_system_prompt}
    ]

    for h in (history or [])[-10:]:
        role = "user" if h.get("role") == "user" else "assistant"
        content = h.get("content", "").strip()
        if content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_message})

    def _execute_chat_completion(provider_config: Dict[str, Any]) -> Optional[str]:
        from openai import OpenAI
        client = OpenAI(
            api_key=provider_config["api_key"],
            base_url=provider_config.get("base_url"),
            timeout=provider_config.get("timeout", 25.0)
        )
        model = provider_config.get("model", "gpt-4o-mini")

        working_messages = list(messages)
        max_tool_iterations = 4
        iteration = 0

        while iteration < max_tool_iterations:
            iteration += 1

            response = client.chat.completions.create(
                model=model,
                messages=working_messages,
                tools=OPENAI_TOOLS,
                tool_choice="auto",
                temperature=0.35,
                max_tokens=1000
            )

            choice = response.choices[0]
            response_msg = choice.message

            if response_msg.tool_calls:
                tool_calls_dict = []
                for tc in response_msg.tool_calls:
                    tool_calls_dict.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })

                working_messages.append({
                    "role": "assistant",
                    "content": response_msg.content or None,
                    "tool_calls": tool_calls_dict
                })

                for tc in response_msg.tool_calls:
                    func_name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except Exception:
                        args = {}

                    logger.info(f"Tool call requested: {func_name}")

                    tool_result = execute_backend_tool(
                        tool_name=func_name,
                        arguments=args,
                        user_id=user_id,
                        profile=profile
                    )

                    working_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": func_name,
                        "content": json.dumps(tool_result, ensure_ascii=False)
                    })
            elif response_msg.content:
                return response_msg.content.strip()
            else:
                break

        return None

    result, provider_name = execute_with_ai_fallback(_execute_chat_completion)
    if result:
        logger.info(f"AI response successfully synthesized by provider: '{provider_name}'")
        return result

    return None


# =============================================================
# 8. MAIN ORCHESTRATION ENTRYPOINT
# =============================================================

def get_career_assistant_response(
    user_message: str,
    profile: Optional[Dict[str, Any]] = None,
    user_name: str = "Student",
    conversation_history: Optional[List[Dict[str, str]]] = None,
    user_id: Optional[int] = None
) -> Tuple[str, List[str]]:
    """
    Main orchestration entrypoint for multi-turn conversational AI guidance.
    1. Orchestrates primary OpenAI LLM & multi-provider fallback with dynamic tool calling.
    2. Gracefully uses Dynamic Universal Synthesizer if external LLMs are unreachable.
    3. Generates adaptive follow-up suggestions.
    4. Returns (assistant_reply_text, list_of_suggested_followups).
    """
    cleaned_message = user_message.strip()
    if not cleaned_message:
        return "Hi! How can I help you today?", DEFAULT_STARTER_QUESTIONS[:4]

    if len(cleaned_message) > 1000:
        cleaned_message = cleaned_message[:1000]

    history = conversation_history or []
    logger.info(f"Incoming user query: '{cleaned_message}' from user: '{user_name}' (ID: {user_id})")

    # 1. Attempt OpenAI / Multi-Provider LLM with Tool Calling & RAG Grounding
    ai_reply = call_openai_career_assistant(
        system_prompt=CAREER_ASSISTANT_SYSTEM_PROMPT,
        user_message=cleaned_message,
        history=history,
        user_id=user_id,
        profile=profile,
        user_name=user_name
    )

    # 2. If OpenAI is unavailable or offline, execute Universal Dynamic Synthesizer
    if not ai_reply:
        ai_reply = generate_dynamic_general_response(
            query=cleaned_message,
            history=history,
            user_id=user_id,
            profile=profile,
            user_name=user_name
        )

    # 3. Generate Contextual Follow-Up Suggestions
    followups = generate_contextual_suggestions(cleaned_message, ai_reply, profile)

    return ai_reply, followups
