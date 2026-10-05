"""
====================================================
TNEA AI Career Advisor
Main Flask Application
====================================================
"""

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session,
    flash,
    make_response,
    send_file
)

import os
import re
import uuid
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Import our modules
from models.database import (
    get_all_colleges,
    get_all_districts,
    get_all_branches,
    get_college_details,
    get_college_branches,
    search_colleges,
    get_search_districts,
    init_auth_db,
    create_user,
    get_user_by_email,
    get_user_by_id,
    is_email_registered,
    save_student_profile,
    get_student_profile,
    has_student_profile,
    get_or_create_active_conversation,
    create_new_conversation,
    get_conversation_by_id,
    add_message,
    get_conversation_messages,
    clear_conversation_messages,
    get_user_conversations,
    update_conversation_title,
    delete_conversation,
    get_user_choice_list,
    add_to_choice_list,
    remove_from_choice_list,
    reorder_choice_list,
    clear_user_choice_list,
    get_user_checklist,
    toggle_checklist_item,
    DEFAULT_CHECKLIST_ITEMS,
    create_payment_order,
    verify_and_activate_premium,
    set_user_premium_status,
    get_user_payment_history,
    get_user_documents,
    get_user_document_by_id,
    get_user_document_by_type,
    save_or_replace_user_document,
    delete_user_document
)

from models.recommender import (
    recommend
)

from models.career_engine import (
    ASSESSMENT_QUESTIONS,
    process_full_assessment,
    calculate_tnea_cutoff
)

from models.ai_assistant import (
    get_career_assistant_response,
    generate_session_title
)

from models.resources import (
    get_all_resources,
    get_personalized_resources,
    RESOURCE_CATEGORIES
)

# --------------------------------------------------
# Flask App
# --------------------------------------------------

app = Flask(__name__)

app.config["SECRET_KEY"] = "tnea-ai-career-advisor-secure-key-2026"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(
    BASE_DIR,
    "database",
    "tnea.db"
)

app.config["DATABASE"] = DATABASE

# Initialize Auth Database Table
init_auth_db()

# --------------------------------------------------
# Secure Document Vault Configuration (Premium Only)
# --------------------------------------------------

VAULT_STORAGE_DIR = os.path.join(BASE_DIR, "storage", "vault")
os.makedirs(VAULT_STORAGE_DIR, exist_ok=True)

MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10 MB per document
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "webp"}
MIME_TYPE_MAP = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp"
}

VAULT_DOCUMENT_CATEGORIES = [
    {
        "key": "10th Marksheet",
        "group": "academic",
        "group_title": "Academic Documents",
        "name": "10th Marksheet / SSLC",
        "description": "Proof of date of birth and SSLC / 10th grade qualification.",
        "is_mandatory": True,
        "icon": "bi-file-earmark-text"
    },
    {
        "key": "+1 Marksheet",
        "group": "academic",
        "group_title": "Academic Documents",
        "name": "+1 (11th) Marksheet",
        "description": "Higher secondary first-year marksheet.",
        "is_mandatory": True,
        "icon": "bi-file-earmark-text"
    },
    {
        "key": "+2 Marksheet",
        "group": "academic",
        "group_title": "Academic Documents",
        "name": "+2 (12th / HSC) Marksheet",
        "description": "Qualifying examination marksheet used for TNEA cutoff calculation.",
        "is_mandatory": True,
        "icon": "bi-file-earmark-text-fill"
    },
    {
        "key": "Transfer Certificate",
        "group": "counselling",
        "group_title": "Counselling Documents",
        "name": "Transfer Certificate (TC)",
        "description": "Issued by school last attended (mandatory during college admission verification).",
        "is_mandatory": True,
        "icon": "bi-award"
    },
    {
        "key": "Community Certificate",
        "group": "counselling",
        "group_title": "Counselling Documents",
        "name": "Community Certificate",
        "description": "Card / e-Certificate for BC / BCM / MBC & DNC / SC / SCA / ST reservation quota.",
        "is_mandatory": False,
        "applicable_note": "Required if claiming quota reservation",
        "icon": "bi-people"
    },
    {
        "key": "Income Certificate",
        "group": "counselling",
        "group_title": "Counselling Documents",
        "name": "Income Certificate",
        "description": "Issued by Revenue Authority (for fee concession, Post-Matric scholarship, etc.).",
        "is_mandatory": False,
        "applicable_note": "Required for fee concessions / scholarships",
        "icon": "bi-cash-coin"
    },
    {
        "key": "First Graduate Certificate",
        "group": "special",
        "group_title": "Certificates & Special Claims",
        "name": "First Graduate Certificate & Joint Declaration",
        "description": "Eligible for TN Govt tuition fee concession (if no family graduate).",
        "is_mandatory": False,
        "applicable_note": "If claiming First Graduate fee concession",
        "icon": "bi-mortarboard"
    },
    {
        "key": "Nativity Certificate",
        "group": "special",
        "group_title": "Certificates & Special Claims",
        "name": "Nativity Certificate",
        "description": "For candidates who completed schooling (VIII–XII) outside TN claiming TN nativity.",
        "is_mandatory": False,
        "applicable_note": "If studied outside Tamil Nadu",
        "icon": "bi-geo-alt"
    },
    {
        "key": "Special Reservation Document",
        "group": "special",
        "group_title": "Certificates & Special Claims",
        "name": "Special Reservation Certificate",
        "description": "For Eminent Sports Persons, Ex-Servicemen, Differently Abled, or 7.5% Govt School quota.",
        "is_mandatory": False,
        "applicable_note": "If applying under special quota",
        "icon": "bi-star"
    },
    {
        "key": "Other",
        "group": "other",
        "group_title": "Other Documents",
        "name": "Other Official Document",
        "description": "Any additional certificates, migration certificates, or declarations.",
        "is_mandatory": False,
        "applicable_note": "Optional / as needed",
        "icon": "bi-folder2-open"
    }
]

VALID_DOCUMENT_KEYS = {c["key"] for c in VAULT_DOCUMENT_CATEGORIES}


def _validate_vault_file(file_obj):
    """
    Validates uploaded file for extension, size, and header magic bytes.
    Returns (is_valid: bool, error_message: str | None, safe_ext: str, mime_type: str, file_bytes: bytes)
    """
    if not file_obj or not file_obj.filename:
        return False, "No file selected for upload.", "", "", b""
    
    filename = file_obj.filename.strip()
    if "." not in filename:
        return False, "Uploaded file has no extension.", "", "", b""
    
    ext = filename.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File format .{ext} is not allowed. Supported formats: PDF, JPG, JPEG, PNG, WEBP.", "", "", b""
    
    # Read file content to inspect size and magic bytes
    content = file_obj.read()
    file_size = len(content)
    
    if file_size == 0:
        return False, "The uploaded file is empty.", "", "", b""
    
    if file_size > MAX_DOCUMENT_SIZE:
        return False, f"File size ({file_size / (1024*1024):.2f}MB) exceeds the maximum allowed limit of 10MB.", "", "", b""
    
    # Magic byte validation
    is_signature_valid = False
    detected_mime = MIME_TYPE_MAP.get(ext, "application/octet-stream")
    
    if ext == "pdf":
        if content.startswith(b"%PDF") or b"%PDF" in content[:1024]:
            is_signature_valid = True
            detected_mime = "application/pdf"
    elif ext in ("jpg", "jpeg"):
        if content.startswith(b"\xff\xd8\xff"):
            is_signature_valid = True
            detected_mime = "image/jpeg"
    elif ext == "png":
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            is_signature_valid = True
            detected_mime = "image/png"
    elif ext == "webp":
        if content.startswith(b"RIFF") and len(content) >= 12 and content[8:12] == b"WEBP":
            is_signature_valid = True
            detected_mime = "image/webp"
    
    if not is_signature_valid:
        return False, "File contents do not match the expected document format. Upload rejected for security.", "", "", b""
    
    return True, None, ext, detected_mime, content


