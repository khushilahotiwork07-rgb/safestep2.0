"""
database.py — SQLite persistence layer for SafeStep.
Thread-safe database handler for continuous vitals logs, alerts, and nurse visits.
"""

import sqlite3
import os
import json
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "safestep.db")

def _get_connection():
    """Returns a fresh connection to the SQLite database. Thread-safe."""
    # check_same_thread=False allows APScheduler to use the connection
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

# ── 1. Create Tables ───────────────────────────────────────────────────────────

def init_db():
    conn = _get_connection()
    try:
        # Table 1 — patients
        conn.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                patient_id INTEGER PRIMARY KEY,
                name TEXT,
                age INTEGER,
                gender TEXT,
                bed_number TEXT,
                admitted_date TEXT,
                frailty_index TEXT,
                frat_score TEXT,
                medications TEXT,
                mobility_status TEXT,
                toileting_urgency TEXT,
                confusion_score TEXT,
                fall_history TEXT,
                base_risk_category TEXT,
                has_osteoporosis INTEGER DEFAULT 0,
                has_epilepsy INTEGER DEFAULT 0
            )
        ''')
        
        # Add columns if missing (migration for existing DBs)
        try:
            conn.execute("ALTER TABLE patients ADD COLUMN has_osteoporosis INTEGER DEFAULT 0")
        except sqlite3.OperationalError: pass
        try:
            conn.execute("ALTER TABLE patients ADD COLUMN has_epilepsy INTEGER DEFAULT 0")
        except sqlite3.OperationalError: pass

        # Table 2 — vitals_log
        conn.execute('''
            CREATE TABLE IF NOT EXISTS vitals_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                heart_rate REAL,
                blood_pressure_systolic REAL,
                blood_pressure_diastolic REAL,
                spo2 REAL,
                blood_sugar REAL,
                temperature REAL
            )
        ''')
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vitals_pat_ts ON vitals_log(patient_id, timestamp DESC)")

        # Table 3 — risk_score_log
        conn.execute('''
            CREATE TABLE IF NOT EXISTS risk_score_log (
                score_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                final_score INTEGER,
                risk_level TEXT,
                baseline_score INTEGER,
                dynamic_score INTEGER,
                time_score INTEGER,
                reasons TEXT
            )
        ''')
        conn.execute("CREATE INDEX IF NOT EXISTS idx_risk_pat_ts ON risk_score_log(patient_id, timestamp DESC)")

        # Table 4 — alerts_log
        conn.execute('''
            CREATE TABLE IF NOT EXISTS alerts_log (
                alert_id TEXT PRIMARY KEY,
                patient_id INTEGER,
                patient_name TEXT,
                bed_number TEXT,
                timestamp DATETIME,
                risk_level TEXT,
                risk_score INTEGER,
                trigger_reasons TEXT,
                recommended_action TEXT,
                is_responded INTEGER DEFAULT 0,
                responded_at DATETIME,
                responded_by TEXT
            )
        ''')
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts_log(timestamp DESC)")

        # Table 5 — nurse_visits_log
        conn.execute('''
            CREATE TABLE IF NOT EXISTS nurse_visits_log (
                visit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                nurse_name TEXT,
                visit_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                action_taken TEXT,
                notes TEXT
            )
        ''')
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nurse_vis_pat_ts ON nurse_visits_log(patient_id, visit_timestamp DESC)")

        conn.commit()
    except Exception as e:
        print(f"Error initializing DB: {e}")
    finally:
        conn.close()


# ── 2. Insert Functions ────────────────────────────────────────────────────────

def insert_vitals(patient_id: int, vitals_dict: dict):
    conn = _get_connection()
    try:
        conn.execute('''
            INSERT INTO vitals_log (
                patient_id, heart_rate, blood_pressure_systolic, blood_pressure_diastolic,
                spo2, blood_sugar, temperature
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            patient_id,
            vitals_dict.get('heart_rate'),
            vitals_dict.get('blood_pressure_systolic'),
            vitals_dict.get('blood_pressure_diastolic'),
            vitals_dict.get('spo2'),
            vitals_dict.get('blood_sugar'),
            vitals_dict.get('temperature')
        ))
        conn.commit()
    except Exception as e:
        print(f"Error inserting vitals: {e}")
    finally:
        conn.close()

