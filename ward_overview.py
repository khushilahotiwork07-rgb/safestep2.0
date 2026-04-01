"""
page_modules/ward_overview.py — Ward Overview dashboard for SafeStep.
At-a-glance fall-risk status for all patients, auto-refreshing every 5 seconds.
"""

import streamlit as st
import streamlit.components.v1 as components
import textwrap
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from patients import get_patients_with_status
from alerts import get_alert_system
from utils.helpers import (
    inject_global_css, page_header,
    PRIMARY, TEXT_DARK, TEXT_GREY, BORDER, BG_WHITE,
)


def render():
    inject_global_css()
    page_header("Ward Overview", "Real-time fall-risk status across all wards")

    patients = get_patients_with_status()
    sys_alerts = get_alert_system()
    active_alerts = sys_alerts.get_active_alerts()

    # ── 1. 4 Large Metric Cards ────────────────────────────────────────────────
    total    = len(patients)
    watch    = sum(1 for p in patients if p["risk_level"] == "Watch")
    high     = sum(1 for p in patients if p["risk_level"] == "High Risk")
    critical = sum(1 for p in patients if p["risk_level"] == "Critical")

    st.markdown(textwrap.dedent("""
    <style>
    @keyframes pulse-border {
        0% { border-color: #D64045; box-shadow: 0 0 0 0 rgba(214, 64, 69, 0.4); }
        70% { border-color: #FF7B7B; box-shadow: 0 0 0 10px rgba(214, 64, 69, 0); }
        100% { border-color: #D64045; box-shadow: 0 0 0 0 rgba(214, 64, 69, 0); }
    }
    .kpi-card {
        border-radius: 12px; padding: 1.2rem; text-align: center;
    }
    .kpi-critical {
        background: #FFF0F0; border: 2px solid #D64045;
        animation: pulse-border 2s infinite;
    }
    </style>
    """), unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="kpi-card" style="background:#EFF6FF; border:1px solid {PRIMARY}40;" title="Total number of patients currently admitted and tracked by the system.">'
                    f'<div style="font-size:2.5rem;font-weight:800;color:{PRIMARY};line-height:1.1;">{total}</div>'
                    f'<div style="font-size:0.85rem;color:{TEXT_GREY};font-weight:600;">Total Patients</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="kpi-card" style="background:#FFFBEA; border:1px solid #C4A00040;" title="Patients with a risk score between 41 and 65. Requires routine monitoring.">'
                    f'<div style="font-size:2.5rem;font-weight:800;color:#C4A000;line-height:1.1;">{watch}</div>'
                    f'<div style="font-size:0.85rem;color:{TEXT_GREY};font-weight:600;">Watch</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="kpi-card" style="background:#FFF5EE; border:1px solid #E87B3540;" title="Patients with a risk score between 66 and 85. Action required soon.">'
                    f'<div style="font-size:2.5rem;font-weight:800;color:#E87B35;line-height:1.1;">{high}</div>'
                    f'<div style="font-size:0.85rem;color:{TEXT_GREY};font-weight:600;">High Risk</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="kpi-card kpi-critical" title="Patients with a risk score above 85! Immediate clinical intervention required.">'
                    f'<div style="font-size:2.5rem;font-weight:800;color:#D64045;line-height:1.1;">{critical}</div>'
                    f'<div style="font-size:0.85rem;color:#D64045;font-weight:600;">Critical</div></div>', unsafe_allow_html=True)

    st.markdown("<hr style='margin:1.5rem 0;'>", unsafe_allow_html=True)

    st.markdown("<hr style='margin:1.5rem 0;'>", unsafe_allow_html=True)

    # ── 3. Live Digital Monitor Dashboard ──────────────────────────────────────
    st.markdown("### 📽️ Real-Time Clinical Monitors")
    
    @st.fragment(run_every=5)
    def render_monitors():
        # Re-fetch patients inside fragment for latest vitals
        patients = get_patients_with_status()
        
        # Sort logic: Critical -> High Risk -> Watch -> Safe -> Pending
        _ORDER = {"Critical": 1, "High Risk": 2, "Watch": 3, "Safe": 4, "Pending": 5}
        patients.sort(key=lambda p: (_ORDER.get(p["risk_level"], 5), -(p["risk_score"] or 0)))

        # Display in a grid of cards
        cols_per_row = 2
        rows = [patients[i:i + cols_per_row] for i in range(0, len(patients), cols_per_row)]

        for row in rows:
            st_cols = st.columns(cols_per_row)
            for i, p in enumerate(row):
                with st_cols[i]:
                    level = p["risk_level"]
                    score = p.get("risk_score", 0)
                    
                    if level == "Critical":
                        border_color = "#D64045"; bg_grad = "linear-gradient(135deg, #FFF0F0 0%, #FFE5E5 100%)"
                    elif level == "High Risk":
                        border_color = "#E87B35"; bg_grad = "linear-gradient(135deg, #FFF5EE 0%, #FFECD9 100%)"
                    elif level == "Watch":
                        border_color = "#C4A000"; bg_grad = "linear-gradient(135deg, #FFFDE7 0%, #FFF9C4 100%)"
                    else:
                        border_color = "#3DAA6F"; bg_grad = "linear-gradient(135deg, #F0FBF5 0%, #E8F6ED 100%)"

                    v = p.get("vitals", {}) or {}
                    hr = v.get("heart_rate", "—")
                    sbp = v.get("blood_pressure_systolic", "—")
                    dbp = v.get("blood_pressure_diastolic", "—")
                    spo2 = v.get("spo2", "—")

                    # Formatting for display
                    hr_str = f"{hr:.0f}" if isinstance(hr, (int, float)) else str(hr)
                    bp_str = f"{sbp:.0f}/{dbp:.0f}" if isinstance(sbp, (int, float)) else "—/—"
                    spo2_str = f"{spo2:.0f}" if isinstance(spo2, (int, float)) else str(spo2)
                    score_str = f"{score:.0f}"
                    
                    html_card = f"""
<div style="background:{bg_grad}; border:2px solid {border_color}; border-radius:16px; padding:1.5rem; margin-bottom:1rem; box-shadow: 0 4px 12px rgba(0,0,0,0.05); position:relative; overflow:hidden;">
    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:1rem;">
        <div>
            <div style="font-size:1.2rem; font-weight:800; color:{TEXT_DARK};">{p['name']}</div>
            <div style="font-size:0.8rem; font-weight:600; color:{TEXT_GREY}; text-transform:uppercase;">BED {p['bed']} | {p['age']}Y/O</div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:1.5rem; font-weight:900; color:{border_color};">{score_str}</div>
            <div style="font-size:0.6rem; font-weight:700; color:{border_color}; text-transform:uppercase; letter-spacing:1px;">RISK SCORE</div>
        </div>
    </div>
    
    <div style="display:grid; grid-template-columns: 1fr 1.2fr 1fr; gap:10px; background:rgba(0,0,0,0.03); padding:1rem; border-radius:12px;">
        <div style="text-align:center;">
            <div style="font-size:0.75rem; font-weight:700; color:{TEXT_GREY}; margin-bottom:2px;">HR</div>
            <div style="font-size:2rem; font-weight:900; color:{PRIMARY}; font-family:'Courier New', monospace;">{hr_str}</div>
            <div style="font-size:0.6rem; font-weight:600; color:{TEXT_GREY};">BPM</div>
        </div>
        <div style="text-align:center; border-left:1px solid rgba(0,0,0,0.1); border-right:1px solid rgba(0,0,0,0.1);">
            <div style="font-size:0.75rem; font-weight:700; color:{TEXT_GREY}; margin-bottom:2px;">NIBP</div>
            <div style="font-size:2rem; font-weight:900; color:{TEXT_DARK}; font-family:'Courier New', monospace;">{bp_str}</div>
            <div style="font-size:0.6rem; font-weight:600; color:{TEXT_GREY};">mmHg</div>
        </div>
        <div style="text-align:center;">
            <div style="font-size:0.75rem; font-weight:700; color:{TEXT_GREY}; margin-bottom:2px;">SPO2</div>
            <div style="font-size:2rem; font-weight:900; color:#3DAA6F; font-family:'Courier New', monospace;">{spo2_str}%</div>
            <div style="font-size:0.6rem; font-weight:600; color:{TEXT_GREY};">Oxygen</div>
        </div>
    </div>
</div>
"""
                    st.markdown("".join(l.strip() for l in html_card.splitlines()), unsafe_allow_html=True)
                    
                    if st.button(f"Clinical Chart: {p['name']}", key=f"det_{p['id']}", use_container_width=True):
                        st.session_state["selected_patient_id"] = p["id"]
                        st.session_state["current_page"] = "Patient Detail"
                        st.rerun()

        # ── 4. Auto-refresh & Footer ───────────────────────────────────────────────
        now_str = datetime.now().strftime("%I:%M:%S %p")
        st.markdown(f"<div style='text-align:center; font-size:0.8rem; color:{TEXT_GREY}; margin-top:2rem;'>Last monitored sync: {now_str} — Flicker-free updates active</div>", unsafe_allow_html=True)

    # Initial call to render the fragment
    render_monitors()