def _remove_vault_file_from_disk(storage_key: str):
    """
    Safely removes a document file from the private vault storage directory.
    Prevents path traversal by resolving canonical paths.
    """
    if not storage_key:
        return
    safe_name = os.path.basename(storage_key)
    file_path = os.path.join(VAULT_STORAGE_DIR, safe_name)
    resolved_path = os.path.abspath(file_path)
    vault_base = os.path.abspath(VAULT_STORAGE_DIR)
    if resolved_path.startswith(vault_base) and os.path.exists(resolved_path):
        try:
            os.remove(resolved_path)
        except OSError:
            pass



# --------------------------------------------------
# Context Processor for Global User State
# --------------------------------------------------

@app.context_processor
def inject_user():
    user_id = session.get("user_id")
    if user_id:
        user = get_user_by_id(user_id)
        if user:
            # Sync session premium flag with database ground truth
            session["is_premium"] = user["is_premium"]
            return {
                "current_user": {
                    "id": user["id"],
                    "name": user["name"],
                    "email": user["email"],
                    "is_premium": bool(user["is_premium"]),
                    "is_authenticated": True
                }
            }
    return {
        "current_user": {
            "id": None,
            "name": None,
            "email": None,
            "is_premium": False,
            "is_authenticated": False
        }
    }


# --------------------------------------------------
# Auth Helper & Decorators (Critical Product Flow)
# --------------------------------------------------

PUBLIC_ENDPOINTS = {"login", "register", "static"}


