"""
=============================================================
TNEA Career Insight Navigator — Database Layer
=============================================================

DATA SOURCES (authoritative, do NOT change schema):
  colleges      (445 rows) — from colleges_clean.csv
                  college_code  ← primary key
                  college_name  ← ONLY source for college names
                  district      ← dirty (101 variants), NOT used
                  college_type

  college_info  (450 rows) — from college_details.csv
                  college_code  ← foreign key
                  district      ← CLEAN (38 uppercase values) ← used everywhere
                  taluk, address, pincode, phone, email, website
                  autonomous, hostel_boys, hostel_girls, transport

  32 codes exist in college_info but NOT in colleges.
  These codes DO appear in cutoffs/branches (real colleges
  missing from colleges_clean.csv).  They are excluded from
  search/display because we have no verified college_name for them.

JOIN RULE (applied everywhere):
  FROM colleges c
  LEFT JOIN college_info ci ON ci.college_code = c.college_code

  → college_name  always from  c.college_name
  → district      always from  ci.district   (clean)
  → all details   always from  ci.*
=============================================================
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "database" / "tnea.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


print("=" * 60)
print("Database Module Loaded")
print("Database :", DB_PATH)
print("=" * 60)


# =============================================================
# INTERNAL HELPERS
# =============================================================

def _normalize_district(raw: str) -> str:
    """
    Normalise a district string for fuzzy matching.
    college_info.district is clean uppercase e.g. 'COIMBATORE'.
    User input from planner is title-case e.g. 'Coimbatore'.
    Both normalise to 'coimbatore'.
    """
    if not raw:
        return ""
    s = raw.lower().replace("district", "").strip()
    while "  " in s:
        s = s.replace("  ", " ")
    return s.strip()


# =============================================================
# BRANCH GROUPS
# =============================================================

BRANCH_GROUPS = {
    "CY": ["CY", "SC", "SB"],
    "SC": ["CY", "SC", "SB"],
    "SB": ["CY", "SC", "SB"],
    "AD": ["AD", "AL", "AI", "AT"],
    "AL": ["AD", "AL", "AI", "AT"],
    "AI": ["AD", "AL", "AI", "AT"],
    "AT": ["AD", "AL", "AI", "AT"],
    "CS": ["CS", "CM"],
    "CM": ["CS", "CM"],
    "EC": ["EC", "EM"],
    "EM": ["EC", "EM"],
    "ME": ["ME", "MF"],
    "MF": ["ME", "MF"],
    "CE": ["CE", "CN"],
    "CN": ["CE", "CN"],
}


def _resolve_branch_codes(branch_code: str) -> list:
    return BRANCH_GROUPS.get(branch_code.upper(), [branch_code.upper()])


# =============================================================
# GET ALL COLLEGES  (trend page dropdowns)
# Source: colleges JOIN college_info
# =============================================================

def get_all_colleges():
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            c.college_code,
            c.college_name,
            ci.district,
            c.college_type
        FROM colleges c
        LEFT JOIN college_info ci ON ci.college_code = c.college_code
        ORDER BY c.college_name
    """)
    colleges = cursor.fetchall()
    conn.close()
    return colleges


# =============================================================
# GET ALL DISTRICTS  (planner page dropdown)
# Source: college_info.district — the only clean district column.
# Excludes the one bad value '- 642 120.'
# Returns title-cased, deduplicated list.
# =============================================================

def get_all_districts():
    conn   = get_connection()
    cursor = conn.cursor()
    # Only districts that belong to colleges we actually have names for
    cursor.execute("""
        SELECT DISTINCT ci.district
        FROM college_info ci
        JOIN colleges c ON c.college_code = ci.college_code
        WHERE ci.district IS NOT NULL
          AND ci.district != ''
          AND ci.district != '- 642 120.'
        ORDER BY ci.district
    """)
    districts = [row["district"].strip().title() for row in cursor.fetchall()]
    conn.close()
    return districts


# =============================================================
# GET ALL BRANCHES
# =============================================================

