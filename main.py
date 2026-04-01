"""
main.py — Entry point and routing for the SafeStep Patient Fall Risk System.
"""

import streamlit as st
import sys
import os

# Ensure the app root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ── System initialisation ──────────────────────────────────────────────────────
@st.cache_resource
def _init_system():
    # 1. Initialize SQLite Database
    from database import init_db
    init_db()

    # Seed initial 5 patients if the table is empty
    from patients import seed_patients_if_empty
    seed_patients_if_empty()

    # 2. Start APScheduler Background Vitals Simulator
    # Runs automatically every 5 seconds without blocking the UI
    from vitals_simulator import start_simulator
    start_simulator()
    return True

_init_system()

# ── Page imports ───────────────────────────────────────────────────────────────
from page_modules import (     # noqa: E402
    ward_overview,
    patient_detail,
    active_alerts,
    alert_history,
    handover_summary,
    login,
)
from utils.helpers import PRIMARY, TEXT_DARK, TEXT_GREY, BORDER, BG_LIGHT, inject_global_css
from alerts import get_unacknowledged_count

# ── Streamlit UI Config ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SafeStep — Patient Fall Risk System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


def render_sidebar():
    """Renders the persistent left navigation sidebar."""
    with st.sidebar:
        # ── Branding ──
        hospital = st.session_state.get("hospital_name", "SafeStep Facility")
        st.markdown(f"""
<div style="padding:1rem 0.5rem 1rem 0.5rem;">
<div style="font-size:1.6rem;font-weight:800;color:{PRIMARY};letter-spacing:-0.5px;display:flex;align-items:center;gap:8px;">
<span style="font-size:1.8rem;">🏥</span> SafeStep
</div>
<div style="font-size:0.6rem;font-weight:700;color:{TEXT_GREY};letter-spacing:1px;margin-top:2px;text-transform:uppercase;">
{hospital} — Fall Risk Analytics
</div>
</div>
""".replace('\n', ''), unsafe_allow_html=True)
        
        st.markdown(f"<hr style='margin:0 0 1.5rem 0;border-top:1px solid {BORDER};'>",
                    unsafe_allow_html=True)

        # ── Setup state ──
        if "current_page" not in st.session_state:
            st.session_state["current_page"] = "Ward Overview"

        nav_buttons = [
            ("🏠 Ward Overview", "Ward Overview"),
            ("👤 Patient Detail", "Patient Detail"),
        ]

        count = get_unacknowledged_count()
        badge_text = f"  [{count}]" if count > 0 else ""
        nav_buttons.append((f"🚨 Active Alerts{badge_text}", "Active Alerts"))
        nav_buttons.append(("📋 Alert History", "Alert History"))
        nav_buttons.append(("📝 Shift Handover", "Shift Handover"))
        nav_buttons.append(("➕ Admit Patient", "Admit Patient"))

        for label, page_name in nav_buttons:
            is_active = st.session_state["current_page"] == page_name
            if st.button(
                label,
                key=f"nav_{page_name}",
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.session_state["current_page"] = page_name
                st.rerun()

        st.markdown("<div style='flex-grow:1;min-height:20vh;'></div>", unsafe_allow_html=True)
        
        # ── Logout mechanism ──
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            st.session_state["logged_in"] = False
            st.rerun()

        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
        from datetime import datetime
        sync_time = datetime.now().strftime("%I:%M:%S %p")
        st.markdown(f"""
<div style="background:{BG_LIGHT}; border:1px solid {BORDER}; border-radius:8px; padding:0.8rem; text-align:center;">
<div style="font-size:0.75rem; font-weight:700; color:#3DAA6F; margin-bottom:4px; display:flex; align-items:center; justify-content:center; gap:6px;">
<span style="font-size:0.9rem;">🟢</span> Live Monitoring Active
</div>
<div style="font-size:0.65rem; color:{TEXT_GREY};">
Last sync: {sync_time}
</div>
</div>
""".replace('\n', ''), unsafe_allow_html=True)


def main():
    inject_global_css()
    # Add CSS transition rules here
    st.markdown("""
    <style>
    .kpi-card, div[style*="background"] {
        transition: background-color 0.4s ease, border-color 0.4s ease, color 0.4s ease;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Check for login state
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        login.render()
        return

    # If logged in, show the regular dashboard
    render_sidebar()

    page = st.session_state.get("current_page", "Ward Overview")

    with st.spinner("Updating patient data..."):
        if page == "Ward Overview":
            ward_overview.render()
        elif page == "Patient Detail":
            patient_detail.render()
        elif page == "Active Alerts":
            active_alerts.render()
        elif page == "Alert History":
            alert_history.render()
        elif page == "Shift Handover":
            handover_summary.render()
        elif page == "Admit Patient":
            import page_modules.add_patient as add_patient
            add_patient.render()


if __name__ == "__main__":
    main()