@app.before_request
def require_login_for_visitors():
    """
    CRITICAL PRODUCT FLOW:
    A new visitor must first be required to Login or Create an Account.
    Publicly allowed endpoints: login, register, static files.
    All other views require authentication.
    """
    endpoint = request.endpoint
    if endpoint is None:
        return
    # Allow static assets and authentication endpoints
    if endpoint in PUBLIC_ENDPOINTS or endpoint.startswith("static"):
        return
    # If unauthenticated, redirect to login with destination preservation
    if not session.get("user_id"):
        return redirect(url_for("login", next=request.url))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def premium_required(f):
    """
    Guards the 4 Premium features:
    1. AI Career Assistant
    2. TNEA Counselling Assistant
    3. Personalized Learning Resources
    4. Advanced Choice List / Choice Analysis
    Redirects free users to the ₹200 Premium Details page or returns 403 JSON API.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"status": "unauthenticated", "message": "Please sign in to proceed."}), 401
            return redirect(url_for("login", next=request.url))

        user = get_user_by_id(user_id)
        if not user or not user["is_premium"]:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({
                    "status": "premium_required",
                    "message": "Premium Access (₹200) required to use this feature."
                }), 403
            flash("Unlock ₹200 Premium Access to use this feature.", "warning")
            return redirect(url_for("premium_view", next=request.url, feature=request.endpoint))
        return f(*args, **kwargs)
    return decorated_function


# ==================================================
# AUTHENTICATION ROUTES
# ==================================================

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


@app.route("/register", methods=["GET", "POST"])
def register():
    # If already logged in, redirect to career guidance or destination
    if session.get("user_id"):
        return redirect(url_for("career_guidance"))

    next_url = request.args.get("next") or request.form.get("next") or ""

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Server-side validations
        if not name or not email or not password or not confirm_password:
            return render_template(
                "register.html",
                error="All fields are required.",
                name=name,
                email=email,
                next_url=next_url
            )

        if not EMAIL_REGEX.match(email):
            return render_template(
                "register.html",
                error="Please enter a valid email address format.",
                name=name,
                email=email,
                next_url=next_url
            )

        if len(password) < 6:
            return render_template(
                "register.html",
                error="Password must be at least 6 characters long.",
                name=name,
                email=email,
                next_url=next_url
            )

        if password != confirm_password:
            return render_template(
                "register.html",
                error="Passwords do not match. Please verify your password.",
                name=name,
                email=email,
                next_url=next_url
            )

        if is_email_registered(email):
            return render_template(
                "register.html",
                error="An account with this email address already exists. Please sign in.",
                name=name,
                email=email,
                next_url=next_url
            )

        # Hash password and create user
        password_hash = generate_password_hash(password)
        user_id = create_user(name=name, email=email, password_hash=password_hash)

        # Automatically establish secure session
        session["user_id"] = user_id
        session["user_name"] = name
        session["user_email"] = email
        session["is_premium"] = 0

        flash("Account created successfully! Welcome to TNEA Career Navigator.", "success")

        # Safely redirect
        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect(url_for("home"))

    return render_template("register.html", next_url=next_url)


@app.route("/login", methods=["GET", "POST"])
def login():
    # If already logged in, redirect to home or destination
    if session.get("user_id"):
        return redirect(url_for("home"))

    next_url = request.args.get("next") or request.form.get("next") or ""

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template(
                "login.html",
                error="Please enter both your email address and password.",
                email=email,
                next_url=next_url
            )

        user = get_user_by_email(email)

        if not user or not check_password_hash(user["password_hash"], password):
            return render_template(
                "login.html",
                error="Invalid email or password. Please check your credentials.",
                email=email,
                next_url=next_url
            )

        # Establish session
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        session["is_premium"] = user["is_premium"]

        # Safely redirect
        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect(url_for("home"))

    return render_template("login.html", next_url=next_url)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out successfully.", "info")
    response = make_response(redirect(url_for("login")))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ==================================================
# 1. CAREER GUIDANCE & ASSESSMENT (PREMIUM BENEFIT 1)
# ==================================================

@app.route("/career-guidance")
@login_required
@premium_required
def career_guidance():
    user_id = session.get("user_id")
    profile = get_student_profile(user_id)
    if profile:
        response = make_response(render_template("career_profile.html", profile=profile))
    else:
        response = make_response(render_template("career_guidance.html"))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/career-guidance/assessment", methods=["GET", "POST"])
@login_required
@premium_required
def assessment():
    user_id = session.get("user_id")

    if request.method == "POST":
        try:
            maths = float(request.form.get("maths_marks", 0))
            physics = float(request.form.get("physics_marks", 0))
            chemistry = float(request.form.get("chemistry_marks", 0))

            if maths < 0 or maths > 100 or physics < 0 or physics > 100 or chemistry < 0 or chemistry > 100:
                districts = get_all_districts()
                profile = get_student_profile(user_id)
                return render_template(
                    "assessment.html",
                    questions=ASSESSMENT_QUESTIONS,
                    districts=districts,
                    profile=profile,
                    error="Please enter valid subject marks between 0 and 100."
                )

            # Process assessment using career engine
            profile_data = process_full_assessment(request.form)

            # Save in database
            save_student_profile(user_id, profile_data)

            flash("Career Discovery & Interest Assessment completed successfully!", "success")
            return redirect(url_for("career_guidance"))

        except Exception as e:
            print("Assessment submission error:", e)
            districts = get_all_districts()
            profile = get_student_profile(user_id)
            return render_template(
                "assessment.html",
                questions=ASSESSMENT_QUESTIONS,
                districts=districts,
                profile=profile,
                error="An error occurred while evaluating your assessment. Please verify your inputs."
            )

    districts = get_all_districts()
    profile = get_student_profile(user_id)
    return render_template(
        "assessment.html",
        questions=ASSESSMENT_QUESTIONS,
        districts=districts,
        profile=profile
    )


@app.route("/career-guidance/submit", methods=["POST"])
@login_required
@premium_required
def submit_assessment():
    return assessment()


@app.route("/career-guidance/profile")
@login_required
@premium_required
def student_profile_view():
    user_id = session.get("user_id")
    profile = get_student_profile(user_id)
    if not profile:
        return redirect(url_for("assessment"))
    response = make_response(render_template("career_profile.html", profile=profile))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/career-guidance/retake")
@login_required
@premium_required
def retake_assessment():
    return redirect(url_for("assessment"))


# ==================================================
# PREMIUM DETAILS & SERVER-SIDE PAYMENT ROUTES
# ==================================================

@app.route("/premium")
def premium_view():
    """
    CRITICAL PRODUCT FLOW:
    Premium Details page explaining the ₹200 Premium Access and its four benefits:
    1. AI Career Assistant
    2. TNEA Counselling Assistant
    3. Personalized Learning Resources
    4. Advanced Choice List / Choice Analysis
    """
    user_id = session.get("user_id")
    user = get_user_by_id(user_id) if user_id else None
    feature = request.args.get("feature", "")
    next_url = request.args.get("next", "")

    feature_names = {
        "career_guidance": "Personalized Career Guidance & Aptitude Discovery",
        "assessment": "Career Discovery & Aptitude Assessment",
        "student_profile_view": "Career Guidance & Student Profile Report",
        "career_assistant_view": "AI Career Assistant & Chatbot",
        "career_assistant": "AI Career Assistant",
        "counselling_guide": "TNEA Counselling Assistant & Strategy Checklist",
        "counselling": "TNEA Counselling Assistant",
        "learning_resources": "Personalized Learning Resources Track",
        "resources": "Personalized Learning Resources Track",
        "choice_analysis": "Advanced Choice List & Admission Opportunity Analysis",
        "choice_list_view": "Advanced Choice List & Opportunity Analysis",
        "choice_list": "Advanced Choice List & Opportunity Analysis"
    }

    feature_notice = feature_names.get(feature)

    response = make_response(render_template(
        "premium.html",
        feature_notice=feature_notice,
        next_url=next_url,
        user=user
    ))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@app.route("/api/payment/create-order", methods=["POST"])
@login_required
def api_payment_create_order():
    """
    Server-side order creation for ₹200 Premium Access.
    """
    user_id = session.get("user_id")
    data = request.get_json() or {}
    amount = float(data.get("amount", 200.0))
    currency = str(data.get("currency", "INR")).upper()

    import uuid
    order_id = f"order_{uuid.uuid4().hex[:12].upper()}"

    res = create_payment_order(user_id=user_id, order_id=order_id, amount=amount, currency=currency)
    return jsonify({
        "status": "success",
        "order_id": order_id,
        "amount": amount,
        "currency": currency,
        "key_id": "rzp_test_tnea2026mock"
    })


@app.route("/api/payment/verify", methods=["POST"])
@login_required
def api_payment_verify():
    """
    CRITICAL PRODUCT FLOW:
    Server-side payment verification.
    Only after successful verification is the user's Premium entitlement activated.
    Updates database users.is_premium = 1 and syncs session.
    """
    user_id = session.get("user_id")
    data = request.get_json() or {}
    order_id = str(data.get("order_id", "")).strip()
    payment_id = str(data.get("payment_id", "")).strip()
    signature = str(data.get("signature", "")).strip()

    if not order_id:
        return jsonify({"status": "error", "message": "Order ID is required for verification."}), 400

    # Execute server-side verification and activation
    success = verify_and_activate_premium(
        user_id=user_id,
        order_id=order_id,
        payment_id=payment_id or f"pay_{order_id}",
        signature=signature or "sig_verified"
    )

    if success:
        # Update session entitlement
        session["is_premium"] = 1
        return jsonify({
            "status": "success",
            "message": "Payment verified successfully. Premium entitlement activated!",
            "is_premium": True
        })

    return jsonify({"status": "error", "message": "Payment verification failed."}), 400


# ==================================================
# 1. AI CAREER ASSISTANT & CHATBOT (PREMIUM BENEFIT 1)
# ==================================================

def can_access_career_assistant(user_id: int) -> bool:
    """
    Encapsulates permission logic for Career Assistant.
    Requires active Premium entitlement.
    """
    if not user_id:
        return False
    user = get_user_by_id(user_id)
    return bool(user and user.get("is_premium"))


@app.route("/career-guidance/assistant")
@app.route("/career-assistant")
@login_required
@premium_required
def career_assistant_view():
    user_id = session.get("user_id")
    profile = get_student_profile(user_id)
    
    # Check if a specific conversation session was requested
    session_id_raw = request.args.get("session_id")
    conversation = None
    if session_id_raw:
        try:
            conv_id = int(session_id_raw)
            conversation = get_conversation_by_id(conv_id, user_id)
        except (ValueError, TypeError):
            conversation = None

    if not conversation:
        conversation = get_or_create_active_conversation(user_id)

    messages = get_conversation_messages(conversation["id"], user_id)
    conversations = get_user_conversations(user_id)

    response = make_response(render_template(
        "career_assistant.html",
        profile=profile,
        conversation=conversation,
        messages=messages,
        conversations=conversations
    ))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/career-guidance/assistant/chat", methods=["POST"])
@login_required
@premium_required
def career_assistant_chat():
    user_id = session.get("user_id")
    data = request.get_json() or {}
    raw_message = str(data.get("message", "")).strip()
    conv_id_raw = data.get("conversation_id")

    if not raw_message:
        return jsonify({"status": "error", "message": "Please enter a valid message."}), 400

    # Limit message size for security
    if len(raw_message) > 1000:
        raw_message = raw_message[:1000]

    # Verify conversation ownership
    conversation = None
    if conv_id_raw is not None and str(conv_id_raw).strip() != "":
        try:
            conv_id = int(conv_id_raw)
            conversation = get_conversation_by_id(conv_id, user_id)
            if not conversation:
                return jsonify({"status": "error", "message": "Conversation not found or access denied."}), 403
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "Invalid conversation ID."}), 400
    else:
        conversation = get_or_create_active_conversation(user_id)

    conversation_id = conversation["id"]

    # 1. Save student message
    add_message(conversation_id, user_id, "user", raw_message)

    # 2. Retrieve student context & history
    profile = get_student_profile(user_id)
    user = get_user_by_id(user_id)
    user_name = user["name"] if user else session.get("user_name", "Student")
    history = get_conversation_messages(conversation_id, user_id)

    # Auto-update conversation title if it's currently generic
    if conversation.get("title") in ["Career Guidance Session", "New Guidance Session", ""] or len(history) <= 2:
        smart_title = generate_session_title(raw_message)
        update_conversation_title(conversation_id, user_id, smart_title)
        conversation["title"] = smart_title

    # 3. Generate assistant guidance response and contextual followups
    try:
        assistant_reply, followups = get_career_assistant_response(
            user_message=raw_message,
            profile=profile,
            user_name=user_name,
            conversation_history=history,
            user_id=user_id
        )
    except Exception as e:
        print("Career Assistant generation error:", e)
        assistant_reply = (
            "I apologize, but I encountered a momentary issue processing your request. "
            "Your profile and assessment results are safely preserved. Please feel free to ask again."
        )
        from models.ai_assistant import DEFAULT_STARTER_QUESTIONS
        followups = DEFAULT_STARTER_QUESTIONS[:4]

    # 4. Save assistant reply
    add_message(conversation_id, user_id, "assistant", assistant_reply)

    return jsonify({
        "status": "success",
        "response": assistant_reply,
        "followups": followups,
        "conversation_id": conversation_id,
        "conversation_title": conversation.get("title", "Career Guidance Session")
    })


@app.route("/career-guidance/assistant/new", methods=["POST"])
@login_required
@premium_required
def career_assistant_new():
    user_id = session.get("user_id")
    new_conv = create_new_conversation(user_id, "New Guidance Session")
    return jsonify({"status": "success", "conversation_id": new_conv["id"]})


@app.route("/career-guidance/assistant/clear", methods=["POST"])
@login_required
@premium_required
def career_assistant_clear():
    user_id = session.get("user_id")
    data = request.get_json() or {}
    conv_id_raw = data.get("conversation_id")
    if conv_id_raw:
        try:
            conv_id = int(conv_id_raw)
            clear_conversation_messages(conv_id, user_id)
        except (ValueError, TypeError):
            pass
    else:
        conv = get_or_create_active_conversation(user_id)
        clear_conversation_messages(conv["id"], user_id)
    return jsonify({"status": "success"})


@app.route("/career-guidance/assistant/delete", methods=["POST"])
@login_required
@premium_required
def career_assistant_delete():
    user_id = session.get("user_id")
    data = request.get_json() or {}
    conv_id_raw = data.get("conversation_id")
    if conv_id_raw:
        try:
            conv_id = int(conv_id_raw)
            success = delete_conversation(conv_id, user_id)
            if success:
                return jsonify({"status": "success"})
            else:
                return jsonify({"status": "error", "message": "Conversation not found or access denied."}), 403
        except (ValueError, TypeError):
            pass
    return jsonify({"status": "error", "message": "Invalid conversation ID"}), 400


# ==================================================
# 2. TNEA COUNSELLING ASSISTANT (PREMIUM BENEFIT 2)
# ==================================================

@app.route("/counselling")
@app.route("/counselling-guide")
@login_required
@premium_required
def counselling_guide():
    user_id = session.get("user_id")
    profile = get_student_profile(user_id) if user_id else None
    checklist_status = get_user_checklist(user_id) if user_id else {}
    choice_list = get_user_choice_list(user_id) if user_id else []

    # Calculate checklist progress
    total_items = len(DEFAULT_CHECKLIST_ITEMS)
    completed_count = sum(1 for item in DEFAULT_CHECKLIST_ITEMS if checklist_status.get(item["key"], False))
    progress_pct = int((completed_count / total_items) * 100) if total_items > 0 else 0

    # Retrieve student's document vault
    user_docs = get_user_documents(user_id) if user_id else []
    doc_map = {d["document_type"]: d for d in user_docs}
    vault_uploaded_count = len(user_docs)
    vault_total_categories = len(VAULT_DOCUMENT_CATEGORIES)

    response = make_response(render_template(
        "counselling.html",
        profile=profile,
        checklist_items=DEFAULT_CHECKLIST_ITEMS,
        checklist_status=checklist_status,
        completed_count=completed_count,
        total_items=total_items,
        progress_pct=progress_pct,
        choice_count=len(choice_list),
        vault_categories=VAULT_DOCUMENT_CATEGORIES,
        user_documents=user_docs,
        doc_map=doc_map,
        vault_uploaded_count=vault_uploaded_count,
        vault_total_categories=vault_total_categories
    ))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


# ==================================================
# 3. VERIFIED & PERSONALIZED LEARNING RESOURCES (PREMIUM BENEFIT 3)
# ==================================================

@app.route("/resources")
@login_required
@premium_required
def learning_resources():
    category = request.args.get("category", "all").strip().lower()
    search_q = request.args.get("q", "").strip()

    user_id = session.get("user_id")
    user = get_user_by_id(user_id) if user_id else None
    profile = get_student_profile(user_id) if user_id else None

    # Check premium entitlement for personalized recommendations
    is_premium_user = bool(user and user.get("is_premium"))

    # Get personalized resources prioritized for the student's career fit
    personalized = get_personalized_resources(profile, limit=6)

    # Get full catalog filtered by category / search query
    resources = get_all_resources(category=category, search_query=search_q)

    response = make_response(render_template(
        "resources.html",
        categories=RESOURCE_CATEGORIES,
        resources=resources,
        personalized_resources=personalized,
        is_personalized_locked=not is_premium_user,
        selected_category=category,
        search_query=search_q,
        profile=profile,
        total_count=len(resources)
    ))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


# ==================================================
# 5. CHOICE LIST & ADVANCED CHOICE ANALYSIS (PREMIUM BENEFIT 5)
# ==================================================

@app.route("/choice-list")
@app.route("/choice-list/advanced")
@login_required
@premium_required
def choice_list_view():
    user_id = session.get("user_id")
    user = get_user_by_id(user_id) if user_id else None
    profile = get_student_profile(user_id) if user_id else None
    choices = get_user_choice_list(user_id) if user_id else []

    is_premium_user = bool(user and user.get("is_premium"))

    # Enrich choices with admission opportunity classification if cutoff is available
    student_cutoff = float(profile.get("cutoff", 0.0)) if profile else 0.0
    student_comm = str(profile.get("community", "OC")).upper() if profile else "OC"
    comm_col = student_comm.lower()

    for item in choices:
        cutoffs = item.get("historical_cutoffs", [])
        ref_cutoff = None
        # Try latest available cutoff
        for c in cutoffs:
            val = c.get(comm_col) or c.get("oc")
            if val is not None:
                ref_cutoff = float(val)
                break
        
        item["ref_cutoff"] = ref_cutoff
        if ref_cutoff and student_cutoff > 0:
            diff = student_cutoff - ref_cutoff
            if diff < -1.0:
                item["tier"] = "Dream"
                item["tier_class"] = "badge-danger"
                item["tier_desc"] = "Aspirational (Cutoff above score)"
            elif -1.0 <= diff <= 2.0:
                item["tier"] = "Realistic"
                item["tier_class"] = "badge-primary"
                item["tier_desc"] = "Target Match (Near exact score)"
            else:
                item["tier"] = "Safer"
                item["tier_class"] = "badge-success"
                item["tier_desc"] = "Safe Backup (Score comfortably above)"
        else:
            item["tier"] = "Unranked"
            item["tier_class"] = "badge-secondary"
            item["tier_desc"] = "Add Cutoff to Classify"

    response = make_response(render_template(
        "choice_list.html",
        choices=choices,
        profile=profile,
        student_cutoff=student_cutoff,
        student_community=student_comm,
        total_choices=len(choices),
        is_premium_analysis=is_premium_user
    ))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


# ==================================================
# CHOICE LIST & CHECKLIST JSON APIs
# ==================================================

@app.route("/api/choice-list", methods=["GET"])
@login_required
@premium_required
def api_get_choice_list():
    user_id = session.get("user_id")
    choices = get_user_choice_list(user_id)
    return jsonify({"status": "success", "choices": choices, "count": len(choices)})


@app.route("/api/choice-list/add", methods=["POST"])
@login_required
@premium_required
def api_add_choice():
    user_id = session.get("user_id")
    data = request.get_json() or {}
    college_code = data.get("college_code")
    branch_code = data.get("branch_code")

    if not college_code or not branch_code:
        return jsonify({"status": "error", "message": "College code and branch code are required."}), 400

    try:
        c_code = int(college_code)
        b_code = str(branch_code).strip().upper()
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid code parameters."}), 400

    result = add_to_choice_list(user_id, c_code, b_code)
    choices = get_user_choice_list(user_id)

    return jsonify({
        "status": "success",
        "data": result,
        "total_count": len(choices)
    })


@app.route("/api/choice-list/remove", methods=["POST"])
@login_required
@premium_required
def api_remove_choice():
    user_id = session.get("user_id")
    data = request.get_json() or {}
    college_code = data.get("college_code")
    branch_code = data.get("branch_code")

    if not college_code or not branch_code:
        return jsonify({"status": "error", "message": "College code and branch code required."}), 400

    try:
        c_code = int(college_code)
        b_code = str(branch_code).strip().upper()
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid code parameters."}), 400

    success = remove_from_choice_list(user_id, c_code, b_code)
    choices = get_user_choice_list(user_id)

    return jsonify({
        "status": "success" if success else "error",
        "total_count": len(choices)
    })


@app.route("/api/choice-list/reorder", methods=["POST"])
@login_required
@premium_required
def api_reorder_choice():
    user_id = session.get("user_id")
    data = request.get_json() or {}
    items = data.get("items", [])
    if not isinstance(items, list):
        return jsonify({"status": "error", "message": "Invalid items format."}), 400

    success = reorder_choice_list(user_id, items)
    return jsonify({"status": "success" if success else "error"})


@app.route("/api/choice-list/clear", methods=["POST"])
@login_required
@premium_required
def api_clear_choice():
    user_id = session.get("user_id")
    success = clear_user_choice_list(user_id)
    return jsonify({"status": "success" if success else "error", "total_count": 0})


@app.route("/api/checklist/toggle", methods=["POST"])
@login_required
@premium_required
def api_toggle_checklist():
    user_id = session.get("user_id")
    data = request.get_json() or {}
    item_key = str(data.get("item_key", "")).strip()
    is_completed = bool(data.get("is_completed", False))

    if not item_key:
        return jsonify({"status": "error", "message": "Item key is required."}), 400

    success = toggle_checklist_item(user_id, item_key, is_completed)
    checklist_status = get_user_checklist(user_id)
    total_items = len(DEFAULT_CHECKLIST_ITEMS)
    completed_count = sum(1 for item in DEFAULT_CHECKLIST_ITEMS if checklist_status.get(item["key"], False))
    progress_pct = int((completed_count / total_items) * 100) if total_items > 0 else 0

    return jsonify({
        "status": "success" if success else "error",
        "item_key": item_key,
        "is_completed": is_completed,
        "completed_count": completed_count,
        "total_items": total_items,
        "progress_pct": progress_pct
    })


# ==================================================
# STUDENT DOCUMENT VAULT APIs (PREMIUM ONLY)
# ==================================================

@app.route("/api/vault/documents", methods=["GET"])
@login_required
@premium_required
def api_get_vault_documents():
    """
    Retrieves the document list for the authenticated student.
    Guarantees user isolation.
    """
    user_id = session.get("user_id")
    docs = get_user_documents(user_id)
    doc_map = {d["document_type"]: d for d in docs}
    
    formatted_categories = []
    for cat in VAULT_DOCUMENT_CATEGORIES:
        uploaded_doc = doc_map.get(cat["key"])
        formatted_categories.append({
            "key": cat["key"],
            "group": cat["group"],
            "group_title": cat["group_title"],
            "name": cat["name"],
            "description": cat["description"],
            "is_mandatory": cat.get("is_mandatory", False),
            "applicable_note": cat.get("applicable_note", ""),
            "icon": cat.get("icon", "bi-file-earmark"),
            "is_uploaded": uploaded_doc is not None,
            "document": {
                "id": uploaded_doc["id"],
                "original_filename": uploaded_doc["original_filename"],
                "file_size": uploaded_doc["file_size"],
                "mime_type": uploaded_doc["mime_type"],
                "uploaded_at": uploaded_doc["uploaded_at"],
                "updated_at": uploaded_doc["updated_at"]
            } if uploaded_doc else None
        })

    return jsonify({
        "status": "success",
        "total_uploaded": len(docs),
        "total_categories": len(VAULT_DOCUMENT_CATEGORIES),
        "categories": formatted_categories,
        "documents": [
            {
                "id": d["id"],
                "document_type": d["document_type"],
                "original_filename": d["original_filename"],
                "file_size": d["file_size"],
                "mime_type": d["mime_type"],
                "uploaded_at": d["uploaded_at"],
                "updated_at": d["updated_at"]
            } for d in docs
        ]
    })


@app.route("/api/vault/upload", methods=["POST"])
@login_required
@premium_required
def api_upload_vault_document():
    """
    Uploads or replaces a document in the student's personal vault.
    Enforces file size, extension, header magic bytes, and user ownership.
    """
    user_id = session.get("user_id")
    document_type = request.form.get("document_type", "").strip()

    if not document_type:
        return jsonify({"status": "error", "message": "Document category is required."}), 400

    if document_type not in VALID_DOCUMENT_KEYS:
        return jsonify({"status": "error", "message": f"Invalid document category: {document_type}"}), 400

    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded in the request."}), 400

    file_obj = request.files["file"]
    is_valid, err_msg, safe_ext, mime_type, file_bytes = _validate_vault_file(file_obj)

    if not is_valid:
        return jsonify({"status": "error", "message": err_msg}), 400

    # Sanitize original filename
    raw_name = os.path.basename(file_obj.filename.strip())
    safe_original_name = secure_filename(raw_name)
    if not safe_original_name or safe_original_name == f".{safe_ext}":
        safe_original_name = f"{document_type.replace(' ', '_').lower()}.{safe_ext}"

    # Generate isolated random storage key
    storage_key = f"{uuid.uuid4().hex}_{user_id}.{safe_ext}"
    target_path = os.path.join(VAULT_STORAGE_DIR, storage_key)

    try:
        with open(target_path, "wb") as f:
            f.write(file_bytes)
    except Exception as e:
        return jsonify({"status": "error", "message": "Failed to store file securely on disk."}), 500

    # Save to database
    try:
        res = save_or_replace_user_document(
            user_id=user_id,
            document_type=document_type,
            original_filename=safe_original_name,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size=len(file_bytes)
        )
        # Clean up replaced old file if one existed
        if res.get("old_storage_key"):
            _remove_vault_file_from_disk(res["old_storage_key"])

        doc = res["document"]
        return jsonify({
            "status": "success",
            "message": f"'{document_type}' uploaded successfully.",
            "document": {
                "id": doc["id"],
                "document_type": doc["document_type"],
                "original_filename": doc["original_filename"],
                "file_size": doc["file_size"],
                "mime_type": doc["mime_type"],
                "uploaded_at": doc["uploaded_at"],
                "updated_at": doc["updated_at"]
            }
        })
    except Exception as e:
        # Clean up newly written file if database transaction fails
        _remove_vault_file_from_disk(storage_key)
        return jsonify({"status": "error", "message": "Failed to record document metadata in database."}), 500


@app.route("/api/vault/document/<int:doc_id>/view", methods=["GET"])
@login_required
@premium_required
def api_view_vault_document(doc_id):
    """
    Secure inline view of a student's own document.
    Enforces authenticated user ownership (prevents IDOR).
    """
    user_id = session.get("user_id")
    doc = get_user_document_by_id(user_id, doc_id)

    if not doc:
        return jsonify({"status": "error", "message": "Document not found or access denied."}), 404

    safe_name = os.path.basename(doc["storage_key"])
    file_path = os.path.join(VAULT_STORAGE_DIR, safe_name)
    resolved_path = os.path.abspath(file_path)
    vault_base = os.path.abspath(VAULT_STORAGE_DIR)

    if not resolved_path.startswith(vault_base) or not os.path.exists(resolved_path):
        return jsonify({"status": "error", "message": "Stored document file could not be found."}), 404

    response = make_response(send_file(
        resolved_path,
        mimetype=doc["mime_type"],
        as_attachment=False,
        download_name=doc["original_filename"]
    ))
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, no-cache, no-store, must-revalidate"
    return response


@app.route("/api/vault/document/<int:doc_id>/download", methods=["GET"])
@login_required
@premium_required
def api_download_vault_document(doc_id):
    """
    Secure attachment download of a student's own document with its original filename.
    Enforces authenticated user ownership (prevents IDOR).
    """
    user_id = session.get("user_id")
    doc = get_user_document_by_id(user_id, doc_id)

    if not doc:
        return jsonify({"status": "error", "message": "Document not found or access denied."}), 404

    safe_name = os.path.basename(doc["storage_key"])
    file_path = os.path.join(VAULT_STORAGE_DIR, safe_name)
    resolved_path = os.path.abspath(file_path)
    vault_base = os.path.abspath(VAULT_STORAGE_DIR)

    if not resolved_path.startswith(vault_base) or not os.path.exists(resolved_path):
        return jsonify({"status": "error", "message": "Stored document file could not be found."}), 404

    response = make_response(send_file(
        resolved_path,
        mimetype=doc["mime_type"],
        as_attachment=True,
        download_name=doc["original_filename"]
    ))
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, no-cache, no-store, must-revalidate"
    return response


@app.route("/api/vault/document/<int:doc_id>", methods=["DELETE"])
@app.route("/api/vault/document/<int:doc_id>/delete", methods=["POST"])
@login_required
@premium_required
def api_delete_vault_document(doc_id):
    """
    Deletes a student's own document and cleans up the stored file from disk.
    Enforces authenticated user ownership.
    """
    user_id = session.get("user_id")
    deleted = delete_user_document(user_id, doc_id)

    if not deleted:
        return jsonify({"status": "error", "message": "Document not found or access denied."}), 404

    _remove_vault_file_from_disk(deleted["storage_key"])

    return jsonify({
        "status": "success",
        "message": f"'{deleted['document_type']}' removed successfully.",
        "doc_id": doc_id,
        "document_type": deleted["document_type"]
    })


# ==================================================
# HOME PAGE
# ==================================================

@app.route("/")
def home():
    districts = get_all_districts()
    branches = get_all_branches()
    colleges = get_all_colleges()

    return render_template(
        "landing.html",
        districts=districts,
        branches=branches,
        colleges=colleges,
        communities=["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"],
        years=[2025, 2024, 2023]
    )
# ==================================================
# ADMISSION PLANNER
# ==================================================

@app.route("/planner")
def planner():

    # Load data from database
    districts = get_all_districts()
    branches = get_all_branches()

    # Community Categories
    communities = [
        "OC",
        "BC",
        "BCM",
        "MBC",
        "SC",
        "SCA",
        "ST"
    ]

    # Available Years
    years = [
        2025,
        2024,
        2023
    ]

    # Pre-population from query params (e.g. from Career Guidance links)
    selected_branch = request.args.get("branch", "").strip().upper()
    selected_cutoff = request.args.get("cutoff", "").strip()
    selected_community = request.args.get("community", "").strip().upper()
    selected_district = request.args.get("district", "").strip()

    user_id = session.get("user_id")
    profile = get_student_profile(user_id) if user_id else None

    # Fallback to saved profile if query params are not provided
    if not selected_cutoff and profile:
        selected_cutoff = f"{profile.get('cutoff', 0):.2f}"
    if not selected_community and profile:
        selected_community = str(profile.get("community", "OC"))
    if not selected_district and profile:
        selected_district = str(profile.get("preferred_district", ""))

    return render_template(
        "planner.html",
        districts=districts,
        branches=branches,
        communities=communities,
        years=years,
        selected_branch=selected_branch,
        selected_cutoff=selected_cutoff,
        selected_community=selected_community,
        selected_district=selected_district,
        profile=profile
    )
# ==================================================
# GENERATE RECOMMENDATIONS
# ==================================================

@app.route("/recommend", methods=["POST"])
def recommend_route():

    try:

        cutoff = float(request.form["cutoff"])
        community = request.form["community"]
        branch = request.form["branch"]
        district = request.form.get("district", "")
        year = int(request.form["year"])

        # ── Cutoff range validation ────────────────────────────────
        if cutoff < 0 or cutoff > 200:
            districts = get_all_districts()
            branches  = get_all_branches()
            return render_template(
                "planner.html",
                districts=districts,
                branches=branches,
                communities=["OC","BC","BCM","MBC","SC","SCA","ST"],
                years=[2025, 2024, 2023],
                validation_error="Please enter a cutoff value between 0 and 200."
            )

        recommendations = recommend(
            cutoff=cutoff,
            community=community,
            branch_code=branch,
            district=district if district else None,
            year=year
        )

        return render_template(
            "result.html",
            recommendations=recommendations,
            cutoff=cutoff,
            community=community,
            branch=branch,
            district=district,
            year=year
        )

    except Exception as e:
        print("=" * 60)
        print("ERROR:")
        print(e)
        print("=" * 60)
        raise
    # ==================================================
# COLLEGE SEARCH
# ==================================================

@app.route("/search")
def search():
    query      = request.args.get("q", "").strip()
    district   = request.args.get("district", "").strip()
    autonomous = request.args.get("autonomous", "").strip().lower()
    hostel     = request.args.get("hostel", "").strip().lower()
    transport  = request.args.get("transport", "").strip().lower()

    results  = search_colleges(query, district, autonomous, hostel, transport)
    districts = get_search_districts()

    return render_template(
        "search.html",
        results=results,
        total=len(results),
        query=query,
        district=district,
        autonomous=autonomous,
        hostel=hostel,
        transport=transport,
        districts=districts
    )

# ==================================================
# COLLEGE DETAILS
# ==================================================

@app.route("/college/<int:college_code>")
def college_details(college_code):

    college = get_college_details(college_code)

    if college is None:

        return "College Not Found", 404

    branches = get_college_branches(college_code)

    return render_template(
        "college.html",
        college=college,
        branches=branches
    )
# ==================================================
# COMPARE COLLEGES
# ==================================================

def _build_comparison_summary(*args, **kwargs):
    """
    Build a plain-English summary list by comparing college records and branch lists.
    Supports either:
      - (colleges_list, branches_list)
      - (c1, c2, branches1, branches2) [legacy compatibility]
    No external API used. All text is derived purely from database values.
    """
    if len(args) == 4:
        colleges = [args[0], args[1]]
        branches_list = [args[2], args[3]]
    elif len(args) >= 2 and isinstance(args[0], list):
        colleges = args[0]
        branches_list = args[1]
    elif "colleges" in kwargs:
        colleges = kwargs["colleges"]
        branches_list = kwargs.get("branches_list", [])
    else:
        return []

    if not colleges or len(colleges) < 2:
        return []

    def get_field(c, key, default=None):
        if c is None:
            return default
        try:
            val = c[key]
            return val if val is not None else default
        except (KeyError, IndexError, TypeError):
            return default

    names = [get_field(c, "college_name") or f"College {get_field(c, 'college_code')}" for c in colleges]
    n = len(colleges)
    summary = []

    def is_yes(val):
        return str(val or "").strip().lower() == "yes"

    # ── Autonomous ────────────────────────────────────────────────────
    auto_flags = [is_yes(get_field(c, "autonomous")) for c in colleges]
    auto_count = sum(auto_flags)
    if auto_count == n:
        summary.append(f"All {n} colleges hold autonomous status.")
    elif auto_count == 0:
        summary.append("None of the selected colleges hold autonomous status.")
    else:
        auto_names = [names[i] for i, flag in enumerate(auto_flags) if flag]
        if n == 2:
            non_auto = [names[i] for i, flag in enumerate(auto_flags) if not flag][0]
            summary.append(f"{auto_names[0]} is autonomous, while {non_auto} is not.")
        else:
            summary.append(f"Autonomous status ({auto_count} of {n}): {', '.join(auto_names)}.")

    # ── Transport ─────────────────────────────────────────────────────
    tr_flags = [is_yes(get_field(c, "transport")) for c in colleges]
    tr_count = sum(tr_flags)
    if tr_count == n:
        summary.append(f"All {n} colleges provide transport facilities.")
    elif tr_count == 0:
        summary.append("None of the selected colleges offer transport facilities.")
    else:
        tr_names = [names[i] for i, flag in enumerate(tr_flags) if flag]
        if n == 2:
            summary.append(f"Only {tr_names[0]} provides transport facilities.")
        else:
            summary.append(f"Transport facilities available at: {', '.join(tr_names)}.")

    # ── Boys Hostel ───────────────────────────────────────────────────
    bh_flags = [is_yes(get_field(c, "hostel_boys")) for c in colleges]
    bh_count = sum(bh_flags)
    if bh_count == n:
        summary.append(f"All {n} colleges offer boys hostel accommodation.")
    elif bh_count == 0:
        summary.append("None of the selected colleges offer boys hostel accommodation.")
    else:
        bh_names = [names[i] for i, flag in enumerate(bh_flags) if flag]
        if n == 2:
            summary.append(f"Only {bh_names[0]} provides a boys hostel.")
        else:
            summary.append(f"Boys hostel available at: {', '.join(bh_names)}.")

    # ── Girls Hostel ──────────────────────────────────────────────────
    gh_flags = [is_yes(get_field(c, "hostel_girls")) for c in colleges]
    gh_count = sum(gh_flags)
    if gh_count == n:
        summary.append(f"All {n} colleges offer girls hostel accommodation.")
    elif gh_count == 0:
        summary.append("None of the selected colleges offer girls hostel accommodation.")
    else:
        gh_names = [names[i] for i, flag in enumerate(gh_flags) if flag]
        if n == 2:
            summary.append(f"Only {gh_names[0]} provides a girls hostel.")
        else:
            summary.append(f"Girls hostel available at: {', '.join(gh_names)}.")

    # ── District ──────────────────────────────────────────────────────
    districts = [(get_field(c, "district") or "").strip().title().replace(" District", "") for c in colleges]
    unique_districts = sorted(list(set(d for d in districts if d)))
    if len(unique_districts) == 1 and unique_districts[0]:
        summary.append(f"All selected colleges are located in {unique_districts[0]} district.")
    elif len(unique_districts) > 1:
        if n == 2:
            summary.append(f"{names[0]} is in {districts[0]} district, while {names[1]} is in {districts[1]} district.")
        else:
            summary.append(f"Districts represented: {', '.join(unique_districts)}.")

    # ── Branch count ──────────────────────────────────────────────────
    branch_counts = [len(b) if isinstance(b, list) else 0 for b in branches_list]
    if len(branch_counts) == n:
        if all(cnt == branch_counts[0] for cnt in branch_counts):
            summary.append(f"All selected colleges offer the same number of branches ({branch_counts[0]}).")
        else:
            max_c = max(branch_counts)
            max_colleges = [names[i] for i, cnt in enumerate(branch_counts) if cnt == max_c]
            if n == 2:
                if branch_counts[0] > branch_counts[1]:
                    summary.append(f"{names[0]} offers more branches ({branch_counts[0]}) than {names[1]} ({branch_counts[1]}).")
                else:
                    summary.append(f"{names[1]} offers more branches ({branch_counts[1]}) than {names[0]} ({branch_counts[0]}).")
            else:
                summary.append(f"Branch offerings: {', '.join(f'{names[i]} ({branch_counts[i]})' for i in range(n))}. {', '.join(max_colleges)} offers the highest number of branches ({max_c}).")

    return summary


@app.route("/compare")
def compare():
    user_id = session.get("user_id")
    user = get_user_by_id(user_id) if user_id else None
    is_premium = bool(user and user.get("is_premium"))
    max_limit = 5 if is_premium else 2

    # Collect college IDs preserving order and deduplicating
    college_raw_list = []

    # 1. Check college1 .. college5
    for i in range(1, 6):
        val = request.args.get(f"college{i}", "").strip()
        if val and val not in college_raw_list:
            college_raw_list.append(val)

    # 2. Check repeated 'college' or 'colleges' args or comma-separated lists
    for key in ("college", "colleges"):
        for arg in request.args.getlist(key):
            for part in arg.split(","):
                part = part.strip()
                if part and part not in college_raw_list:
                    college_raw_list.append(part)

    # If no parameters provided at all
    if not college_raw_list:
        return render_template(
            "compare.html",
            error="Select 2 or more colleges from search or recommendations to compare.",
            is_premium=is_premium,
            max_limit=max_limit,
            college1=None,
            college2=None,
            branches1=[],
            branches2=[],
            comparison_summary=[],
            colleges=[]
        )

    # Minimum check: at least 2 colleges required
    if len(college_raw_list) < 2:
        return render_template(
            "compare.html",
            error="Please select at least 2 colleges to compare side-by-side.",
            is_premium=is_premium,
            max_limit=max_limit,
            college1=None,
            college2=None,
            branches1=[],
            branches2=[],
            comparison_summary=[],
            colleges=[]
        )

    # Server-side limit enforcement:
    if not is_premium and len(college_raw_list) > 2:
        return render_template(
            "compare.html",
            error="Free accounts can compare up to 2 colleges at a time. Upgrade to Premium to compare up to 5 colleges simultaneously.",
            upgrade_required=True,
            is_premium=is_premium,
            max_limit=max_limit,
            college1=None,
            college2=None,
            branches1=[],
            branches2=[],
            comparison_summary=[],
            colleges=[]
        )

    if is_premium and len(college_raw_list) > 5:
        return render_template(
            "compare.html",
            error="You can compare a maximum of 5 colleges at once.",
            is_premium=is_premium,
            max_limit=max_limit,
            college1=None,
            college2=None,
            branches1=[],
            branches2=[],
            comparison_summary=[],
            colleges=[]
        )

    # Validate all codes are integers
    college_codes = []
    for raw in college_raw_list:
        try:
            college_codes.append(int(raw))
        except ValueError:
            return render_template(
                "compare.html",
                error="College codes must be valid integers.",
                is_premium=is_premium,
                max_limit=max_limit,
                college1=None,
                college2=None,
                branches1=[],
                branches2=[],
                comparison_summary=[],
                colleges=[]
            )

    # Fetch college details and branches
    colleges_list = []
    branches_list = []
    for code in college_codes:
        col = get_college_details(code)
        if col is None:
            return render_template(
                "compare.html",
                error=f"College with code {code} was not found.",
                is_premium=is_premium,
                max_limit=max_limit,
                college1=None,
                college2=None,
                branches1=[],
                branches2=[],
                comparison_summary=[],
                colleges=[]
            )
        brs = get_college_branches(code)
        colleges_list.append(col)
        branches_list.append(brs)

    # Build comparison summary
    comparison_summary = _build_comparison_summary(colleges_list, branches_list)

    return render_template(
        "compare.html",
        colleges=colleges_list,
        branches_list=branches_list,
        comparison_summary=comparison_summary,
        is_premium=is_premium,
        max_limit=max_limit,
        # backward compatibility variables:
        college1=colleges_list[0] if len(colleges_list) > 0 else None,
        college2=colleges_list[1] if len(colleges_list) > 1 else None,
        branches1=branches_list[0] if len(branches_list) > 0 else [],
        branches2=branches_list[1] if len(branches_list) > 1 else []
    )

# ==================================================
# ANALYTICS PAGE
# ==================================================

@app.route("/analytics")
def analytics():

    from models.database import get_connection

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Total colleges
        cursor.execute("SELECT COUNT(*) FROM colleges")
        total_colleges = cursor.fetchone()[0]

        # Total cutoff records for verified colleges
        cursor.execute("""
            SELECT COUNT(*) 
            FROM cutoffs ct
            JOIN colleges c ON c.college_code = ct.college_code
        """)
        total_cutoffs = cursor.fetchone()[0]

        # Total unique branches for verified colleges
        cursor.execute("""
            SELECT COUNT(DISTINCT b.branch_code) 
            FROM branches b
            JOIN colleges c ON c.college_code = b.college_code
        """)
        total_branches = cursor.fetchone()[0]

        # Cutoff records per year for verified colleges
        cursor.execute("""
            SELECT ct.year, COUNT(*) as count
            FROM cutoffs ct
            JOIN colleges c ON c.college_code = ct.college_code
            GROUP BY ct.year
            ORDER BY ct.year
        """)
        cutoffs_by_year = [dict(r) for r in cursor.fetchall()]

        # Top 10 districts by college count (using clean district from college_info)
        cursor.execute("""
            SELECT ci.district, COUNT(*) as count
            FROM colleges c
            JOIN college_info ci ON ci.college_code = c.college_code
            WHERE ci.district IS NOT NULL 
              AND ci.district != '' 
              AND ci.district != '- 642 120.'
            GROUP BY ci.district
            ORDER BY count DESC
            LIMIT 10
        """)
        top_districts = [{"district": r["district"].strip().title(), "count": r["count"]} for r in cursor.fetchall()]

        # Top 10 branches by college count for verified colleges
        cursor.execute("""
            SELECT b.branch_name, COUNT(DISTINCT b.college_code) as count
            FROM branches b
            JOIN colleges c ON c.college_code = b.college_code
            GROUP BY b.branch_name
            ORDER BY count DESC
            LIMIT 10
        """)
        top_branches = [{"branch_name": r["branch_name"].strip().title(), "count": r["count"]} for r in cursor.fetchall()]

        # Average OC cutoff per year for verified colleges
        cursor.execute("""
            SELECT ct.year, ROUND(AVG(ct.oc), 2) as avg_oc
            FROM cutoffs ct
            JOIN colleges c ON c.college_code = ct.college_code
            WHERE ct.oc IS NOT NULL
            GROUP BY ct.year
            ORDER BY ct.year
        """)
        avg_cutoff_by_year = [dict(r) for r in cursor.fetchall()]

        # Autonomous stats for verified colleges
        cursor.execute("""
            SELECT ci.autonomous, COUNT(*) as count
            FROM college_info ci
            JOIN colleges c ON c.college_code = ci.college_code
            WHERE ci.autonomous IS NOT NULL
            GROUP BY ci.autonomous
            ORDER BY ci.autonomous DESC
        """)
        autonomous_stats = [{"autonomous": r["autonomous"].strip().title() if r["autonomous"] else "Unknown", "count": r["count"]} for r in cursor.fetchall()]

        # Hostel boys stats for verified colleges
        cursor.execute("""
            SELECT ci.hostel_boys, COUNT(*) as count
            FROM college_info ci
            JOIN colleges c ON c.college_code = ci.college_code
            WHERE ci.hostel_boys IS NOT NULL
            GROUP BY ci.hostel_boys
            ORDER BY ci.hostel_boys DESC
        """)
        hostel_boys_stats = [{"hostel_boys": r["hostel_boys"].strip().title() if r["hostel_boys"] else "Unknown", "count": r["count"]} for r in cursor.fetchall()]

        # Hostel girls stats for verified colleges
        cursor.execute("""
            SELECT ci.hostel_girls, COUNT(*) as count
            FROM college_info ci
            JOIN colleges c ON c.college_code = ci.college_code
            WHERE ci.hostel_girls IS NOT NULL
            GROUP BY ci.hostel_girls
            ORDER BY ci.hostel_girls DESC
        """)
        hostel_girls_stats = [{"hostel_girls": r["hostel_girls"].strip().title() if r["hostel_girls"] else "Unknown", "count": r["count"]} for r in cursor.fetchall()]

        # Transport stats for verified colleges
        cursor.execute("""
            SELECT ci.transport, COUNT(*) as count
            FROM college_info ci
            JOIN colleges c ON c.college_code = ci.college_code
            WHERE ci.transport IS NOT NULL
            GROUP BY ci.transport
            ORDER BY ci.transport DESC
        """)
        transport_stats = [{"transport": r["transport"].strip().title() if r["transport"] else "Unknown", "count": r["count"]} for r in cursor.fetchall()]

        conn.close()

        return render_template(
            "analytics.html",
            total_colleges=total_colleges,
            total_cutoffs=total_cutoffs,
            total_branches=total_branches,
            cutoffs_by_year=cutoffs_by_year,
            top_districts=top_districts,
            top_branches=top_branches,
            avg_cutoff_by_year=avg_cutoff_by_year,
            autonomous_stats=autonomous_stats,
            hostel_boys_stats=hostel_boys_stats,
            hostel_girls_stats=hostel_girls_stats,
            transport_stats=transport_stats
        )

    except Exception as e:
        print("Analytics error:", e)
        return render_template(
            "analytics.html",
            total_colleges=None,
            total_cutoffs=None,
            total_branches=None,
            cutoffs_by_year=[],
            top_districts=[],
            top_branches=[],
            avg_cutoff_by_year=[],
            autonomous_stats=[],
            hostel_boys_stats=[],
            hostel_girls_stats=[],
            transport_stats=[],
            error="Analytics data could not be loaded."
        )

# ==================================================
# COLLEGE TREND ANALYSIS
# ==================================================

@app.route("/trend")
def trend():
    from models.database import get_connection

    college_code = request.args.get("college_code", "", type=str).strip()
    branch_code  = request.args.get("branch_code",  "", type=str).strip()
    community    = request.args.get("community",    "OC", type=str).strip().upper()

    # Map community to cutoff column
    community_columns = {
        "OC": "oc", "BC": "bc", "BCM": "bcm",
        "MBC": "mbc", "SC": "sc", "SCA": "sca", "ST": "st"
    }
    communities = ["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"]
    col = community_columns.get(community, "oc")

    colleges = get_all_colleges()
    branches = get_all_branches()

    trend_data = []
    college_name    = ""
    branch_name     = ""
    trend_direction = ""

    if college_code and branch_code:
        try:
            conn   = get_connection()
            cursor = conn.cursor()

            # Use parameterised column via safe whitelist lookup
            cursor.execute(f"""
                SELECT ct.year,
                       ct.{col} AS cutoff,
                       c.college_name,
                       b.branch_name
                FROM cutoffs ct
                JOIN colleges c ON c.college_code = ct.college_code
                JOIN branches b ON b.college_code = ct.college_code
                             AND b.branch_code  = ct.branch_code
                WHERE ct.college_code = ?
                  AND ct.branch_code  = ?
                  AND ct.{col} IS NOT NULL
                ORDER BY ct.year
            """, (college_code, branch_code))

            rows = cursor.fetchall()
            conn.close()

            if rows:
                college_name = rows[0]["college_name"]
                branch_name  = rows[0]["branch_name"]
                trend_data   = [{"year": r["year"], "cutoff": r["cutoff"]} for r in rows]

                values = [r["cutoff"] for r in trend_data]
                if len(values) >= 2:
                    diff = values[-1] - values[0]
                    if diff > 0.5:
                        trend_direction = "Increasing"
                    elif diff < -0.5:
                        trend_direction = "Decreasing"
                    else:
                        trend_direction = "Stable"

        except Exception as e:
            print("Trend error:", e)

    return render_template(
        "trend.html",
        colleges=colleges,
        branches=branches,
        communities=communities,
        trend_data=trend_data,
        college_code=college_code,
        branch_code=branch_code,
        community=community,
        college_name=college_name,
        branch_name=branch_name,
        trend_direction=trend_direction
    )

# ==================================================
# RUN APPLICATION
# ==================================================

if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )