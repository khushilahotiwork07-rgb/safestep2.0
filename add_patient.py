"""
page_modules/add_patient.py — Patient Admission Page.
Allows nurses to dynamically add new patients to the SafeStep system.
"""

import streamlit as st
from database import insert_patient
from utils.helpers import inject_global_css, PRIMARY, TEXT_DARK, TEXT_GREY, BORDER, BG_LIGHT, BG_WHITE

def render():
    inject_global_css()
    st.markdown("## ➕ Admit New Patient")
    st.markdown(f"<div style='color:{TEXT_GREY}; margin-bottom: 2rem;'>Enter patient details to begin real-time monitoring and fall-risk assessment.</div>", unsafe_allow_html=True)

    with st.container():
        st.markdown(f"<div style='background:{BG_WHITE}; border:1px solid {BORDER}; border-radius:12px; padding:2rem;'>", unsafe_allow_html=True)
        
        with st.form("admission_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name", placeholder="e.g. John Doe")
                age = st.number_input("Age", min_value=0, max_value=120, value=70)
                gender = st.selectbox("Gender", ["Male", "Female", "Other"])
                ward = st.text_input("Ward", value="Ward A")
                bed = st.text_input("Bed Number", placeholder="e.g. Bed 12")
                admitted_on = st.date_input("Admission Date").strftime("%Y-%m-%d")

            with col2:
                frailty = st.selectbox("Frailty Index", [
                    "1/9 — Very Fit", "2/9 — Well", "3/9 — Managing Well", 
                    "4/9 — Vulnerable", "5/9 — Mildly Frail", "6/9 — Moderately Frail", 
                    "7/9 — Severely Frail", "8/9 — Very Severely Frail", "9/9 — Terminally Ill"
                ])
                frat = st.selectbox("EPA FRAT Score", ["Low Risk", "Medium Risk", "High Risk"])
                mobility = st.selectbox("Mobility Status", ["Independent", "Uses walker", "Needs assistance", "Bedbound"])
                toileting = st.text_area("Toileting Urgency / Notes", placeholder="e.g. High urgency, needs assistance at night.")
                confusion = st.selectbox("Confusion Score", ["Fully alert", "Mild confusion", "Moderate disorientation", "Severe disorientation"])
                medications = st.text_area("Current Medications", placeholder="e.g. Sedatives, BP medication, diuretics.")
                fall_history = st.text_input("Fall History", placeholder="e.g. Fell twice in past year.")

            st.markdown("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button("Admit Patient", use_container_width=True)

            if submit:
                if not name or not bed:
                    st.error("Name and Bed Number are required.")
                else:
                    new_patient = {
                        "name": name,
                        "age": age,
                        "gender": gender,
                        "ward": ward,
                        "bed": bed,
                        "admitted_on": admitted_on,
                        "frailty_index": frailty,
                        "epa_frat": frat,
                        "medications": medications,
                        "mobility": mobility,
                        "toileting": toileting,
                        "confusion": confusion,
                        "fall_history": fall_history,
                        "base_risk_category": frat # Defaulting to FRAT
                    }
                    
                    patient_id = insert_patient(new_patient)
                    if patient_id:
                        st.success(f"Patient {name} admitted successfully! ID: {patient_id}")
                        # Automatically switch to Ward Overview to see the new patient
                        st.session_state["current_page"] = "Ward Overview"
                        st.rerun()
                    else:
                        st.error("Failed to admit patient. Please check the database connection.")

        st.markdown("</div>", unsafe_allow_html=True)
