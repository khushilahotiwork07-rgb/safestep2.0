"""
patients.py — Patient data hub for SafeStep.
5 complete, clinically detailed patient profiles with live enrichment.
"""

# ── Canonical 5-patient roster ─────────────────────────────────────────────────
PATIENTS: list[dict] = [
    {
        "id":            1,
        "name":          "Mr. Rajesh Sharma",
        "age":           78,
        "gender":        "Male",
        "ward":          "Ward A",
        "bed":           "Bed 4",
        "admitted_on":   "3 days ago",
        "frailty_index": "5/9 — Moderately Frail",
        "epa_frat":      "Medium Risk",
        "diagnosis":     "Moderately frail, hypertension, gait instability",
        "medications":   "BP medication, daily multivitamins",
        "mobility":      "Uses walker with minimal assistance",
        "toileting":     "Moderate urgency — sometimes needs help at night",
        "confusion":     "Mild disorientation occasional",
        "fall_history":  "No previous falls",
        "scenario":      "deteriorating",
    },
    {
        "id":            2,
        "name":          "Mrs. Sunita Patel",
        "age":           65,
        "gender":        "Female",
        "ward":          "Ward A",
        "bed":           "Bed 7",
        "admitted_on":   "1 day ago",
        "frailty_index": "5/9 — Moderately Frail",
        "epa_frat":      "Medium Risk",
        "diagnosis":     "Moderate frailty, post-op recovery",
        "medications":   "Sleeping pills given at 9 PM, blood thinners",
        "mobility":      "Uses walker independently",
        "toileting":     "Moderate urgency — can go alone but slow",
        "confusion":     "Mild confusion in early morning",
        "fall_history":  "No previous falls",
        "scenario":      "fluctuating",
    },
    {
        "id":            3,
        "name":          "Mr. Arjun Khan",
        "age":           71,
        "gender":        "Male",
        "ward":          "Ward B",
        "bed":           "Bed 2",
        "admitted_on":   "5 days ago",
        "frailty_index": "4/9 — Mildly Frail",
        "epa_frat":      "Medium Risk",
        "diagnosis":     "Diabetes mellitus type 2, mild neuropathy",
        "medications":   "Insulin (diabetic), diuretics",
        "mobility":      "Walks independently but slowly",
        "toileting":     "Frequent urgency due to diuretics — goes alone",
        "confusion":     "Fully alert",
        "fall_history":  "No previous falls",
        "scenario":      "stable",
    },
    {
        "id":            4,
        "name":          "Mrs. Priya Gupta",
        "age":           58,
        "gender":        "Female",
        "ward":          "Ward B",
        "bed":           "Bed 1",
        "admitted_on":   "2 days ago",
        "frailty_index": "2/9 — Minimally Frail",
        "epa_frat":      "Low Risk",
        "diagnosis":     "Minimally frail, post-procedure observation",
        "medications":   "Mild pain medication",
        "mobility":      "Fully independent",
        "toileting":     "Normal — no urgency",
        "confusion":     "Fully alert",
        "fall_history":  "No previous falls",
        "scenario":      "stable",
    },
    {
        "id":            5,
        "name":          "Mr. Hardev Singh",
        "age":           82,
        "gender":        "Male",
        "ward":          "Ward C",
        "bed":           "Bed 3",
        "admitted_on":   "7 days ago",
        "frailty_index": "7/9 — Severely Frail",
        "epa_frat":      "High Risk",
        "diagnosis":     "Severe frailty, diabetes, cardiac condition, fall history",
        "medications":   "Sedatives, BP medication, insulin",
        "mobility":      "Needs full assistance — mostly bedridden",
        "toileting":     "High urgency — fully dependent on nurse",
        "confusion":     "Severe disorientation — agitated at night",
        "fall_history":  "Fell twice in past year",
        "scenario":      "high_risk",
    },
]


from database import get_all_patients_db, insert_patient

