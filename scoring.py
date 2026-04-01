"""
scoring.py — Clinical Fall Risk Scoring Engine for SafeStep.

Three-part weighted rule-based scoring system based on:
  - EPA Falls Risk Assessment Tool (FRAT)
  - Clinical Frailty Index research
  - Time-based clinical fall-risk patterns

No machine learning. No training data. Pure evidence-based medical logic.
"""

from datetime import datetime
from typing import Optional


# ── Risk level thresholds (0–100 scale) ───────────────────────────────────────
#   0–40  = Safe
#  41–65  = Watch
#  66–85  = High Risk
#  86–100 = Critical

RISK_THRESHOLDS = [
    (86, "Critical",  "#D64045"),
    (66, "High Risk", "#E87B35"),
    (41, "Watch",     "#C4A000"),
    ( 0, "Safe",      "#3DAA6F"),
]

RISK_COLORS = {
    "Critical":  "#D64045",
    "High Risk": "#E87B35",
    "Watch":     "#C4A000",
    "Safe":      "#3DAA6F",
}

RISK_BG = {
    "Critical":  "#FFF0F0",
    "High Risk": "#FFF5EE",
    "Watch":     "#FFFBEA",
    "Safe":      "#F0FBF5",
}


def _get_risk_level(score: int) -> tuple[str, str]:
    for threshold, level, color in RISK_THRESHOLDS:
        if score >= threshold:
            return level, color
    return "Safe", "#3DAA6F"


# ── STATIC SCORING — from patient profile (never changes between readings) ────

def _static_score(patient: dict) -> tuple[int, list[str]]:
    """
    Score based on the patient's fixed clinical profile.
    Source: EPA FRAT, Clinical Frailty Scale, medication risk tables.
    """
    score   = 0
    reasons = []

    # ── Frailty Index ──────────────────────────────────────────────────────────
    frailty_str = patient.get("frailty_index", "")
    frailty_num = 0
    try:
        frailty_num = int(frailty_str.split("/")[0].strip())
    except (ValueError, IndexError, AttributeError):
        pass

    if frailty_num >= 7:
        score += 25
        reasons.append("Severely frail patient")
    elif frailty_num >= 4:
        score += 15
        reasons.append("Moderately frail patient")
    elif frailty_num >= 1:
        score += 5
        reasons.append("Mildly frail patient")

    # ── EPA FRAT assessment ────────────────────────────────────────────────────
    frat = patient.get("epa_frat", "").lower()
    if "high" in frat:
        score += 25
        reasons.append("EPA FRAT assessment: High Risk")
    elif "medium" in frat or "moderate" in frat:
        score += 15
        reasons.append("EPA FRAT assessment: Medium Risk")
    elif "low" in frat:
        score += 5
        reasons.append("EPA FRAT assessment: Low Risk")

    # ── Medications ────────────────────────────────────────────────────────────
    meds = patient.get("medications", "").lower()

    if any(k in meds for k in ["sedative", "sleeping pill", "sedating"]):
        score += 20
        reasons.append("Sedative medication increases drowsiness risk")

    if any(k in meds for k in ["bp medication", "antihypertensive",
                                "blood pressure", "antihypertensives"]):
        score += 15
        reasons.append("BP medication can cause sudden pressure drops")

    if "diuretic" in meds:
        score += 10
        reasons.append("Diuretics increase toileting urgency")

    if "insulin" in meds:
        score += 10
        reasons.append("Insulin risk of hypoglycemia")

    # ── Mobility ───────────────────────────────────────────────────────────────
    mobility = patient.get("mobility", "").lower()
    if "full assistance" in mobility:
        score += 20
        reasons.append("Requires full assistance to walk")
    elif any(k in mobility for k in ["walker", "walking aid", "cane", "frame"]):
        score += 12
        reasons.append("Uses walking aid")

    # ── Toileting urgency ──────────────────────────────────────────────────────
    toileting = patient.get("toileting", "").lower()
    if "high urgency" in toileting:
        score += 15
        reasons.append("High toileting urgency increases night fall risk")
    elif "moderate urgency" in toileting:
        score += 8
        reasons.append("Moderate toileting urgency")

    # ── Confusion / cognitive state ────────────────────────────────────────────
    confusion = patient.get("confusion", "").lower()
    if any(k in confusion for k in ["severe", "moderate"]):
        score += 15
        reasons.append("Confusion or disorientation increases fall risk")
    elif "mild" in confusion:
        score += 8
        reasons.append("Mild confusion present")

    # ── Fall history ───────────────────────────────────────────────────────────
    fall_hist = patient.get("fall_history", "").lower()
    has_falls = (
        "no previous falls" not in fall_hist
        and any(k in fall_hist for k in ["fell", "fall", "fallen"])
    )
    if has_falls:
        score += 20
        reasons.append("Patient has history of previous falls")

    return score, reasons


