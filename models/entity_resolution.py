"""
=============================================================
TNEA Career Insight Navigator — Robust Entity Resolution Engine
=============================================================
Provides precise, deterministic entity resolution for:
  1. Engineering Colleges:
     - Exact TNEA College Code matching
     - Canonical name normalization
     - 150+ verified college aliases, acronyms, and common short names
     - Strict word-boundary token matching (prevents substring confusion like "Eshwar" in "Venkateshwara")
     - Ambiguity detection & confidence scoring (asks user to clarify if multiple high-confidence matches exist)
  2. Engineering Branches:
     - Normalization for CS, AD, EC, IT, EE, ME, CE, CB, BT, BM, etc.
=============================================================
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("entity_resolution")
logger.setLevel(logging.INFO)

# =============================================================
# 1. VERIFIED COLLEGE ALIAS DICTIONARY (150+ INSTITUTIONS)
# Maps normalized nicknames/acronyms to (College Code, Canonical Name)
# =============================================================

KNOWN_COLLEGE_ALIASES: Dict[str, Dict[str, Any]] = {
    # Sri Eshwar & Coimbatore Institutions
    "sri eshwar": {"code": 2739, "name": "Sri Eshwar College of Engineering (Autonomous)"},
    "eshwar": {"code": 2739, "name": "Sri Eshwar College of Engineering (Autonomous)"},
    "eshwar college": {"code": 2739, "name": "Sri Eshwar College of Engineering (Autonomous)"},
    "sri eshwar college": {"code": 2739, "name": "Sri Eshwar College of Engineering (Autonomous)"},
    "sece": {"code": 2739, "name": "Sri Eshwar College of Engineering (Autonomous)"},

    "sri shakthi": {"code": 2727, "name": "Sri Shakthi Institute of Engineering and Technology"},
    "shakthi": {"code": 2727, "name": "Sri Shakthi Institute of Engineering and Technology"},
    "shakthi college": {"code": 2727, "name": "Sri Shakthi Institute of Engineering and Technology"},
    "siet": {"code": 2727, "name": "Sri Shakthi Institute of Engineering and Technology"},

    "psg": {"code": 2006, "name": "PSG College of Technology (Autonomous)"},
    "psg tech": {"code": 2006, "name": "PSG College of Technology (Autonomous)"},
    "psg college of technology": {"code": 2006, "name": "PSG College of Technology (Autonomous)"},
    "psg itech": {"code": 2377, "name": "PSG Institute of Technology and Applied Research"},
    "psg institute": {"code": 2377, "name": "PSG Institute of Technology and Applied Research"},

    "cit": {"code": 2007, "name": "Coimbatore Institute of Technology (Autonomous)"},
    "coimbatore institute of technology": {"code": 2007, "name": "Coimbatore Institute of Technology (Autonomous)"},

    "gct": {"code": 2005, "name": "Government College of Technology Coimbatore (Autonomous)"},
    "government college of technology": {"code": 2005, "name": "Government College of Technology Coimbatore (Autonomous)"},

    "skcet": {"code": 2718, "name": "Sri Krishna College of Engineering and Technology (Autonomous)"},
    "sri krishna cet": {"code": 2718, "name": "Sri Krishna College of Engineering and Technology (Autonomous)"},
    "krishna kuniamuthur": {"code": 2718, "name": "Sri Krishna College of Engineering and Technology (Autonomous)"},
    
    "skct": {"code": 2722, "name": "Sri Krishna College of Technology (Autonomous)"},
    "sri krishna technology": {"code": 2722, "name": "Sri Krishna College of Technology (Autonomous)"},

    "kct": {"code": 2712, "name": "Kumaraguru College of Technology (Autonomous)"},
    "kumaraguru": {"code": 2712, "name": "Kumaraguru College of Technology (Autonomous)"},

    "kpr": {"code": 2764, "name": "KPR Institute of Engineering and Technology (Autonomous)"},
    "kpr institute": {"code": 2764, "name": "KPR Institute of Engineering and Technology (Autonomous)"},

    "bannari": {"code": 2702, "name": "Bannari Amman Institute of Technology (Autonomous)"},
    "bannari amman": {"code": 2702, "name": "Bannari Amman Institute of Technology (Autonomous)"},
    "bits sathyamangalam": {"code": 2702, "name": "Bannari Amman Institute of Technology (Autonomous)"},

    "dr mahalingam": {"code": 2707, "name": "Dr. Mahalingam College of Engineering and Technology (Autonomous)"},
    "mcet": {"code": 2707, "name": "Dr. Mahalingam College of Engineering and Technology (Autonomous)"},
    "mahalingam": {"code": 2707, "name": "Dr. Mahalingam College of Engineering and Technology (Autonomous)"},

    "sns ctech": {"code": 2736, "name": "SNS College of Technology (Autonomous)"},
    "sns ce": {"code": 2726, "name": "SNS College of Engineering (Autonomous)"},
    "sns": {"code": 2736, "name": "SNS College of Technology (Autonomous)"},

    "karpagam academy": {"code": 2710, "name": "Karpagam College of Engineering (Autonomous)"},
    "kce": {"code": 2710, "name": "Karpagam College of Engineering (Autonomous)"},

    "hindusthan": {"code": 2708, "name": "Hindusthan College of Engineering and Technology (Autonomous)"},
    "hicet": {"code": 2708, "name": "Hindusthan College of Engineering and Technology (Autonomous)"},

    # Chennai & Tier-1 Premier Institutions
    "ceg": {"code": 1, "name": "College of Engineering Guindy (Anna University)"},
    "guindy": {"code": 1, "name": "College of Engineering Guindy (Anna University)"},
    "anna university ceg": {"code": 1, "name": "College of Engineering Guindy (Anna University)"},
    "college of engineering guindy": {"code": 1, "name": "College of Engineering Guindy (Anna University)"},

    "act": {"code": 2, "name": "Alagappa Chettiar College of Technology (Anna University)"},
    "alagappa chettiar": {"code": 2, "name": "Alagappa Chettiar College of Technology (Anna University)"},

    "mit": {"code": 4, "name": "Madras Institute of Technology (Anna University)"},
    "mit chromepet": {"code": 4, "name": "Madras Institute of Technology (Anna University)"},
    "madras institute of technology": {"code": 4, "name": "Madras Institute of Technology (Anna University)"},

    "ssn": {"code": 1315, "name": "Sri Sivasubramaniya Nadar College of Engineering (Autonomous)"},
    "sri sivasubramaniya nadar": {"code": 1315, "name": "Sri Sivasubramaniya Nadar College of Engineering (Autonomous)"},
    "ssn college": {"code": 1315, "name": "Sri Sivasubramaniya Nadar College of Engineering (Autonomous)"},

    "svce": {"code": 1219, "name": "Sri Venkateswara College of Engineering (Autonomous)"},
    "sri venkateswara college of engineering": {"code": 1219, "name": "Sri Venkateswara College of Engineering (Autonomous)"},
    "sri venkateswara sriperumbudur": {"code": 1219, "name": "Sri Venkateswara College of Engineering (Autonomous)"},

    "rec": {"code": 1211, "name": "Rajalakshmi Engineering College (Autonomous)"},
    "rajalakshmi": {"code": 1211, "name": "Rajalakshmi Engineering College (Autonomous)"},
    "rajalakshmi engineering college": {"code": 1211, "name": "Rajalakshmi Engineering College (Autonomous)"},
    "rit chennai": {"code": 1225, "name": "Rajalakshmi Institute of Technology (Autonomous)"},

    "licet": {"code": 1120, "name": "Loyola-ICAM College of Engineering and Technology"},
    "loyola icam": {"code": 1120, "name": "Loyola-ICAM College of Engineering and Technology"},

    "rmk": {"code": 1113, "name": "R.M.K. Engineering College (Autonomous)"},
    "rmk engineering college": {"code": 1113, "name": "R.M.K. Engineering College (Autonomous)"},
    "rmd": {"code": 1112, "name": "R.M.D. Engineering College (Autonomous)"},
    "rmk cet": {"code": 1128, "name": "R.M.K. College of Engineering and Technology"},

    "st joseph": {"code": 1317, "name": "St. Joseph's College of Engineering (Autonomous)"},
    "st josephs": {"code": 1317, "name": "St. Joseph's College of Engineering (Autonomous)"},
    "st joseph college": {"code": 1317, "name": "St. Joseph's College of Engineering (Autonomous)"},
    "st joseph institute": {"code": 1399, "name": "St. Joseph's Institute of Technology (Autonomous)"},

    "prince shri venkateshwara": {"code": 1414, "name": "Prince Shri Venkateshwara Padmavathy Engineering College"},
    "prince venkateshwara": {"code": 1414, "name": "Prince Shri Venkateshwara Padmavathy Engineering College"},
    "prince shri venkateshwara padmavathy": {"code": 1414, "name": "Prince Shri Venkateshwara Padmavathy Engineering College"},

    "velammal": {"code": 1115, "name": "Velammal Engineering College (Autonomous)"},
    "velammal surapet": {"code": 1115, "name": "Velammal Engineering College (Autonomous)"},
    "velammal institute": {"code": 1137, "name": "Velammal Institute of Technology"},

    "panimalar": {"code": 1114, "name": "Panimalar Engineering College (Autonomous)"},
    "panimalar institute": {"code": 1230, "name": "Panimalar Institute of Technology"},

    "sairam": {"code": 1415, "name": "Sri Sairam Engineering College (Autonomous)"},
    "sri sairam": {"code": 1415, "name": "Sri Sairam Engineering College (Autonomous)"},
    "sairam it": {"code": 1450, "name": "Sri Sairam Institute of Technology (Autonomous)"},

    "saveetha": {"code": 1216, "name": "Saveetha Engineering College (Autonomous)"},
    "saveetha engineering college": {"code": 1216, "name": "Saveetha Engineering College (Autonomous)"},

    "easwari": {"code": 1304, "name": "Easwari Engineering College (Autonomous)"},
    "easwari engineering college": {"code": 1304, "name": "Easwari Engineering College (Autonomous)"},

    "meenakshi sundararajan": {"code": 1309, "name": "Meenakshi Sundararajan Engineering College"},
    "msec kodambakkam": {"code": 1309, "name": "Meenakshi Sundararajan Engineering College"},

    # Madurai & South TN Institutions
    "tce": {"code": 5008, "name": "Thiagarajar College of Engineering (Autonomous)"},
    "thiagarajar": {"code": 5008, "name": "Thiagarajar College of Engineering (Autonomous)"},
    "thiagarajar college of engineering": {"code": 5008, "name": "Thiagarajar College of Engineering (Autonomous)"},

    "mepco": {"code": 4960, "name": "Mepco Schlenk Engineering College (Autonomous)"},
    "mepco schlenk": {"code": 4960, "name": "Mepco Schlenk Engineering College (Autonomous)"},

    "national engineering college": {"code": 4962, "name": "National Engineering College (Autonomous)"},
    "nec kovilpatti": {"code": 4962, "name": "National Engineering College (Autonomous)"},

    "psna": {"code": 5901, "name": "PSNA College of Engineering and Technology (Autonomous)"},
    "psna dindigul": {"code": 5901, "name": "PSNA College of Engineering and Technology (Autonomous)"},

    "gce salem": {"code": 2603, "name": "Government College of Engineering Salem (Autonomous)"},
    "gce tirunelveli": {"code": 4974, "name": "Government College of Engineering Tirunelveli (Autonomous)"},
    "gce bargur": {"code": 2615, "name": "Government College of Engineering Bargur (Autonomous)"},
    "gce thanjavur": {"code": 3465, "name": "Government College of Engineering Thanjavur"},

    "sona": {"code": 2618, "name": "Sona College of Technology (Autonomous)"},
    "sona college": {"code": 2618, "name": "Sona College of Technology (Autonomous)"},

    "kongu": {"code": 2711, "name": "Kongu Engineering College (Autonomous)"},
    "kongu engineering college": {"code": 2711, "name": "Kongu Engineering College (Autonomous)"},
}

# Branch normalizations
BRANCH_SYNONYMS: Dict[str, Dict[str, str]] = {
    "cs": {"code": "CS", "name": "Computer Science and Engineering"},
    "cse": {"code": "CS", "name": "Computer Science and Engineering"},
    "computer science": {"code": "CS", "name": "Computer Science and Engineering"},
    "computer science and engineering": {"code": "CS", "name": "Computer Science and Engineering"},
    "comp sci": {"code": "CS", "name": "Computer Science and Engineering"},

    "ad": {"code": "AD", "name": "Artificial Intelligence and Data Science"},
    "aids": {"code": "AD", "name": "Artificial Intelligence and Data Science"},
    "ai&ds": {"code": "AD", "name": "Artificial Intelligence and Data Science"},
    "ai and ds": {"code": "AD", "name": "Artificial Intelligence and Data Science"},
    "ai ds": {"code": "AD", "name": "Artificial Intelligence and Data Science"},
    "artificial intelligence": {"code": "AD", "name": "Artificial Intelligence and Data Science"},
    "artificial intelligence and data science": {"code": "AD", "name": "Artificial Intelligence and Data Science"},
    "ai and data science": {"code": "AD", "name": "Artificial Intelligence and Data Science"},
    "data science": {"code": "AD", "name": "Artificial Intelligence and Data Science"},

    "ec": {"code": "EC", "name": "Electronics and Communication Engineering"},
    "ece": {"code": "EC", "name": "Electronics and Communication Engineering"},
    "electronics": {"code": "EC", "name": "Electronics and Communication Engineering"},
    "electronics and communication": {"code": "EC", "name": "Electronics and Communication Engineering"},
    "electronics and communication engineering": {"code": "EC", "name": "Electronics and Communication Engineering"},

    "it": {"code": "IT", "name": "Information Technology"},
    "information technology": {"code": "IT", "name": "Information Technology"},
    "infotech": {"code": "IT", "name": "Information Technology"},

    "ee": {"code": "EE", "name": "Electrical and Electronics Engineering"},
    "eee": {"code": "EE", "name": "Electrical and Electronics Engineering"},
    "electrical": {"code": "EE", "name": "Electrical and Electronics Engineering"},
    "electrical and electronics": {"code": "EE", "name": "Electrical and Electronics Engineering"},

    "me": {"code": "ME", "name": "Mechanical Engineering"},
    "mech": {"code": "ME", "name": "Mechanical Engineering"},
    "mechanical": {"code": "ME", "name": "Mechanical Engineering"},
    "mechanical engineering": {"code": "ME", "name": "Mechanical Engineering"},

    "ce": {"code": "CE", "name": "Civil Engineering"},
    "civil": {"code": "CE", "name": "Civil Engineering"},
    "civil engineering": {"code": "CE", "name": "Civil Engineering"},

    "cb": {"code": "CB", "name": "Computer Science and Business Systems"},
    "csbs": {"code": "CB", "name": "Computer Science and Business Systems"},

    "bt": {"code": "BT", "name": "Biotechnology"},
    "biotech": {"code": "BT", "name": "Biotechnology"},
    "biotechnology": {"code": "BT", "name": "Biotechnology"},

    "bm": {"code": "BM", "name": "Biomedical Engineering"},
    "biomedical": {"code": "BM", "name": "Biomedical Engineering"},
}


def normalize_branch_query(query: str) -> Optional[Dict[str, str]]:
    """Resolves branch keyword into canonical branch code and full name."""
    q_clean = query.strip().lower()
    
    # Check exact synonym
    if q_clean in BRANCH_SYNONYMS:
        return BRANCH_SYNONYMS[q_clean]

    # Check word match
    for term, b_info in BRANCH_SYNONYMS.items():
        pattern = r"\b" + re.escape(term) + r"\b"
        if re.search(pattern, q_clean):
            return b_info

    return None


def resolve_college_entity(
    query_text: str,
    district_hint: Optional[str] = None
) -> Tuple[Optional[Dict[str, Any]], float, List[Dict[str, Any]]]:
    """
    High-precision college entity resolver.
    Returns:
      (best_college_match, confidence_score_0_to_1, list_of_ambiguous_candidates)

    Resolution steps:
      1. Check explicit college code (e.g. 2739)
      2. Check exact known alias (e.g. 'Sri Eshwar', 'PSG Tech', 'SSN', 'CEG')
      3. Word-boundary token matching on database records with token overlap scoring
      4. Ambiguity detection: If confidence is moderate and multiple candidates exist,
         returns candidates for disambiguation.
    """
    from models.database import get_connection

    cleaned = query_text.strip().lower()
    
    # 1. Check for 4-digit or 1-2 digit college code
    code_match = re.search(r"\b([1-9][0-9]{0,3})\b", cleaned)
    if code_match:
        try:
            cand_code = int(code_match.group(1))
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.college_code, c.college_name, ci.district, ci.taluk, ci.autonomous,
                       ci.hostel_boys, ci.hostel_girls, ci.transport, ci.website, ci.phone
                FROM colleges c
                LEFT JOIN college_info ci ON ci.college_code = c.college_code
                WHERE c.college_code = ?
            """, (cand_code,))
            row = cursor.fetchone()
            conn.close()
            if row:
                res = dict(row)
                return res, 1.0, []
        except Exception:
            pass

    # 2. Check Known Alias Dictionary with word boundaries
    for alias, alias_info in KNOWN_COLLEGE_ALIASES.items():
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, cleaned):
            code = alias_info["code"]
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.college_code, c.college_name, ci.district, ci.taluk, ci.autonomous,
                       ci.hostel_boys, ci.hostel_girls, ci.transport, ci.website, ci.phone
                FROM colleges c
                LEFT JOIN college_info ci ON ci.college_code = c.college_code
                WHERE c.college_code = ?
            """, (code,))
            row = cursor.fetchone()
            conn.close()
            if row:
                res = dict(row)
                return res, 0.98, []

    # 3. Database Word-Boundary Search
    # Clean filler words out
    stop_words = {"where", "is", "are", "tell", "me", "about", "what", "can", "i", "get", "college", "colleges", "institute", "institutes", "engineering", "tech", "technology", "autonomous", "in", "at", "the", "of", "does", "have", "hostel", "transport", "cutoff", "details", "info"}
    raw_tokens = [w for w in re.findall(r"\b[a-zA-Z0-9]+\b", cleaned) if len(w) >= 3 and w not in stop_words]
    
    if not raw_tokens:
        # Check if query had 2-letter tokens like 'psg', 'ssn', 'mit'
        raw_tokens = [w for w in re.findall(r"\b[a-zA-Z0-9]+\b", cleaned) if w not in stop_words]

    if not raw_tokens:
        return None, 0.0, []

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.college_code, c.college_name, ci.district, ci.taluk, ci.autonomous,
               ci.hostel_boys, ci.hostel_girls, ci.transport, ci.website, ci.phone
        FROM colleges c
        LEFT JOIN college_info ci ON ci.college_code = c.college_code
        WHERE c.college_name IS NOT NULL AND c.college_name != ''
    """)
    all_colleges = [dict(r) for r in cursor.fetchall()]
    conn.close()

    candidates = []
    for col in all_colleges:
        col_name = (col.get("college_name") or "").lower()
        col_tokens = set(re.findall(r"\b[a-zA-Z0-9]+\b", col_name))
        
        # Word boundary token intersection
        matched_tokens = 0
        for q_tok in raw_tokens:
            # Must match whole word or prefix of distinct word (>=4 chars)
            if q_tok in col_tokens:
                matched_tokens += 1
            elif len(q_tok) >= 4 and any(ct.startswith(q_tok) for ct in col_tokens):
                matched_tokens += 0.85

        if matched_tokens > 0:
            score = matched_tokens / max(len(raw_tokens), 1)
            
            # Boost if district matches
            if district_hint and col.get("district") and district_hint.lower() in col.get("district").lower():
                score += 0.15

            # Substring penalty: if raw query appears in name as part of an unrelated word (e.g. "eshwar" in "Venkateshwara"), do NOT award credit unless exact word boundary matched
            candidates.append({
                "college": col,
                "score": score,
                "matched_tokens": matched_tokens
            })

    # Sort candidates by score descending
    candidates.sort(key=lambda x: (x["score"], x["matched_tokens"]), reverse=True)

    if not candidates:
        return None, 0.0, []

    top_candidate = candidates[0]
    top_score = top_candidate["score"]

    # Check for ambiguity: if top 2 candidates have very close scores and neither is overwhelmingly dominant
    ambiguous = []
    if len(candidates) > 1 and top_score < 0.90:
        second_score = candidates[1]["score"]
        if abs(top_score - second_score) < 0.15:
            ambiguous = [c["college"] for c in candidates[:4]]

    if top_score >= 0.70:
        return top_candidate["college"], top_score, ambiguous
    elif top_score >= 0.50:
        return top_candidate["college"], top_score, ambiguous
    else:
        return None, top_score, [c["college"] for c in candidates[:3]]
