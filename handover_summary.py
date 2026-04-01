"""
page_modules/handover_summary.py — Shift Handover dashboard for SafeStep.
Auto-generates a complete shift handover report for incoming nurses.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import json
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_handover_notes, get_todays_alerts
from patients import get_patients_with_status
from utils.helpers import (
    inject_global_css, page_header,
    TEXT_DARK, TEXT_GREY, BORDER, BG_WHITE, BG_LIGHT, PRIMARY, RISK_COLORS,
)

def render():
    inject_global_css()
    
    now_str = datetime.now().strftime("%I:%M %p — %B %d, %Y")
    
    col1, col2 = st.columns([3, 1], vertical_alignment="center")
    with col1:
        st.markdown("## 📋 Shift Handover Report")
        st.markdown(f"<div style='color:{TEXT_GREY};font-size:0.9rem;margin-bottom:0.5rem;'>Generated on {now_str}</div>", unsafe_allow_html=True)
    with col2:
        st.download_button(
            label="⬇️ Download Handover Log",
            data=f"SAFE STEP SHIFT HANDOVER REPORT\nGenerated: {now_str}\n\n(See dashboard for full details)",
            file_name=f"Handover_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True
        )

    st.markdown("<hr style='margin:0.5rem 0 1.5rem 0;'>", unsafe_allow_html=True)

    patients = get_patients_with_status()
    if not patients:
        st.info("No patients currently admitted.")
        return

    _ORDER = {"Critical": 1, "High Risk": 2, "Watch": 3, "Safe": 4, "Pending": 5}
    patients.sort(key=lambda x: (_ORDER.get(x["risk_level"], 5), -(x.get("risk_score") or 0)))

    # ── 1. Patients Requiring Immediate Attention ──────────────────────────────
    st.markdown("### 🚨 Patients Requiring Immediate Attention")
    st.markdown(f"<div style='color:{TEXT_GREY};font-size:0.85rem;margin-bottom:1rem;'>Critical and High Risk patients</div>", unsafe_allow_html=True)

    immediate = [p for p in patients if p["risk_level"] in ("Critical", "High Risk")]
    if immediate:
        for p in immediate:
            level = p["risk_level"]
            color = RISK_COLORS.get(level, "#D64045")
            notes = get_handover_notes(p["id"], limit=2)
            recent_note = notes[0]["note"] if notes else "No recent manual nurse notes recorded."
            reasons = p.get("reasons", [])
            top_reason = reasons[0] if reasons else "Elevated risk parameters."

            html_immed = f"""
<div style="border-left:4px solid {color};background:{BG_LIGHT};padding:1rem;border-radius:6px;margin-bottom:0.8rem;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
        <div style="font-size:1.1rem;font-weight:700;color:{TEXT_DARK};">
            {p['name']} (Bed {p['bed']})
        </div>
        <div style="font-weight:800;color:{color};">
            {level} — Score: {p.get('risk_score', 0):.0f}
        </div>
    </div>
    <div style="font-size:0.9rem;color:{TEXT_DARK};margin-bottom:4px;">
        <strong>Primary Flag:</strong> {top_reason}
    </div>
    <div style="font-size:0.85rem;color:{TEXT_GREY};font-style:italic;">
        <strong>Handover Note:</strong> "{recent_note}"
    </div>
</div>
"""
            st.markdown(html_immed, unsafe_allow_html=True)
    else:
        st.success("No patients are currently in Critical or High Risk states.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 2. Patients To Monitor ─────────────────────────────────────────────────
    st.markdown("### ⚠️ Patients To Monitor")
    st.markdown(f"<div style='color:{TEXT_GREY};font-size:0.85rem;margin-bottom:1rem;'>Watch level patients</div>", unsafe_allow_html=True)

    watch = [p for p in patients if p["risk_level"] == "Watch"]
    if watch:
        for p in watch:
            color = RISK_COLORS.get("Watch", "#C4A000")
            notes = get_handover_notes(p["id"], limit=1)
            recent_note = notes[0]["note"] if notes else "Monitor as per standard protocol."
            
            html_watch = f"""