def insert_risk_score(patient_id: int, score_result: dict):
    conn = _get_connection()
    try:
        reasons_json = json.dumps(score_result.get('reasons', []))
        conn.execute('''
            INSERT INTO risk_score_log (
                patient_id, final_score, risk_level, baseline_score,
                dynamic_score, time_score, reasons
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            patient_id,
            score_result.get('final_score'),
            score_result.get('risk_level'),
            score_result.get('baseline_score'),
            score_result.get('dynamic_score'),
            score_result.get('time_score'),
            reasons_json
        ))
        conn.commit()
    except Exception as e:
        print(f"Error inserting risk score: {e}")
    finally:
        conn.close()

def insert_alert(alert_dict: dict):
    conn = _get_connection()
    try:
        trigger_reasons_json = json.dumps(alert_dict.get("trigger_reasons", []))
        conn.execute('''
            INSERT INTO alerts_log (
                alert_id, patient_id, patient_name, bed_number, timestamp,
                risk_level, risk_score, trigger_reasons, recommended_action,
                is_responded, responded_at, responded_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert_dict["alert_id"],
            alert_dict["patient_id"],
            alert_dict["patient_name"],
            alert_dict["bed_number"],
            alert_dict["timestamp"],
            alert_dict["risk_level"],
            alert_dict["risk_score"],
            trigger_reasons_json,
            alert_dict["recommended_action"],
            1 if alert_dict.get("is_responded") else 0,
            alert_dict.get("responded_at"),
            alert_dict.get("responded_by")
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Alert ID already exists
    except Exception as e:
        print(f"Error inserting alert: {e}")
    finally:
        conn.close()

def update_patient_conditions(patient_id: int, osteoporosis: bool, epilepsy: bool):
    conn = _get_connection()
    try:
        conn.execute('''
            UPDATE patients
            SET has_osteoporosis=?, has_epilepsy=?
            WHERE patient_id=?
        ''', (1 if osteoporosis else 0, 1 if epilepsy else 0, patient_id))
        conn.commit()
    except Exception as e:
        print(f"Error updating patient conditions: {e}")
    finally:
        conn.close()

def update_alert_response(alert_id: str, nurse_name: str, response_time: str):
    conn = _get_connection()
    try:
        conn.execute('''
            UPDATE alerts_log 
            SET is_responded=1, responded_by=?, responded_at=? 
            WHERE alert_id=?
        ''', (nurse_name, response_time, alert_id))
        conn.commit()
    except Exception as e:
        print(f"Error responding to alert: {e}")
    finally:
        conn.close()

def insert_nurse_visit(patient_id: int, nurse_name: str, action_taken: str, notes: str = ""):
    conn = _get_connection()
    try:
        conn.execute('''
            INSERT INTO nurse_visits_log (
                patient_id, nurse_name, action_taken, notes
            ) VALUES (?, ?, ?, ?)
        ''', (patient_id, nurse_name, action_taken, notes))
        conn.commit()
    except Exception as e:
        print(f"Error inserting nurse visit: {e}")
    finally:
        conn.close()


# ── 3. Query Functions ─────────────────────────────────────────────────────────

def get_vitals_last_hour(patient_id: int) -> list[dict]:
    conn = _get_connection()
    try:
        # For demo visibility, we want to show rapid changes. Let's select the latest 60 readings (5 mins).
        rows = conn.execute('''
            SELECT * FROM (
                SELECT * FROM vitals_log 
                WHERE patient_id=? 
                ORDER BY timestamp DESC
                LIMIT 60
            ) 
            ORDER BY timestamp ASC
        ''', (patient_id,)).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error getting vitals: {e}")
        return []
    finally:
        conn.close()

def get_risk_score_history(patient_id: int) -> list[dict]:
    conn = _get_connection()
    try:
        rows = conn.execute('''
            SELECT * FROM risk_score_log 
            WHERE patient_id=? 
            ORDER BY timestamp ASC
        ''', (patient_id,)).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error getting risk score history: {e}")
        return []
    finally:
        conn.close()

def get_todays_alerts() -> list[dict]:
    conn = _get_connection()
    try:
        today_str = date.today().isoformat()
        rows = conn.execute('''
            SELECT * FROM alerts_log 
            WHERE timestamp >= date('now')
            ORDER BY timestamp DESC
        ''').fetchall()
        
        results = []
        for r in rows:
            d = dict(r)
            d["is_responded"] = bool(d["is_responded"])
            try:
                d["trigger_reasons"] = json.loads(d["trigger_reasons"])
            except:
                d["trigger_reasons"] = []
            results.append(d)
        return results
    except Exception as e:
        print(f"Error getting today's alerts: {e}")
        return []
    finally:
        conn.close()

def get_last_nurse_visit(patient_id: int):
    conn = _get_connection()
    try:
        row = conn.execute('''
            SELECT visit_timestamp FROM nurse_visits_log 
            WHERE patient_id=? 
            ORDER BY visit_timestamp DESC LIMIT 1
        ''', (patient_id,)).fetchone()
        
        if row:
            return datetime.fromisoformat(row["visit_timestamp"])
        return None
    except Exception as e:
        print(f"Error getting last nurse visit: {e}")
        return None
    finally:
        conn.close()


# Mapping functions so the rest of the application using older database names doesn't immediately crash.
def get_latest_vitals(patient_id):
    conn = _get_connection()
    try:
         row = conn.execute("SELECT * FROM vitals_log WHERE patient_id=? ORDER BY timestamp DESC LIMIT 1", (patient_id,)).fetchone()
         if not row: return None
         d = dict(row)
         d["systolic_bp"] = d["blood_pressure_systolic"]
         d["diastolic_bp"] = d["blood_pressure_diastolic"]
         return d
    except Exception:
         return None
    finally:
         conn.close()

def get_handover_notes(patient_id, limit=10):
    conn = _get_connection()
    try:
        rows = conn.execute('''
            SELECT visit_timestamp as created_at, nurse_name, notes as note 
            FROM nurse_visits_log 
            WHERE patient_id=? 
            ORDER BY visit_timestamp DESC LIMIT ?
        ''', (patient_id, limit)).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()

def get_all_patients_db():
    conn = _get_connection()
    try:
        rows = conn.execute("SELECT * FROM patients ORDER BY patient_id ASC").fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error fetching patients from db: {e}")
        return []
    finally:
        conn.close()

def insert_patient(p: dict):
    conn = _get_connection()
    try:
        conn.execute('''
            INSERT INTO patients (
                name, age, gender, bed_number, admitted_date,
                frailty_index, frat_score, medications, mobility_status,
                toileting_urgency, confusion_score, fall_history, base_risk_category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            p.get('name'), p.get('age'), p.get('gender'), p.get('ward', 'Ward') + " " + str(p.get('bed')),
            p.get('admitted_on'), p.get('frailty_index'), p.get('epa_frat'),
            p.get('medications'), p.get('mobility'), p.get('toileting'),
            p.get('confusion'), p.get('fall_history'), p.get('base_risk_category'),
            1 if p.get('has_osteoporosis') else 0, 1 if p.get('has_epilepsy') else 0
        ))
        conn.commit()
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    except Exception as e:
        print(f"Error inserting patient: {e}")
        return None
    finally:
        conn.close()

get_last_nurse_visit_time = get_last_nurse_visit