def get_all_patients() -> list[dict]:
    pats = get_all_patients_db()
    # Normalize keys if necessary (db uses patient_id, UI expects id)
    for p in pats:
        if "id" not in p and "patient_id" in p:
            p["id"] = p["patient_id"]
        # Map bed_number to ward/bed for UI compatibility
        if "bed_number" in p:
            parts = p["bed_number"].split(" ", 1)
            p["ward"] = parts[0] if len(parts) > 0 else "Ward"
            p["bed"] = parts[1] if len(parts) > 1 else "?"
        # Map other fields
        p["admitted_on"] = p.get("admitted_date", "Unknown")
        p["mobility"] = p.get("mobility_status")
        p["toileting"] = p.get("toileting_urgency")
        p["confusion"] = p.get("confusion_score")
        p["epa_frat"] = p.get("frat_score", "Low Risk")
        p["base_risk_category"] = p.get("base_risk_category", "Low Risk")
        p["has_osteoporosis"] = bool(p.get("has_osteoporosis", 0))
        p["has_epilepsy"] = bool(p.get("has_epilepsy", 0))
    return pats

def get_patient_by_id(patient_id: int) -> dict | None:
    pats = get_all_patients()
    for p in pats:
        if p["id"] == patient_id:
            return p
    return None

def seed_patients_if_empty():
    if not get_all_patients_db():
        for p in PATIENTS:
            # Ensure new keys exist for seed data
            if "has_osteoporosis" not in p: p["has_osteoporosis"] = False
            if "has_epilepsy" not in p: p["has_epilepsy"] = False
            insert_patient(p)

def _enrich_patient(raw: dict, vitals, prev_vitals=None,
                    last_nurse_visit=None, include_components: bool = False) -> dict:
    """Attach live risk scoring + vitals to a copy of a patient dict."""
    from scoring import calculate_risk_score
    from alerts import ALERT_ICONS

    p = raw.copy()

    if vitals:
        result = calculate_risk_score(
            patient               = p,
            current_vitals        = vitals,
            prev_vitals           = prev_vitals,
            last_nurse_visit_time = last_nurse_visit,
        )
        p["risk_score"]  = result["final_score"]
        p["risk_level"]  = result["risk_level"]
        p["risk_color"]  = result["risk_color"]
        p["risk_icon"]   = ALERT_ICONS.get(result["risk_level"], "⚪")
        p["warnings"]    = result["warnings"]
        p["recs"]        = result["recommendations"]
        p["reasons"]     = result["reasons"]
        p["vitals"]      = vitals
        p["score_breakdown"] = {
            "baseline": result["baseline_score"],
            "dynamic":  result["dynamic_score"],
            "time":     result["time_score"],
        }
        if include_components:
            p["components"] = result["components"]
    else:
        p["risk_score"]  = None
        p["risk_level"]  = "Pending"
        p["risk_color"]  = "#9CA3AF"
        p["risk_icon"]   = "⏳"
        p["warnings"]    = []
        p["recs"]        = []
        p["reasons"]     = []
        p["vitals"]      = None
        p["score_breakdown"] = {}
        if include_components:
            p["components"] = {}

    return p


def get_patients_with_status() -> list[dict]:
    from database import get_latest_vitals, get_vitals_last_hour, get_last_nurse_visit_time
    result = []
    pats = get_all_patients()
    for raw in pats:
        vitals      = get_latest_vitals(raw["id"])
        history     = get_vitals_last_hour(raw["id"])
        prev_vitals = history[-2] if len(history) >= 2 else None
        last_visit  = get_last_nurse_visit_time(raw["id"])
        result.append(_enrich_patient(raw, vitals, prev_vitals, last_visit))
    return result


def get_patient_detail(patient_id: int) -> dict | None:
    from database import get_latest_vitals, get_vitals_last_hour, get_last_nurse_visit_time
    raw = get_patient_by_id(patient_id)
    if not raw:
        return None
    vitals      = get_latest_vitals(patient_id)
    history     = get_vitals_last_hour(patient_id)
    prev_vitals = history[-2] if len(history) >= 2 else None
    last_visit  = get_last_nurse_visit_time(patient_id)
    return _enrich_patient(raw, vitals, prev_vitals, last_visit, include_components=True)