# ── DYNAMIC SCORING — from current live vitals ─────────────────────────────────

def _dynamic_score(
    current_vitals: dict,
    prev_vitals: Optional[dict],
) -> tuple[int, list[str]]:
    """
    Score based on current vital signs and comparison to previous reading.
    Source: NEWS2 (National Early Warning Score 2) + clinical syncope risk criteria.
    """
    score   = 0
    reasons = []

    # Normalise key names (simultor uses hr/sbp, DB uses heart_rate/systolic_bp)
    def _get(d: dict, *keys):
        for k in keys:
            if k in d and d[k] is not None:
                return float(d[k])
        return None

    hr   = _get(current_vitals, "heart_rate",   "hr")
    sbp  = _get(current_vitals, "systolic_bp",  "sbp")
    spo2 = _get(current_vitals, "spo2")
    temp = _get(current_vitals, "temperature",  "temp")
    bs   = _get(current_vitals, "blood_sugar")   # optional

    # ── Heart rate ─────────────────────────────────────────────────────────────
    if hr is not None:
        if hr > 110:
            score += 20
            reasons.append("Heart rate dangerously elevated")
        elif hr < 55:
            score += 20
            reasons.append("Heart rate dangerously low")

    # ── Blood pressure ─────────────────────────────────────────────────────────
    if sbp is not None:
        if sbp < 90:
            score += 25
            reasons.append("Blood pressure critically low — dizziness risk")

        if prev_vitals is not None:
            prev_sbp = _get(prev_vitals, "systolic_bp", "sbp")
            if prev_sbp is not None and (prev_sbp - sbp) > 20:
                score += 25
                reasons.append("Sudden blood pressure drop detected")

    # ── Oxygen saturation ──────────────────────────────────────────────────────
    if spo2 is not None and spo2 < 93:
        score += 25
        reasons.append("Oxygen level critically low")

    # ── Blood sugar ────────────────────────────────────────────────────────────
    if bs is not None and bs < 70:
        score += 30
        reasons.append("Hypoglycemia detected — extreme fall risk")

    # ── Temperature (°C; 38.9°C ≈ 102°F threshold) ────────────────────────────
    if temp is not None and temp > 38.9:
        score += 15
        reasons.append("High fever — confusion and weakness risk")

    # ── Sudden vital sign change > 20% vs last reading ────────────────────────
    if prev_vitals is not None:
        check_pairs = [
            ("heart_rate",       "hr"),
            ("spo2",             "spo2"),
            ("respiratory_rate", "rr"),
        ]
        for key_long, key_short in check_pairs:
            curr_val = _get(current_vitals, key_long, key_short)
            prev_val = _get(prev_vitals,    key_long, key_short)
            if curr_val and prev_val and prev_val > 0:
                if abs(curr_val - prev_val) / prev_val > 0.20:
                    score += 15
                    reasons.append("Sudden vital sign change detected")
                    break   # Only add this reason once

    return score, reasons


# ── TIME-BASED SCORING — from current time and nurse visit log ─────────────────

def _time_score(
    patient: dict,
    current_time: datetime,
    last_nurse_visit_time: Optional[datetime],
) -> tuple[int, list[str]]:
    """
    Score based on time-of-day patterns and time since last nurse visit.
    Source: clinical fall-incident analysis studies (most falls: 0000–0600).
    """
    score   = 0
    reasons = []
    hour    = current_time.hour

    # ── Night hours (midnight – 6 AM: highest fall risk window) ───────────────
    if 0 <= hour < 6:
        score += 15
        reasons.append("Night hours — highest fall risk window")

    # ── Time since last nurse visit ────────────────────────────────────────────
    if last_nurse_visit_time is not None:
        hours_since = (current_time - last_nurse_visit_time).total_seconds() / 3600
        if hours_since > 4:
            score += 25
            reasons.append("No nurse visit in over 4 hours")
        elif hours_since > 3:
            score += 18
            reasons.append("No nurse visit in over 3 hours")
    else:
        score += 18
        reasons.append("No nurse visit recorded in system")

    # ── Sedative peak drowsiness window ───────────────────────────────────────
    meds = patient.get("medications", "").lower()
    has_sedative = any(k in meds for k in ["sedative", "sleeping pill"])
    if has_sedative:
        # 10 PM sedative → peak effect 10 PM – midnight (hours 22, 23, 0)
        # 9 PM sleeping pill → peak 9 PM – 11 PM (hours 21, 22, 23)
        if hour in {21, 22, 23, 0}:
            score += 20
            reasons.append("Peak sedative drowsiness window active")

    # ── Patient approaching usual toileting time (within 30 min) ──────────────
    toileting = patient.get("toileting", "").lower()
    toilet_window_active = False

    # Explicit 1 AM–3 AM window (Patient 1 profile)
    if any(k in toileting for k in ["1 am", "2 am", "3 am"]):
        if hour in {0, 1, 2}:   # midnight – 3 AM
            toilet_window_active = True

    # High urgency patient + night hours = approaching toileting time
    if "high urgency" in toileting and 0 <= hour < 6:
        toilet_window_active = True

    if toilet_window_active:
        score += 15
        reasons.append("Patient approaching usual toileting time")

    return score, reasons


