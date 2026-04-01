"""
vitals_simulator.py — Real-time vitals simulation engine for SafeStep.
Simulates live medical device data feeding into the system every 5 seconds.
Includes scheduled clinical scenarios for demonstration purposes.
"""

import time
import random
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

from database import insert_vitals, insert_risk_score
from scoring import calculate_risk_score
from patients import get_all_patients

# Initialise start time to calculate scenario triggers
_START_TIME = datetime.now()

# Baseline vitals per patient ID (matching the required specifications)
# 1: Mr. Sharma
# 2: Mrs. Patel
# 3: Mr. Khan
# 4: Mrs. Gupta
# 5: Mr. Singh
_BASELINES = {
    1: {"hr": 82, "sbp": 118, "dbp": 78, "spo2": 96, "sugar": 110, "temp": 98.6},
    2: {"hr": 75, "sbp": 125, "dbp": 82, "spo2": 97, "sugar": 105, "temp": 98.4},
    3: {"hr": 78, "sbp": 122, "dbp": 80, "spo2": 98, "sugar": 135, "temp": 98.8},
    4: {"hr": 70, "sbp": 118, "dbp": 76, "spo2": 99, "sugar": 95,  "temp": 98.2},
    5: {"hr": 88, "sbp": 110, "dbp": 72, "spo2": 95, "sugar": 145, "temp": 99.1},
}

# In-memory history (last 5 seconds) as requested
# Format: { patient_id: [ {"timestamp": dt, "hr": ..., etc.} ] }
_MEMORY_HISTORY = {pid: [] for pid in _BASELINES.keys()}
_LEVEL_ORDER = {"Safe": 0, "Watch": 1, "High Risk": 2, "Critical": 3}


class VitalsSimulator:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self.run_simulation_tick, 'interval', seconds=5)
        # Track scenario progress
        self.scen1_step = 0
        self.scen2_step = 0
        
        # Current state initialized to baselines
        self.current_state = {pid: dict(vitals) for pid, vitals in _BASELINES.items()}

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()

    def run_simulation_tick(self):
        now = datetime.now()
        elapsed = now - _START_TIME
        
        # 1. Fetch ALL patients from the database (including newly added ones)
        from patients import get_all_patients
        patients = get_all_patients()
        
        for patient in patients:
            pid = patient["id"]
            
            # 2. If new patient, initialize their baseline and current state
            if pid not in self.current_state:
                # Assign a random variation of a standard normal baseline
                baseline = {
                    "hr": 75 + random.randint(-5, 10),
                    "sbp": 120 + random.randint(-10, 10),
                    "dbp": 80 + random.randint(-5, 5),
                    "spo2": 98 + random.randint(-2, 1),
                    "sugar": 110 + random.randint(-10, 20),
                    "temp": round(98.4 + random.uniform(-0.5, 0.5), 1)
                }
                _BASELINES[pid] = baseline
                self.current_state[pid] = dict(baseline)
                _MEMORY_HISTORY[pid] = []
            
            base = _BASELINES[pid]
            current = self.current_state[pid]
            
            # Application of normal random variation
            current["hr"] = base["hr"] + random.randint(-3, 3)
            current["sbp"] = base["sbp"] + random.randint(-5, 5)
            current["dbp"] = base["dbp"] + random.randint(-5, 5)
            current["spo2"] = min(100, max(85, base["spo2"] + random.randint(-1, 1)))
            current["sugar"] = base["sugar"] + random.randint(-5, 5)
            current["temp"] = round(base["temp"] + random.uniform(-0.2, 0.2), 1)

            # Scenario logic (shortened for demo)
            if pid == 1 and elapsed >= timedelta(seconds=20):
                if self.scen1_step == 0:
                    current["sbp"] = 98
                    current["hr"] = 98
                    self.scen1_step = 1
                elif self.scen1_step == 1:
                    current["sbp"] = 82
                    current["hr"] = 115
                    self.scen1_step = 2
                else:
                    current["sbp"] = 82 + random.randint(-2, 2)
                    current["hr"] = 115 + random.randint(-2, 2)

            if pid == 5 and elapsed >= timedelta(seconds=40):
                if self.scen2_step == 0:
                    current["sugar"] = 120
                    current["spo2"] = 93
                    self.scen2_step = 1
                elif self.scen2_step == 1:
                    current["sugar"] = 95
                    current["spo2"] = 91
                    self.scen2_step = 2
                elif self.scen2_step == 2:
                    current["sugar"] = 75
                    current["spo2"] = 90
                    self.scen2_step = 3
                elif self.scen2_step == 3:
                    current["sugar"] = 58
                    current["spo2"] = 89
                    self.scen2_step = 4
                else:
                    current["sugar"] = 58 + random.randint(-2, 2)
                    current["spo2"] = 89 + random.choice([0, -1])

            if pid == 2 and elapsed >= timedelta(seconds=60):
                current["hr"] = 124 + random.randint(-2, 2)

            # Prepare for DB
            temp_c = (current["temp"] - 32) * 5.0 / 9.0
            final_vitals = {
                "heart_rate": current["hr"],
                "blood_pressure_systolic": current["sbp"],
                "blood_pressure_diastolic": current["dbp"],
                "spo2": current["spo2"],
                "temperature": round(temp_c, 1),
                "blood_sugar": current["sugar"]
            }
            
            from database import get_last_nurse_visit_time
            hist = _MEMORY_HISTORY[pid]
            prev_vitals = hist[-1] if hist else None
            last_visit = get_last_nurse_visit_time(pid)
            
            record = dict(final_vitals)
            record["timestamp"] = now
            hist.append(record)
            if len(hist) > 720: hist.pop(0)

            result = calculate_risk_score(
                patient=patient,
                current_vitals=final_vitals,
                prev_vitals=prev_vitals,
                last_nurse_visit_time=last_visit,
            )

            insert_vitals(patient_id=pid, vitals_dict=final_vitals)
            insert_risk_score(patient_id=pid, score_result=result)

            from alerts import get_alert_system
            sys_alerts = get_alert_system()
            sys_alerts.check_and_fire_alerts(patient, result)

# Global Instance
_simulator_instance = None

def start_simulator():
    global _simulator_instance
    if _simulator_instance is None:
        _simulator_instance = VitalsSimulator()
        _simulator_instance.start()

def get_current_vitals(patient_id: int) -> dict | None:
    hist = _MEMORY_HISTORY.get(patient_id)
    return hist[-1] if hist else None

def get_vitals_history(patient_id: int) -> list[dict]:
    return _MEMORY_HISTORY.get(patient_id, [])
