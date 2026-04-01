"""
alerts.py — Alert management system for SafeStep.
Handles generating, storing, displaying, and tracking nurse responses.
"""

import uuid
from datetime import datetime, date
from database import insert_alert, update_alert_response, get_todays_alerts

ALERT_ICONS = {
    "Critical":  "🔴",
    "High Risk": "🟠",
    "Watch":     "🟡",
    "Safe":      "🟢",
}

ALERT_COLORS = {
    "Critical":  "#D64045",
    "High Risk": "#E87B35",
    "Watch":     "#C4A000",
    "Safe":      "#3DAA6F",
}

ALERT_BG = {
    "Critical":  "#FFF0F0",
    "High Risk": "#FFF5EE",
    "Watch":     "#FFFBEA",
    "Safe":      "#F0FBF5",
}

class AlertSystem:
    def __init__(self):
        # In-memory alert cache mapping alert_id -> alert_dict
        self._alerts: dict[str, dict] = {}
        # Track last fired score per patient to prevent spam
        self._last_fired_score: dict[int, int] = {}
        self._last_fired_level: dict[int, str] = {}
        self._LEVEL_ORDER = {"Safe": 0, "Watch": 1, "High Risk": 2, "Critical": 3}

        # Initialize from DB on startup
        db_active = get_todays_alerts()
        for a in db_active:
            if not a.get("is_responded"):
                self._alerts[a["alert_id"]] = a

    def _get_recommendation(self, risk_level: str) -> str:
        if risk_level == "Critical":
            return "Go immediately. Check vitals manually. Do not leave patient unattended. Assist with positioning. Raise all bed rails. Consider moving patient closer to nursing station."
        elif risk_level == "High Risk":
            return "Visit patient soon. Check vitals manually. Assist with any toileting needs. Ensure call button is within reach."
        elif risk_level == "Watch":
            return "Plan a check-in visit within the next 30 minutes. Verify bed rails are up."
        return ""

    def check_and_fire_alerts(self, patient: dict, risk_score_result: dict):
        pid = patient["id"]
        current_score = risk_score_result["final_score"]
        current_level = risk_score_result["risk_level"]

        if current_level == "Safe":
            # Reset tracking if patient is safe
            self._last_fired_score[pid] = current_score
            self._last_fired_level[pid] = current_level
            return

        last_score = self._last_fired_score.get(pid, 0)
        last_level = self._last_fired_level.get(pid, "Safe")

        level_escalated = self._LEVEL_ORDER.get(current_level, 0) > self._LEVEL_ORDER.get(last_level, 0)
        score_jumped = (current_score - last_score) >= 15

        if level_escalated or score_jumped:
            # Fire an alert!
            alert_id = str(uuid.uuid4())
            ts = datetime.now()
            
            # Extract top 3 unique reasons prioritizing dynamic/warnings
            reasons = list(dict.fromkeys(risk_score_result["warnings"] + risk_score_result["reasons"]))
            top_3_reasons = reasons[:3]

            alert_obj = {
                "alert_id": alert_id,
                "patient_id": pid,
                "patient_name": patient["name"],
                "bed_number": patient["bed"],
                "timestamp": ts.isoformat(),
                "risk_level": current_level,
                "risk_score": current_score,
                "trigger_reasons": top_3_reasons,
                "recommended_action": self._get_recommendation(current_level),
                "is_responded": False,
                "responded_at": None,
                "responded_by": None
            }

            self._alerts[alert_id] = alert_obj
            insert_alert(alert_obj)

            # Update tracker
            self._last_fired_score[pid] = current_score
            self._last_fired_level[pid] = current_level

    def mark_alert_responded(self, alert_id: str, nurse_name: str):
        if alert_id in self._alerts:
            ts_str = datetime.now().isoformat()
            self._alerts[alert_id]["is_responded"] = True
            self._alerts[alert_id]["responded_by"] = nurse_name
            self._alerts[alert_id]["responded_at"] = ts_str
            update_alert_response(alert_id, nurse_name, ts_str)

    def get_active_alerts(self) -> list[dict]:
        """Returns all unresponded alerts sorted by risk level descending, then time."""
        active = [a for a in self._alerts.values() if not a["is_responded"]]
        active.sort(key=lambda x: (
            -self._LEVEL_ORDER.get(x["risk_level"], 0),
            x["timestamp"]
        ), reverse=True) # Sort descending by level, then time
        # Handle the sort properly: critical=3, high=2, watch=1
        active.sort(key=lambda x: (-self._LEVEL_ORDER.get(x["risk_level"], 0), x["timestamp"]))
        return active

    def get_alert_history(self) -> list[dict]:
        """Returns all alerts from today sorted by most recent first."""
        history = get_todays_alerts()
        today_str = date.today().isoformat()
        
        # Filter for today
        today_alerts = [a for a in history if a["timestamp"].startswith(today_str)]
        
        # Sort most recent first
        today_alerts.sort(key=lambda x: x["timestamp"], reverse=True)
        return today_alerts

    def get_alert_count_by_level(self) -> dict:
        counts = {"Critical": 0, "High Risk": 0, "Watch": 0}
        active = self.get_active_alerts()
        for a in active:
            if a["risk_level"] in counts:
                counts[a["risk_level"]] += 1
        return counts

# Global singleton
_alert_system_instance = None

def get_alert_system() -> AlertSystem:
    global _alert_system_instance
    if _alert_system_instance is None:
        _alert_system_instance = AlertSystem()
    return _alert_system_instance


# Helper functions mapped to the singleton for easy import
def format_alert_badge(risk_level: str) -> str:
    """Return an HTML coloured badge for the risk level."""
    icon  = ALERT_ICONS.get(risk_level, "⚪")
    color = ALERT_COLORS.get(risk_level, "#999")
    return f'<span style="color:{color};font-weight:700;">{icon} {risk_level}</span>'

def get_unacknowledged_count() -> int:
    return len(get_alert_system().get_active_alerts())
