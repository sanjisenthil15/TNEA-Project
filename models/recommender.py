"""
=========================================================
TNEA Career Insight Navigator
Redesigned Smart Recommendation Engine
=========================================================
"""

import sqlite3
import math
import statistics
from models.database import get_connection, _resolve_branch_codes, _normalize_district

CHENNAI_METRO_DISTRICTS = ["Chennai", "Chengalpattu", "Kancheepuram", "Thiruvallur", "Tiruvallur"]

# =========================================================
# ADMISSION PROBABILITY & CATEGORY
# =========================================================

def calculate_metrics(hist_dict):
    """
    hist_dict should be a dictionary like {2023: 190.5, 2024: 192.0} with only valid non-None cutoffs.
    """
    years = sorted(hist_dict.keys())
    values = [hist_dict[y] for y in years]
    
    if not values:
        return 0.0, 0.0, 0.0
        
    mean_cutoff = statistics.mean(values)
    volatility = statistics.stdev(values) if len(values) > 1 else 0.0
    
    yoy_trend_slope = 0.0
    if len(years) > 1:
        # linear regression slope: sum((x - mean_x) * (y - mean_y)) / sum((x - mean_x)**2)
        mean_y = statistics.mean(years)
        mean_v = statistics.mean(values)
        numerator = sum((y - mean_y) * (v - mean_v) for y, v in zip(years, values))
        denominator = sum((y - mean_y)**2 for y in years)
        if denominator != 0:
            yoy_trend_slope = numerator / denominator

    return mean_cutoff, volatility, yoy_trend_slope

def get_calibrated_probability(student_cutoff, latest_cutoff, yoy_trend_slope, volatility):
    diff = student_cutoff - latest_cutoff
    z = (diff * 0.85) - (yoy_trend_slope * 0.45) - (volatility * 0.25)
    
    # Fix: Ensure positive mark differences aren't over-penalized by volatility/trend
    if diff > 0 and z < 0.2:
        z = 0.2 # Guarantees minimum ~55% probability (Target Match)
        
    # Sigmoid Probability
    try:
        prob = 1.0 / (1.0 + math.exp(-z))
    except OverflowError:
        prob = 1.0 if z > 0 else 0.0
        
    # Convert to percentage and bound between 8.0% and 94.0%
    prob_pct = prob * 100.0
    prob_pct = max(8.0, min(94.0, prob_pct))
    
    # Tier Categorization
    if prob_pct >= 80.0:
        category = "Safe"
        chance = "High Probability"
    elif prob_pct >= 55.0:
        category = "Target"
        chance = "Competitive Match"
    elif prob_pct >= 35.0:
        category = "Moderate"
        chance = "Borderline"
    else:
        category = "Dream"
        chance = "Ambitious Choice"
        
    return round(prob_pct, 1), chance, category

# =========================================================
# REASON GENERATOR
# =========================================================

def generate_ai_reason(student_cutoff, latest_cutoff, chance, category, branch_match, is_autonomous, district_match, yoy_trend_slope, reference_year=2025):
    """
    Generate a natural language rationale.
    """
    difference = round(student_cutoff - latest_cutoff, 2)
    
    if difference > 0:
        intro = f"Your cutoff is {abs(difference)} marks higher than the {reference_year} closing cutoff."
    elif difference < 0:
        intro = f"Your cutoff is {abs(difference)} marks lower than the {reference_year} closing cutoff."
    else:
        intro = f"Your cutoff exactly matches the {reference_year} closing cutoff."
        
    trend_desc = "stable"
    if yoy_trend_slope > 1.0:
        trend_desc = "rising significantly"
    elif yoy_trend_slope > 0.1:
        trend_desc = "rising steadily"
    elif yoy_trend_slope < -1.0:
        trend_desc = "falling significantly"
    elif yoy_trend_slope < -0.1:
        trend_desc = "falling slightly"
        
    intro += f" Across 2023-2025, the historical cutoff trend for this branch has been {trend_desc}."
        
    advice = ""
    if category == "Dream":
        advice = "Place this as an Ambitious/Dream choice in your top 1–5 options."
    elif category == "Target":
        advice = "Place this as a Target match in choices 6–15 to maximize chances."
    elif category == "Moderate":
        advice = "Place this as a Moderate choice to balance your options."
    elif category == "Safe":
        advice = "Secure this as a Safe bet near the bottom of your choice list."
        
    notes = []
    if branch_match:
        notes.append("Matches exact preferred branch.")
    if district_match:
        notes.append("Located in your preferred district.")
    if is_autonomous:
        notes.append("Autonomous institution.")
        
    notes_str = " ".join(notes)
    if notes_str:
        return f"{intro} {advice} Features: {notes_str}"
    else:
        return f"{intro} {advice}"