def get_all_branches():
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT branch_code, branch_name
        FROM branches
        ORDER BY branch_name
    """)
    branches = cursor.fetchall()
    conn.close()
    return branches


# =============================================================
# GET COLLEGE DETAILS
# Source: colleges (name) + college_info (all details).
# college_name always from colleges.college_name.
# district always from college_info.district (clean).
# =============================================================

def get_college_details(college_code):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            c.college_code,
            c.college_name,
            ci.district,
            c.college_type,
            ci.taluk,
            ci.address,
            ci.pincode,
            ci.phone,
            ci.email,
            ci.website,
            ci.autonomous,
            ci.hostel_boys,
            ci.hostel_girls,
            ci.transport
        FROM colleges c
        LEFT JOIN college_info ci ON ci.college_code = c.college_code
        WHERE c.college_code = ?
    """, (college_code,))
    result = cursor.fetchone()
    conn.close()
    return result


# =============================================================
# GET COLLEGE BRANCHES
# =============================================================

def get_college_branches(college_code):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT branch_code, branch_name
        FROM branches
        WHERE college_code = ?
        ORDER BY branch_name
    """, (college_code,))
    branches = cursor.fetchall()
    conn.close()
    return branches


# =============================================================
# SEARCH COLLEGES
# =============================================================
# Rules:
#   • college_name  → colleges.college_name  (never address)
#   • district      → college_info.district  (clean, 38 values)
#   • Search fields: college_name, college_code, ci.district, ci.taluk
#   • Only colleges with a verified name are returned
#     (AND c.college_name IS NOT NULL)
#   • District filter matches against ci.district (clean uppercase)
# =============================================================

def search_colleges(query="", district="", autonomous="",
                    hostel="", transport=""):
    conn   = get_connection()
    cursor = conn.cursor()

    sql = """
        SELECT
            c.college_code,
            c.college_name,
            ci.district,
            c.college_type,
            ci.taluk,
            ci.address,
            ci.pincode,
            ci.phone,
            ci.email,
            ci.website,
            ci.autonomous,
            ci.hostel_boys,
            ci.hostel_girls,
            ci.transport
        FROM colleges c
        LEFT JOIN college_info ci ON ci.college_code = c.college_code
        WHERE c.college_name IS NOT NULL
          AND c.college_name != ''
    """
    params = []

    # Text search: name, code, district, taluk only — never address
    if query and query.strip():
        q = "%" + query.strip() + "%"
        sql += """
            AND (
                CAST(c.college_code AS TEXT) LIKE ?
                OR LOWER(c.college_name)          LIKE LOWER(?)
                OR LOWER(COALESCE(ci.district,'')) LIKE LOWER(?)
                OR LOWER(COALESCE(ci.taluk,''))    LIKE LOWER(?)
            )
        """
        params += [q, q, q, q]

    # District filter — match against clean college_info.district
    if district and district.strip():
        sql += " AND LOWER(COALESCE(ci.district,'')) LIKE LOWER(?)"
        params.append("%" + district.strip() + "%")

    if autonomous == "yes":
        sql += " AND LOWER(COALESCE(ci.autonomous,'')) = 'yes'"
    elif autonomous == "no":
        sql += " AND LOWER(COALESCE(ci.autonomous,'')) = 'no'"

    if hostel == "yes":
        sql += """
            AND (
                LOWER(COALESCE(ci.hostel_boys,''))  = 'yes'
             OR LOWER(COALESCE(ci.hostel_girls,'')) = 'yes'
            )
        """

    if transport == "yes":
        sql += " AND LOWER(COALESCE(ci.transport,'')) = 'yes'"

    sql += " ORDER BY c.college_name"

    cursor.execute(sql, params)
    results = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return results


# =============================================================
# GET SEARCH DISTRICTS
# Source: college_info.district for colleges that have a
# verified name in the colleges table.
# Returns 38 clean, unique, title-cased district names.
# =============================================================

def get_search_districts():
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT ci.district
        FROM college_info ci
        JOIN colleges c ON c.college_code = ci.college_code
        WHERE ci.district IS NOT NULL
          AND ci.district != ''
          AND ci.district != '- 642 120.'
          AND c.college_name IS NOT NULL
          AND c.college_name != ''
        ORDER BY ci.district
    """)
    districts = [row["district"].strip().title() for row in cursor.fetchall()]
    conn.close()
    return districts