# ── RECOMMENDATIONS builder ────────────────────────────────────────────────────

def _build_recommendations(risk_level: str, reasons: list[str]) -> list[str]:
    recs      = []
    reason_lc = " ".join(reasons).lower()

    if risk_level == "Critical":
        recs.append("⚠️ Immediate nursing assessment — do not leave patient unattended")
        recs.append("Activate bed alarm and raise all side rails now")
        recs.append("Consider 1:1 continuous supervision")
    elif risk_level == "High Risk":
        recs.append("Increase observation frequency to every 30 minutes")
        recs.append("Ensure call bell is within reach and bed alarm is active")
    elif risk_level == "Watch":
        recs.append("2-hourly checks advised")
        recs.append("Remind patient to call for assistance before getting up")

    if "sedative" in reason_lc:
        recs.append("Monitor alertness closely — sedative peak window")
    if "toileting" in reason_lc:
        recs.append("Proactively offer toileting assistance now")
    if "blood pressure" in reason_lc or "pressure drop" in reason_lc:
        recs.append("Assist with any position changes — sit before standing")
    if "hypoglycemia" in reason_lc:
        recs.append("Check blood sugar immediately — administer glucose if needed")
    if "oxygen" in reason_lc:
        recs.append("Check oxygen supplementation and respiratory status")
    if "fall" in reason_lc and "history" in reason_lc:
        recs.append("Review fall prevention care plan with patient")

    return recs


# ── MAIN public function ───────────────────────────────────────────────────────

def calculate_risk_score(
    patient: dict,
    current_vitals: dict,
    current_time: Optional[datetime]  = None,
    last_nurse_visit_time: Optional[datetime] = None,
    prev_vitals: Optional[dict]       = None,
) -> dict:
    """
    Compute a 0–100 composite fall-risk score for one patient.

    Parameters
    ----------
    patient               : Full patient profile dict (from patients.py PATIENTS list)
    current_vitals        : Latest vitals dict (heart_rate/hr, systolic_bp/sbp,
                            diastolic_bp/dbp, spo2, temperature/temp, respiratory_rate/rr)
    current_time          : Timestamp to evaluate; defaults to datetime.now()
    last_nurse_visit_time : Datetime of the last nurse visit / handover note
    prev_vitals           : Previous vitals dict for trend/sudden-change detection

    Returns
    -------
    dict:
        final_score    (int 0–100)
        risk_level     (str: "Safe" | "Watch" | "High Risk" | "Critical")
        risk_color     (str: hex colour)
        baseline_score (int — static component from profile)
        dynamic_score  (int — live vitals component)
        time_score     (int — time-based component)
        reasons        (list[str] — every reason points were added, shown to nurses)
        warnings       (list[str] — urgent real-time warnings subset)
        recommendations(list[str] — nursing actions)
        components     (dict — for breakdown chart)
        total_score    (int — alias for final_score, backward compat)
    """
    if current_time is None:
        current_time = datetime.now()

    baseline, base_reasons = _static_score(patient)
    dynamic,  dyn_reasons  = _dynamic_score(current_vitals, prev_vitals)
    time_pts, time_reasons = _time_score(patient, current_time, last_nurse_visit_time)

    raw   = baseline + dynamic + time_pts
    final = min(raw, 100)           # Capped at 100 — cannot exceed
    level, color = _get_risk_level(final)
    all_reasons  = base_reasons + dyn_reasons + time_reasons

    return {
        "final_score":     final,
        "risk_level":      level,
        "risk_color":      color,
        "baseline_score":  min(baseline, 100),
        "dynamic_score":   min(dynamic,  100),
        "time_score":      min(time_pts, 100),
        "reasons":         all_reasons,
        "warnings":        dyn_reasons + time_reasons,
        "recommendations": _build_recommendations(level, all_reasons),
        "components": {
            "Patient Profile (Static)": baseline,
            "Live Vitals (Dynamic)":    dynamic,
            "Time Factors":             time_pts,
        },
        # Backward-compat aliases used by patients.py / vitals_simulator.py
        "total_score":  final,
        "risk_level":   level,
        "risk_color":   color,
    }
