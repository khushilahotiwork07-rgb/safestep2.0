"""
page_modules/active_alerts.py — Live pending alerts for SafeStep.
Unresponded alerts requiring nurse input.
"""

import streamlit as st
import streamlit.components.v1 as components
import sys, os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alerts import get_alert_system
from utils.helpers import inject_global_css, PRIMARY, TEXT_DARK, TEXT_GREY, BG_WHITE, BG_LIGHT, RISK_COLORS, RISK_BG

def render():
    inject_global_css()
    st.markdown("## 🚨 Active Alerts")
    st.markdown(f"<div style='color:{TEXT_GREY};font-size:0.9rem;margin-bottom:1.5rem;'>Unresponded fall-risk alerts sorted by urgency.</div>", unsafe_allow_html=True)

    sys_alerts = get_alert_system()
    alerts = sys_alerts.get_active_alerts()

    if not alerts:
        st.success("All patients are currently stable. No active alerts.")
        return

    for a in alerts:
        level = a["risk_level"]
        color = RISK_COLORS.get(level, "#9CA3AF")
        bg = RISK_BG.get(level, "#F5F5F5")
        
        with st.container(border=True):
            html_top = f"""
<div style="background:{bg}; color:{color}; font-weight:800; text-transform:uppercase; 
            padding:6px 12px; border-radius:6px 6px 0 0; margin:-1rem -1rem 1rem -1rem;
            border-bottom:2px solid {color}40; letter-spacing:1px;">
    {level} ALERT
</div>
"""
            st.markdown(html_top, unsafe_allow_html=True)

            col_main, col_btn = st.columns([3, 1])

            with col_main:
                st.markdown(f"<div style='font-size:1.6rem;font-weight:800;color:{TEXT_DARK};margin-bottom:4px;'>{a['patient_name']} — Bed {a['bed_number']}</div>", unsafe_allow_html=True)
                
                ts = a["timestamp"]
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    ts_str = dt.strftime("%I:%M:%S %p")
                except:
                    ts_str = ts
                    
                st.markdown(f"<div style='color:{TEXT_GREY};font-size:0.9rem;margin-bottom:8px;'><strong>Risk Score:</strong> {a['risk_score']} &nbsp;·&nbsp; <strong>Time:</strong> {ts_str}</div>", unsafe_allow_html=True)

                st.markdown(f"<div style='font-size:0.85rem;font-weight:700;margin-top:0.5rem;color:{TEXT_DARK};'>Top 3 Risk Factors:</div>", unsafe_allow_html=True)
                for reason in a.get("trigger_reasons", []):
                    st.markdown(f"<div style='font-size:0.85rem;color:{TEXT_DARK};margin-left:8px;'>• {reason}</div>", unsafe_allow_html=True)
                
                rec_text = a.get("recommended_action", "")
                if level in ("Critical", "High Risk"):
                    st.markdown(f"<div style='margin-top:1rem;color:#D64045;font-weight:700;'>ACTION REQUIRED: {rec_text}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='margin-top:1rem;font-weight:600;'>Recommended Action: {rec_text}</div>", unsafe_allow_html=True)
            
            with col_btn:
                st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
                if st.button("👁 View Patient", key=f"vp_{a['alert_id']}", use_container_width=True):
                    st.session_state["selected_patient_id"] = a["patient_id"]
                    st.session_state["current_page"] = "Patient Detail"
                    st.rerun()
                
                with st.popover("✓ Mark Responded", use_container_width=True):
                    with st.form(f"resp_form_{a['alert_id']}"):
                        nurse = st.text_input("Nurse Name", placeholder="Your name...")
                        if st.form_submit_button("Confirm Response", use_container_width=True):
                            if nurse:
                                sys_alerts.mark_alert_responded(a["alert_id"], nurse)
                                st.rerun()
                            else:
                                st.error("Please enter your name.")