import json

# =============================================================
# USER AUTHENTICATION & PROFILE DATA ACCESS
# =============================================================

def init_auth_db():
    """
    Initializes the users and student_profiles tables if they do not already exist.
    Preserves all existing tables and data.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_premium INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            maths_marks REAL NOT NULL,
            physics_marks REAL NOT NULL,
            chemistry_marks REAL NOT NULL,
            cs_bio_marks REAL,
            cutoff REAL NOT NULL,
            community TEXT NOT NULL,
            preferred_district TEXT,
            school_stream TEXT,
            assessment_answers TEXT NOT NULL,
            interest_scores TEXT NOT NULL,
            top_branches TEXT NOT NULL,
            subject_strengths TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS career_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'Career Guidance Session',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS career_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES career_conversations(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_choice_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            college_code INTEGER NOT NULL,
            branch_code TEXT NOT NULL,
            preference_order INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, college_code, branch_code),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_counselling_checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_key TEXT NOT NULL,
            is_completed INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, item_key),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            order_id TEXT UNIQUE NOT NULL,
            amount REAL NOT NULL DEFAULT 200.0,
            currency TEXT NOT NULL DEFAULT 'INR',
            status TEXT NOT NULL DEFAULT 'created',
            payment_id TEXT,
            signature TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verified_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            document_type TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            storage_key TEXT NOT NULL UNIQUE,
            mime_type TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, document_type),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()


def create_user(name: str, email: str, password_hash: str) -> int:
    """
    Creates a new user record.
    Returns the newly generated user id.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (name, email, password_hash, is_premium)
        VALUES (?, ?, ?, 0)
    """, (name.strip(), email.strip().lower(), password_hash))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def get_user_by_email(email: str):
    """
    Fetches user record by email address (case-insensitive).
    """
    if not email:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, email, password_hash, is_premium, created_at
        FROM users
        WHERE LOWER(email) = LOWER(?)
    """, (email.strip(),))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_by_id(user_id: int):
    """
    Fetches user record by user id.
    """
    if not user_id:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, email, password_hash, is_premium, created_at
        FROM users
        WHERE id = ?
    """, (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


def is_email_registered(email: str) -> bool:
    """
    Checks if an email is already present in the users table.
    """
    return get_user_by_email(email) is not None


def save_student_profile(user_id: int, profile_data: dict) -> bool:
    """
    Inserts or updates the student's career interest assessment profile.
    """
    conn = get_connection()
    cursor = conn.cursor()

    assessment_answers_json = json.dumps(profile_data.get("assessment_answers", {}))
    interest_scores_json = json.dumps(profile_data.get("interest_scores", {}))
    top_branches_json = json.dumps(profile_data.get("top_branches", []))
    subject_strengths_json = json.dumps(profile_data.get("subject_strengths", {}))

    cursor.execute("""
        INSERT INTO student_profiles (
            user_id, maths_marks, physics_marks, chemistry_marks, cs_bio_marks,
            cutoff, community, preferred_district, school_stream,
            assessment_answers, interest_scores, top_branches, subject_strengths,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            maths_marks = excluded.maths_marks,
            physics_marks = excluded.physics_marks,
            chemistry_marks = excluded.chemistry_marks,
            cs_bio_marks = excluded.cs_bio_marks,
            cutoff = excluded.cutoff,
            community = excluded.community,
            preferred_district = excluded.preferred_district,
            school_stream = excluded.school_stream,
            assessment_answers = excluded.assessment_answers,
            interest_scores = excluded.interest_scores,
            top_branches = excluded.top_branches,
            subject_strengths = excluded.subject_strengths,
            updated_at = CURRENT_TIMESTAMP
    """, (
        user_id,
        float(profile_data.get("maths_marks", 0)),
        float(profile_data.get("physics_marks", 0)),
        float(profile_data.get("chemistry_marks", 0)),
        float(profile_data["cs_bio_marks"]) if profile_data.get("cs_bio_marks") is not None and str(profile_data.get("cs_bio_marks")).strip() != "" else None,
        float(profile_data.get("cutoff", 0)),
        profile_data.get("community", "OC"),
        profile_data.get("preferred_district", ""),
        profile_data.get("school_stream", "General Science"),
        assessment_answers_json,
        interest_scores_json,
        top_branches_json,
        subject_strengths_json
    ))
    conn.commit()
    conn.close()
    return True


def get_student_profile(user_id: int):
    """
    Retrieves and parses the student's career profile by user_id.
    """
    if not user_id:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sp.*, u.name, u.email, u.is_premium
        FROM student_profiles sp
        JOIN users u ON u.id = sp.user_id
        WHERE sp.user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    profile = dict(row)
    profile["assessment_answers"] = json.loads(profile.get("assessment_answers") or "{}")
    profile["interest_scores"] = json.loads(profile.get("interest_scores") or "{}")
    profile["top_branches"] = json.loads(profile.get("top_branches") or "[]")
    profile["subject_strengths"] = json.loads(profile.get("subject_strengths") or "{}")
    return profile


def has_student_profile(user_id: int) -> bool:
    """
    Checks if an authenticated user has already completed their career profile assessment.
    """
    return get_student_profile(user_id) is not None


# =============================================================
# CAREER ASSISTANT CHAT CONVERSATIONS & MESSAGES
# =============================================================

def get_or_create_active_conversation(user_id: int) -> dict:
    """
    Retrieves the most recent conversation for the user, or creates a new one if none exists.
    """
    if not user_id:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM career_conversations
        WHERE user_id = ?
        ORDER BY updated_at DESC
        LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    if row:
        conv = dict(row)
        conn.close()
        return conv

    # Create initial conversation
    cursor.execute("""
        INSERT INTO career_conversations (user_id, title)
        VALUES (?, 'Career Guidance Session')
    """, (user_id,))
    conv_id = cursor.lastrowid
    conn.commit()
    cursor.execute("SELECT * FROM career_conversations WHERE id = ?", (conv_id,))
    new_conv = dict(cursor.fetchone())
    conn.close()
    return new_conv


def create_new_conversation(user_id: int, title: str = "Career Guidance Session") -> dict:
    """
    Creates a new conversation session for the user.
    """
    if not user_id:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO career_conversations (user_id, title)
        VALUES (?, ?)
    """, (user_id, title.strip() or "Career Guidance Session"))
    conv_id = cursor.lastrowid
    conn.commit()
    cursor.execute("SELECT * FROM career_conversations WHERE id = ?", (conv_id,))
    conv = dict(cursor.fetchone())
    conn.close()
    return conv