<div style="border-left:4px solid {color};background:{BG_WHITE};border-top:1px solid {BORDER};border-right:1px solid {BORDER};border-bottom:1px solid {BORDER};padding:0.8rem 1rem;border-radius:6px;margin-bottom:0.5rem;">
    <div style="font-size:1rem;font-weight:700;color:{TEXT_DARK};margin-bottom:2px;">
        {p['name']} (Bed {p['bed']}) — Score {p.get('risk_score', 0):.0f}
    </div>
    <div style="font-size:0.85rem;color:{TEXT_GREY};">
        {recent_note}
    </div>
</div>
"""
            st.markdown(html_watch, unsafe_allow_html=True)
    else:
        st.info("No patients currently in Watch state.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 3. Stable Patients ─────────────────────────────────────────────────────
    st.markdown("### ✅ Stable Patients")
    stable = [p for p in patients if p["risk_level"] in ("Safe", "Pending")]
    if stable:
        st.markdown(f"<div style='background:{BG_WHITE};border:1px solid {BORDER};border-radius:8px;padding:1rem;'>", unsafe_allow_html=True)
        for p in stable:
            notes = get_handover_notes(p["id"], limit=1)
            extra = f"— <em>{notes[0]['note'][:40]}...</em>" if notes else "— Routine obs normal"
            st.markdown(f"<div style='font-size:0.9rem;color:{TEXT_DARK};margin-bottom:6px;'>🟢 <strong>{p['name']}</strong> (Bed {p['bed']}) {extra}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No stable patients at this time.")

    st.markdown("<hr style='margin:2rem 0;'>", unsafe_allow_html=True)

    # ── 4. Shift Summary Statistics ────────────────────────────────────────────
    st.markdown("### 📊 Shift Summary Statistics")
    
    alerts = get_todays_alerts()
    all_notes = []
    for p in patients:
        pts = get_handover_notes(p["id"], limit=50)
        all_notes.extend(pts)
        
    total_alerts = len(alerts)
    
    resp_times = []
    triggers = {}
    for a in alerts:
        trigs = a.get("trigger_reasons", [])
        if trigs:
            t = trigs[0]
            triggers[t] = triggers.get(t, 0) + 1
            
        if a.get("is_responded") and a.get("responded_at") and a.get("timestamp"):
            try:
                t1 = datetime.fromisoformat(a["timestamp"].replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(a["responded_at"].replace("Z", "+00:00"))
                mins = (t2 - t1).total_seconds() / 60.0
                if mins >= 0: resp_times.append(mins)
            except: pass
            
    avg_resp = f"{sum(resp_times)/len(resp_times):.1f} min" if resp_times else "N/A"
    most_common = max(triggers, key=triggers.get) if triggers else "None"
    
    highest_risk_pat = patients[0] 
    
    col_s1, col_s2, col_s3 = st.columns(3)
    col_s1.metric("Total Alerts This Shift", total_alerts)
    col_s2.metric("Average Response Time", avg_resp)
    col_s3.metric("Nurse Visits Logged", len(all_notes))
    
    col_s4, col_s5 = st.columns(2)
    col_s4.metric("Highest Risk Patient", f"{highest_risk_pat['name']} ({highest_risk_pat['risk_level']})")
    col_s5.metric("Most Common Trigger", most_common[:45] + ("..." if len(most_common) > 45 else ""))

    st.markdown("<hr style='margin:1.5rem 0;'>", unsafe_allow_html=True)

    # ── 5. Recommended Actions ─────────────────────────────────────────────────
    st.markdown("### 💡 Recommended Actions For Incoming Shift")
    st.markdown(f"<div style='color:{TEXT_GREY};font-size:0.85rem;margin-bottom:1rem;'>Auto-generated based on current trends and clinical profiles</div>", unsafe_allow_html=True)

    recs = []
    for p in immediate:
        action = "Check patient immediately upon shift start."
        if p.get("recs"): action = p["recs"][0]
        recs.append(f"**{p['name']}**: {action}")
        
    for p in watch:
        recs.append(f"**{p['name']}**: Monitor usual patterns. Schedule a check-in visit early in shift.")
        
    if not recs:
         st.success("All stable. Continue routine hourly rounding.")
    else:
         for r in recs[:5]:
             st.info(r, icon="📌")