# =========================================================
# RECOMMENDATION ENGINE
# =========================================================

def recommend(cutoff, community, branch_code, district=None, year=2025):
    """
    Smart Recommendation Engine with dynamic window limits, weighted ranking, and geographic constraint.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    community_columns = {
        "OC": "oc", "BC": "bc", "BCM": "bcm",
        "MBC": "mbc", "SC": "sc", "SCA": "sca", "ST": "st"
    }
    column = community_columns.get(community.upper(), "oc")
    
    # Step 1: Resolve branches and build query base
    branch_codes = _resolve_branch_codes(branch_code)
    branch_placeholders = ",".join(["?"] * len(branch_codes))
    
    # Safe Multi-Year Left Joins (No Missing Colleges)
    query = f"""
        SELECT 
            c.college_code,
            c.college_name,
            ci.district,
            c.college_type,
            ci.autonomous,
            ci.hostel_boys,
            ci.hostel_girls,
            ci.transport,
            ci.phone,
            ci.email,
            ci.website,
            b.branch_code,
            b.branch_name,
            MAX(CASE WHEN ct.year = 2025 THEN ct.{column} END) AS cutoff_2025,
            MAX(CASE WHEN ct.year = 2024 THEN ct.{column} END) AS cutoff_2024,
            MAX(CASE WHEN ct.year = 2023 THEN ct.{column} END) AS cutoff_2023
        FROM branches b
        JOIN colleges c ON c.college_code = b.college_code
        JOIN college_info ci ON ci.college_code = c.college_code
        LEFT JOIN cutoffs ct ON b.college_code = ct.college_code 
                             AND b.branch_code = ct.branch_code 
                             AND ct.year IN (2023, 2024, 2025)
        WHERE b.branch_code IN ({branch_placeholders})
    """
    params = branch_codes.copy()
    
    # Strict Canonical Normalization & Hard Filter
    if district and district.strip() and district.strip() != "All Districts":
        clean_dist = district.strip().replace("District", "").replace("Dist", "").strip()
        
        # Chennai Metro Clustering
        if clean_dist.lower() in ["chennai", "chennai region", "chennai metro"]:
            metro_placeholders = ",".join(["?"] * len(CHENNAI_METRO_DISTRICTS))
            query += f" AND UPPER(TRIM(ci.district)) IN ({metro_placeholders})"
            params.extend([d.upper() for d in CHENNAI_METRO_DISTRICTS])
        else:
            query += " AND UPPER(TRIM(ci.district)) = UPPER(TRIM(?))"
            params.append(clean_dist)
            
    query += """
        GROUP BY 
            c.college_code,
            c.college_name,
            ci.district,
            c.college_type,
            ci.autonomous,
            ci.hostel_boys,
            ci.hostel_girls,
            ci.transport,
            ci.phone,
            ci.email,
            ci.website,
            b.branch_code,
            b.branch_name
        HAVING 
            cutoff_2025 IS NOT NULL OR cutoff_2024 IS NOT NULL OR cutoff_2023 IS NOT NULL
    """
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    raw_candidates = [dict(r) for r in rows]
    
    # Generalized Dynamic Cutoff Search Window (Anchored to Reference Year)
    window = 8.0
    while True:
        lower_limit = max(50.0, cutoff - window)
        upper_limit = min(200.0, cutoff + window)
        
        filtered_candidates = []
        for col in raw_candidates:
            c_2025 = float(col["cutoff_2025"]) if col["cutoff_2025"] is not None else None
            c_2024 = float(col["cutoff_2024"]) if col["cutoff_2024"] is not None else None
            c_2023 = float(col["cutoff_2023"]) if col["cutoff_2023"] is not None else None
            
            # Dynamic Reference-Year Anchoring: Strict match for reference year
            ref_cutoff = c_2025 if year == 2025 else (c_2024 if year == 2024 else c_2023)
            
            # Skip if there is NO cutoff for the explicitly requested reference year
            if ref_cutoff is None:
                continue
                
            if lower_limit <= ref_cutoff <= upper_limit:
                filtered_candidates.append((col, ref_cutoff, c_2025, c_2024, c_2023))
        
        if len(filtered_candidates) >= 6 or window >= 14.0:
            break
        window = 14.0
        
    recommendations = []
    
    # Process each candidate and compute weighted ranking score
    for col, ref_cutoff, c_2025, c_2024, c_2023 in filtered_candidates:
        col_code = col["college_code"]
        col_branch = col["branch_code"]
        
        # Cutoff difference based on Reference Year
        diff = cutoff - ref_cutoff
        
        # 2. District Match Score
        dist_score = 0.0
        if district and district.strip() and district.strip() != "All Districts":
            clean_user_dist = _normalize_district(district)
            clean_col_dist = _normalize_district(col["district"] or "")
            if clean_user_dist == clean_col_dist or clean_user_dist in clean_col_dist or clean_col_dist in clean_user_dist:
                dist_score = 100.0
            # Also consider Chennai Metro match 
            elif clean_user_dist in ["chennai", "chennai region", "chennai metro"]:
                if any(_normalize_district(m) in clean_col_dist for m in CHENNAI_METRO_DISTRICTS):
                    dist_score = 100.0
        else:
            dist_score = 100.0
        
        # 3. Branch Match Score
        branch_score = 100.0 if col_branch.upper() == branch_code.upper() else 80.0
        
        # 4. Historical Cutoff Trend Score
        hist = {}
        if c_2023 is not None: hist[2023] = c_2023
        if c_2024 is not None: hist[2024] = c_2024
        if c_2025 is not None: hist[2025] = c_2025
        
        mean_cutoff, volatility, yoy_trend_slope = calculate_metrics(hist)
        
        # Probability & Chance Label (recalibrated to fix the penalty bug)
        prob, chance, category = get_calibrated_probability(cutoff, ref_cutoff, yoy_trend_slope, volatility)
        
        # Reason explanation
        is_auto = str(col["autonomous"] or "").strip().lower() == "yes"
        reason = generate_ai_reason(
            student_cutoff=cutoff,
            latest_cutoff=ref_cutoff,
            chance=chance,
            category=category,
            branch_match=(col_branch.upper() == branch_code.upper()),
            is_autonomous=is_auto,
            district_match=(dist_score == 100.0),
            yoy_trend_slope=yoy_trend_slope,
            reference_year=year
        )
        
        recommendations.append({
            "college_code": col_code,
            "college_name": col["college_name"],
            "district": col["district"],
            "branch_code": col_branch,
            "branch_name": col["branch_name"],
            "college_type": col["college_type"],
            "autonomous": col["autonomous"],
            "hostel_boys": col["hostel_boys"],
            "hostel_girls": col["hostel_girls"],
            "transport": col["transport"],
            "phone": col["phone"],
            "email": col["email"],
            "website": col["website"],
            "cutoff": ref_cutoff, # Primary comparison value anchored to reference year
            "student_cutoff": cutoff,
            "cutoff_difference": diff,
            "mean_cutoff": round(mean_cutoff, 2), # Retaining secondary context metrics
            "volatility": round(volatility, 2),
            "yoy_trend_slope": round(yoy_trend_slope, 2),
            "probability": prob,
            "recommendation_level": chance,
            "recommendation_category": category,
            "ai_reason": [reason],
            "cutoff_2025": c_2025,
            "cutoff_2024": c_2024,
            "cutoff_2023": c_2023
        })
        
    # Sorting key logic:
    # 1. Closest cutoff difference (abs(student_cutoff - cutoff) ascending)
    # 2. Probability descending
    def sort_key(rec):
        diff_abs = abs(rec["cutoff_difference"])
        return (diff_abs, -rec["probability"])

    # Deduplicate colleges to keep only the highest ranked record per college
    unique_colleges = {}
    for rec in recommendations:
        code = rec["college_code"]
        key_val = sort_key(rec)
        if code not in unique_colleges:
            unique_colleges[code] = (rec, key_val)
        else:
            # If this rec has a better (smaller) sort key, replace it
            if key_val < unique_colleges[code][1]:
                unique_colleges[code] = (rec, key_val)
                
    deduped_recommendations = [item[0] for item in unique_colleges.values()]
    
    # Sort by the sort key
    deduped_recommendations.sort(key=sort_key)
    
    # Verify results against rules before returning
    final_verified = []
    for rec in deduped_recommendations:
        # ✓ College exists (college_name is not empty)
        if not rec["college_name"] or rec["college_name"] == "Unknown":
            continue
        # ✓ Branch exists (branch_name is not empty)
        if not rec["branch_name"]:
            continue
        # ✓ District is valid
        if not rec["district"]:
            continue
            
        final_verified.append(rec)
        
    return final_verified