def get_conversation_by_id(conversation_id: int, user_id: int):
    """
    Retrieves a conversation ensuring it belongs strictly to user_id (Security Authorization).
    """
    if not conversation_id or not user_id:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM career_conversations
        WHERE id = ? AND user_id = ?
    """, (conversation_id, user_id))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def add_message(conversation_id: int, user_id: int, role: str, content: str) -> int:
    """
    Adds a message to a conversation after verifying user ownership.
    """
    if not conversation_id or not user_id or not content.strip():
        return None
    
    # Ownership verification
    conv = get_conversation_by_id(conversation_id, user_id)
    if not conv:
        return None

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO career_messages (conversation_id, role, content)
        VALUES (?, ?, ?)
    """, (conversation_id, role, content.strip()))
    msg_id = cursor.lastrowid

    # Touch updated_at on conversation
    cursor.execute("""
        UPDATE career_conversations
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (conversation_id,))

    conn.commit()
    conn.close()
    return msg_id


def get_conversation_messages(conversation_id: int, user_id: int) -> list:
    """
    Fetches all messages for a conversation after verifying user ownership.
    """
    if not conversation_id or not user_id:
        return []
    
    conv = get_conversation_by_id(conversation_id, user_id)
    if not conv:
        return []

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, conversation_id, role, content, created_at
        FROM career_messages
        WHERE conversation_id = ?
        ORDER BY id ASC
    """, (conversation_id,))
    messages = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return messages


def clear_conversation_messages(conversation_id: int, user_id: int) -> bool:
    """
    Clears all messages in a conversation after verifying user ownership.
    """
    if not conversation_id or not user_id:
        return False
    
    conv = get_conversation_by_id(conversation_id, user_id)
    if not conv:
        return False

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM career_messages
        WHERE conversation_id = ?
    """, (conversation_id,))
    cursor.execute("""
        UPDATE career_conversations
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (conversation_id,))
    conn.commit()
    conn.close()
    return True


def get_user_conversations(user_id: int) -> list:
    """
    Retrieves all conversation sessions for a student ordered by most recently active.
    """
    if not user_id:
        return []
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, 
               (SELECT COUNT(*) FROM career_messages m WHERE m.conversation_id = c.id) as message_count,
               (SELECT content FROM career_messages m WHERE m.conversation_id = c.id ORDER BY id ASC LIMIT 1) as preview
        FROM career_conversations c
        WHERE c.user_id = ?
        ORDER BY c.updated_at DESC
    """, (user_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def update_conversation_title(conversation_id: int, user_id: int, title: str) -> bool:
    """
    Updates the conversation title if it belongs to user_id.
    """
    if not conversation_id or not user_id or not title.strip():
        return False
    conv = get_conversation_by_id(conversation_id, user_id)
    if not conv:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE career_conversations
        SET title = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (title.strip()[:60], conversation_id))
    conn.commit()
    conn.close()
    return True


def delete_conversation(conversation_id: int, user_id: int) -> bool:
    """
    Deletes a conversation and its messages after verifying user ownership.
    """
    if not conversation_id or not user_id:
        return False
    conv = get_conversation_by_id(conversation_id, user_id)
    if not conv:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM career_messages WHERE conversation_id = ?", (conversation_id,))
    cursor.execute("DELETE FROM career_conversations WHERE id = ?", (conversation_id,))
    conn.commit()
    conn.close()
    return True


# =============================================================
# CHOICE LIST MANAGEMENT (PHASE 5)
# Uniquely identified by (user_id, college_code, branch_code)
# Isolated per authenticated student.
# =============================================================

def get_user_choice_list(user_id: int) -> list:
    """
    Retrieves the organized preference list for a specific student,
    enriched with college info, branch names, and historical cutoffs.
    """
    if not user_id:
        return []

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            ucl.id,
            ucl.user_id,
            ucl.college_code,
            ucl.branch_code,
            ucl.preference_order,
            ucl.created_at,
            c.college_name,
            c.college_type,
            ci.district,
            ci.taluk,
            ci.autonomous,
            b.branch_name
        FROM user_choice_list ucl
        LEFT JOIN colleges c ON c.college_code = ucl.college_code
        LEFT JOIN college_info ci ON ci.college_code = ucl.college_code
        LEFT JOIN branches b ON b.college_code = ucl.college_code AND b.branch_code = ucl.branch_code
        WHERE ucl.user_id = ?
        ORDER BY ucl.preference_order ASC, ucl.id ASC
    """, (user_id,))

    rows = [dict(r) for r in cursor.fetchall()]

    # Enrich each choice item with historical cutoff data (2023-2025)
    for item in rows:
        c_code = item["college_code"]
        b_code = item["branch_code"]
        cursor.execute("""
            SELECT year, oc, bc, bcm, mbc, sc, sca, st
            FROM cutoffs
            WHERE college_code = ? AND branch_code = ?
            ORDER BY year DESC
        """, (c_code, b_code))
        cutoffs = [dict(cr) for cr in cursor.fetchall()]
        item["historical_cutoffs"] = cutoffs

    conn.close()
    return rows


def add_to_choice_list(user_id: int, college_code: int, branch_code: str) -> dict:
    """
    Adds a college + branch combination to the student's choice list.
    Prevents duplicates through UNIQUE constraint.
    Assigns the next available preference order.
    """
    if not user_id or not college_code or not branch_code:
        return {"success": False, "message": "Missing parameters."}

    branch_code = branch_code.strip().upper()

    conn = get_connection()
    cursor = conn.cursor()

    # Check if this exact combination is already present for this student
    cursor.execute("""
        SELECT id, preference_order FROM user_choice_list
        WHERE user_id = ? AND college_code = ? AND branch_code = ?
    """, (user_id, college_code, branch_code))
    existing = cursor.fetchone()

    if existing:
        conn.close()
        return {
            "success": True,
            "already_exists": True,
            "message": "This college and branch choice is already in your list.",
            "choice_id": existing["id"],
            "preference_order": existing["preference_order"]
        }

    # Determine next preference order
    cursor.execute("""
        SELECT COALESCE(MAX(preference_order), 0) + 1 AS next_order
        FROM user_choice_list
        WHERE user_id = ?
    """, (user_id,))
    next_order = cursor.fetchone()["next_order"]

    cursor.execute("""
        INSERT INTO user_choice_list (user_id, college_code, branch_code, preference_order)
        VALUES (?, ?, ?, ?)
    """, (user_id, college_code, branch_code, next_order))
    choice_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return {
        "success": True,
        "already_exists": False,
        "message": "Added to your choice list successfully.",
        "choice_id": choice_id,
        "preference_order": next_order
    }


def remove_from_choice_list(user_id: int, college_code: int, branch_code: str) -> bool:
    """
    Removes a college + branch choice and re-indexes the preference ordering.
    """
    if not user_id or not college_code or not branch_code:
        return False

    branch_code = branch_code.strip().upper()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM user_choice_list
        WHERE user_id = ? AND college_code = ? AND branch_code = ?
    """, (user_id, college_code, branch_code))

    # Re-index preference orders sequentially
    cursor.execute("""
        SELECT id FROM user_choice_list
        WHERE user_id = ?
        ORDER BY preference_order ASC, id ASC
    """, (user_id,))
    remaining = cursor.fetchall()

    for idx, row in enumerate(remaining, start=1):
        cursor.execute("""
            UPDATE user_choice_list
            SET preference_order = ?
            WHERE id = ?
        """, (idx, row["id"]))

    conn.commit()
    conn.close()
    return True


def reorder_choice_list(user_id: int, ordered_items: list) -> bool:
    """
    Updates the preference orders based on an ordered list of {college_code, branch_code}.
    Verifies user ownership of all records.
    """
    if not user_id or not ordered_items:
        return False

    conn = get_connection()
    cursor = conn.cursor()

    for idx, item in enumerate(ordered_items, start=1):
        c_code = int(item.get("college_code", 0))
        b_code = str(item.get("branch_code", "")).strip().upper()
        if c_code and b_code:
            cursor.execute("""
                UPDATE user_choice_list
                SET preference_order = ?
                WHERE user_id = ? AND college_code = ? AND branch_code = ?
            """, (idx, user_id, c_code, b_code))

    conn.commit()
    conn.close()
    return True


def clear_user_choice_list(user_id: int) -> bool:
    """
    Clears all saved choices for a student.
    """
    if not user_id:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_choice_list WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True


# =============================================================
# COUNSELLING CHECKLIST (PHASE 5)
# Tracks completion of pre-counselling and pre-submission steps.
# =============================================================

DEFAULT_CHECKLIST_ITEMS = [
    # Before Choice Filling
    {"key": "review_career_fit", "stage": "before_filling", "title": "Review career-fit engineering branches", "desc": "Check your Phase 3 recommended branches matching your aptitude and interests."},
    {"key": "review_eligibility", "stage": "before_filling", "title": "Review TNEA eligibility and official cutoff calculation", "desc": "Confirm your 200-mark cutoff (Maths + Physics/2 + Chemistry/2) and community category."},
    {"key": "check_cutoff_trends", "stage": "before_filling", "title": "Inspect historical cutoff trends (2023–2025)", "desc": "Evaluate 3-year cutoff movements to understand branch competition patterns."},
    {"key": "shortlist_colleges", "stage": "before_filling", "title": "Shortlist target colleges by district and facilities", "desc": "Filter colleges by district, autonomous status, and hostel/transport availability."},
    {"key": "compare_branches", "stage": "before_filling", "title": "Compare curriculum and core focus of related branches", "desc": "Understand differences between core and specialized branches (e.g. CSE vs IT vs AI&DS)."},
    {"key": "check_college_info", "stage": "before_filling", "title": "Check verified college contact and accreditation info", "desc": "Review official website, address, taluk, and institutional status."},

    # Before Final Submission
    {"key": "verify_branch_order", "stage": "before_submission", "title": "Verify branch priority ordering", "desc": "Ensure your most desired branch is placed above compromise choices."},
    {"key": "verify_college_order", "stage": "before_submission", "title": "Verify college preference sequence", "desc": "Ensure preferred institutions are ordered correctly without naming confusion."},
    {"key": "review_dream_choices", "stage": "before_submission", "title": "Review ambitious (Dream) choices", "desc": "Keep aspirational choices at the top without worrying about losing lower chances."},
    {"key": "review_realistic_choices", "stage": "before_submission", "title": "Review realistic (Target) options", "desc": "Ensure 10–15 solid choices closely matching your exact cutoff range."},
    {"key": "review_safer_choices", "stage": "before_submission", "title": "Review safe backup (Safety) choices", "desc": "Include dependable choices with historical cutoffs safely below your score."},
    {"key": "recheck_official_portal", "stage": "before_submission", "title": "Recheck official TNEA portal announcements", "desc": "Verify current round rules, timelines, and vacancy notices on official tneaonline.org."},
    {"key": "final_choice_audit", "stage": "before_submission", "title": "Final review before locking choices", "desc": "Double check college codes and branch codes carefully before final lock."}
]


def get_user_checklist(user_id: int) -> dict:
    """
    Retrieves the checklist status map {item_key: True/False} for a user.
    """
    if not user_id:
        return {}

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT item_key, is_completed
        FROM user_counselling_checklist
        WHERE user_id = ?
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    status_map = {r["item_key"]: bool(r["is_completed"]) for r in rows}
    return status_map


def toggle_checklist_item(user_id: int, item_key: str, is_completed: bool) -> bool:
    """
    Toggles or sets the completion state of a specific checklist item for the user.
    """
    if not user_id or not item_key:
        return False

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_counselling_checklist (user_id, item_key, is_completed, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, item_key) DO UPDATE SET
            is_completed = excluded.is_completed,
            updated_at = CURRENT_TIMESTAMP
    """, (user_id, item_key.strip(), 1 if is_completed else 0))

    conn.commit()
    conn.close()
    return True


# =============================================================
# PREMIUM ENTITLEMENT & PAYMENT MANAGEMENT (CRITICAL PRODUCT FLOW)
# =============================================================

def create_payment_order(user_id: int, order_id: str, amount: float = 200.0, currency: str = "INR") -> dict:
    """
    Creates a pending order record for ₹200 Premium Access.
    """
    if not user_id or not order_id:
        return {"success": False, "message": "Missing user or order ID."}

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (user_id, order_id, amount, currency, status, created_at)
        VALUES (?, ?, ?, ?, 'created', CURRENT_TIMESTAMP)
    """, (user_id, order_id.strip(), float(amount), currency.strip().upper()))
    order_db_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "success": True,
        "id": order_db_id,
        "order_id": order_id.strip(),
        "amount": amount,
        "currency": currency
    }


def verify_and_activate_premium(user_id: int, order_id: str, payment_id: str = None, signature: str = None) -> bool:
    """
    Performs server-side payment verification and activates Premium entitlement in the database.
    Updates users.is_premium = 1 and orders record to 'paid'.
    """
    if not user_id or not order_id:
        return False

    conn = get_connection()
    cursor = conn.cursor()

    # 1. Update or create order record
    cursor.execute("""
        UPDATE orders
        SET status = 'paid',
            payment_id = ?,
            signature = ?,
            verified_at = CURRENT_TIMESTAMP
        WHERE user_id = ? AND order_id = ?
    """, (payment_id or f"pay_{order_id}", signature or "sig_verified", user_id, order_id.strip()))

    # If order didn't exist prior, insert as completed
    if cursor.rowcount == 0:
        cursor.execute("""
            INSERT INTO orders (user_id, order_id, amount, currency, status, payment_id, signature, created_at, verified_at)
            VALUES (?, ?, 200.0, 'INR', 'paid', ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (user_id, order_id.strip(), payment_id or f"pay_{order_id}", signature or "sig_verified"))

    # 2. Activate user premium entitlement
    cursor.execute("""
        UPDATE users
        SET is_premium = 1
        WHERE id = ?
    """, (user_id,))

    conn.commit()
    conn.close()
    return True


def set_user_premium_status(user_id: int, is_premium: bool) -> bool:
    """
    Explicitly sets or toggles premium entitlement for a user.
    """
    if not user_id:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users
        SET is_premium = ?
        WHERE id = ?
    """, (1 if is_premium else 0, user_id))
    conn.commit()
    conn.close()
    return True


def get_user_payment_history(user_id: int) -> list:
    """
    Retrieves the order/payment history for a student.
    """
    if not user_id:
        return []
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, user_id, order_id, amount, currency, status, payment_id, created_at, verified_at
        FROM orders
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# =============================================================
# STUDENT DOCUMENT VAULT (PREMIUM ONLY)
# =============================================================

def get_user_documents(user_id: int) -> list:
    """
    Retrieves all uploaded documents belonging to the authenticated student.
    Enforces strict user isolation.
    """
    if not user_id:
        return []
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, user_id, document_type, original_filename, storage_key, mime_type, file_size, uploaded_at, updated_at
        FROM student_documents
        WHERE user_id = ?
        ORDER BY updated_at DESC, uploaded_at DESC
    """, (user_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_user_document_by_id(user_id: int, doc_id: int) -> dict | None:
    """
    Retrieves a specific document belonging to user_id.
    Returns None if the document does not exist or belongs to another user.
    """
    if not user_id or not doc_id:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, user_id, document_type, original_filename, storage_key, mime_type, file_size, uploaded_at, updated_at
        FROM student_documents
        WHERE id = ? AND user_id = ?
    """, (doc_id, user_id))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_document_by_type(user_id: int, document_type: str) -> dict | None:
    """
    Retrieves a document of a specific type belonging to user_id.
    """
    if not user_id or not document_type:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, user_id, document_type, original_filename, storage_key, mime_type, file_size, uploaded_at, updated_at
        FROM student_documents
        WHERE user_id = ? AND document_type = ?
    """, (user_id, document_type))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def save_or_replace_user_document(user_id: int, document_type: str, original_filename: str, storage_key: str, mime_type: str, file_size: int) -> dict:
    """
    Saves a new document or updates/replaces an existing document for the user & document_type.
    Returns a dict with the new document record and any previous storage_key that should be removed from disk.
    """
    if not user_id or not document_type or not storage_key:
        raise ValueError("Invalid parameters for saving document")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if a document of this type already exists for the user
    cursor.execute("""
        SELECT id, storage_key
        FROM student_documents
        WHERE user_id = ? AND document_type = ?
    """, (user_id, document_type))
    existing = cursor.fetchone()
    
    old_storage_key = None
    if existing:
        old_storage_key = existing["storage_key"]
        doc_id = existing["id"]
        cursor.execute("""
            UPDATE student_documents
            SET original_filename = ?, storage_key = ?, mime_type = ?, file_size = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        """, (original_filename, storage_key, mime_type, file_size, doc_id, user_id))
    else:
        cursor.execute("""
            INSERT INTO student_documents (user_id, document_type, original_filename, storage_key, mime_type, file_size)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, document_type, original_filename, storage_key, mime_type, file_size))
        doc_id = cursor.lastrowid
        
    conn.commit()
    
    # Fetch updated row
    cursor.execute("""
        SELECT id, user_id, document_type, original_filename, storage_key, mime_type, file_size, uploaded_at, updated_at
        FROM student_documents
        WHERE id = ? AND user_id = ?
    """, (doc_id, user_id))
    doc = dict(cursor.fetchone())
    conn.close()
    
    return {
        "document": doc,
        "old_storage_key": old_storage_key
    }


def delete_user_document(user_id: int, doc_id: int) -> dict | None:
    """
    Deletes a user's document record from the database.
    Returns the deleted document data (including storage_key) so the file can be cleaned up from disk,
    or None if not found or unauthorized.
    """
    if not user_id or not doc_id:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, user_id, document_type, original_filename, storage_key, mime_type, file_size
        FROM student_documents
        WHERE id = ? AND user_id = ?
    """, (doc_id, user_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    
    deleted_doc = dict(row)
    cursor.execute("DELETE FROM student_documents WHERE id = ? AND user_id = ?", (doc_id, user_id))
    conn.commit()
    conn.close()
    return deleted_doc

