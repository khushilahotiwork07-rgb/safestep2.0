"""
page_modules/alert_history.py — Complete alert history log for SafeStep.
Searchable, filterable table of all generated alerts.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_todays_alerts
from utils.helpers import inject_global_css, PRIMARY, TEXT_DARK, TEXT_GREY, BG_WHITE, BG_LIGHT, RISK_COLORS

def render():
    inject_global_css()
    st.markdown("## 📋 Alert History")
    st.markdown(f"<div style='color:{TEXT_GREY};font-size:0.9rem;margin-bottom:1.5rem;'>Complete log of all alerts generated today.</div>", unsafe_allow_html=True)

    alerts = get_todays_alerts()

    if not alerts:
        st.info("No alerts recorded today.")
        return

    # ── Calculate Metrics ──────────────────────────────────────────────────────
    total_alerts = len(alerts)
    response_times = []

    for a in alerts:
        if a.get("is_responded") and a.get("responded_at") and a.get("timestamp"):
            try:
                ts_trigger = datetime.fromisoformat(a["timestamp"].replace("Z", "+00:00"))
                ts_respond = datetime.fromisoformat(a["responded_at"].replace("Z", "+00:00"))
                mins = (ts_respond - ts_trigger).total_seconds() / 60.0
                if mins >= 0:
                    response_times.append(mins)
            except Exception:
                pass

    if response_times:
        avg_resp = sum(response_times) / len(response_times)
        fast_resp = min(response_times)
        avg_str = f"{avg_resp:.1f} min"
        fast_str = f"{fast_resp:.1f} min"
    else:
        avg_str = "—"
        fast_str = "—"

    # ── KPI Row ────────────────────────────────────────────────────────────────
    k1, k2, k3 = st.columns(3)
    
    def _kpi(title, val, border_col):
        html = f"""
<div style="background:{BG_LIGHT};border:1px solid {border_col}60;border-radius:12px;padding:1.2rem;text-align:center;">
    <div style="font-size:2.5rem;font-weight:800;color:{TEXT_DARK};line-height:1.1;">{val}</div>
    <div style="font-size:0.85rem;color:{TEXT_GREY};font-weight:600;margin-top:4px;">{title}</div>
</div>
"""
        return html
        
    k1.markdown(_kpi("Total Alerts Today", total_alerts, PRIMARY), unsafe_allow_html=True)
    k2.markdown(_kpi("Average Response Time", avg_str, "#C4A000"), unsafe_allow_html=True)
    k3.markdown(_kpi("Fastest Response Time", fast_str, "#3DAA6F"), unsafe_allow_html=True)

    st.markdown("<hr style='margin:1.5rem 0;'>", unsafe_allow_html=True)

    # ── Table ──────────────────────────────────────────────────────────────────
    f_risk = st.selectbox("Filter by Risk Level", ["All", "Critical", "High Risk", "Watch", "Safe"], index=0)

    rows = []
    _ORDER = {"Critical": 1, "High Risk": 2, "Watch": 3, "Safe": 4, "Pending": 5}
    alerts.sort(key=lambda x: (_ORDER.get(x["risk_level"], 5), x["timestamp"]), reverse=True)

    for a in alerts:
        if f_risk != "All" and a["risk_level"] != f_risk:
             continue

        ts_str = a["timestamp"]
        try:
            dt = datetime.fromisoformat(a["timestamp"].replace("Z", "+00:00"))
            ts_str = dt.strftime("%I:%M:%S %p")
        except: pass
        
        resp_min_str = "—"
        if a.get("is_responded") and a.get("responded_at") and a.get("timestamp"):
            try:
                t1 = datetime.fromisoformat(a["timestamp"].replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(a["responded_at"].replace("Z", "+00:00"))
                mins = (t2 - t1).total_seconds() / 60.0
                if mins >= 0:
                    resp_min_str = f"{mins:.1f}"
            except: pass

        reasons = a.get("trigger_reasons", [])
        top_reason = reasons[0] if reasons else "Multiple factors"
        if len(top_reason) > 50: top_reason = top_reason[:47] + "..."

        nurse = a.get("responded_by", "—")
        if not nurse: nurse = "—"
        
        action_taken = "Acknowledged" if a.get("is_responded") else "Pending"

        rows.append({
            "Time":           ts_str,
            "Patient Name":   a["patient_name"],
            "Bed":            a["bed_number"],
            "Risk Level":     a["risk_level"],
            "Risk Score":     a["risk_score"],
            "Top Trigger Reason": top_reason,
            "Response Time (mins)": resp_min_str,
            "Nurse Who Responded": nurse,
            "Action Taken":   action_taken
        })
        
    df = pd.DataFrame(rows)
    
    if df.empty:
        st.info("No alerts match the selected filter.")
    else:
        def color_risk(val):
            color = RISK_COLORS.get(val, '')
            return f'color: {color}; font-weight: bold' if color else ''
            
        try:
             s_df = df.style.map(color_risk, subset=["Risk Level"])
        except AttributeError:
             s_df = df.style.applymap(color_risk, subset=["Risk Level"])
             
        st.dataframe(s_df, hide_index=True, use_container_width=True)
