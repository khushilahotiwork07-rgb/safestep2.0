"""
page_modules/patient_detail.py — Deep-dive patient monitoring page.
Real-time vitals, prediction models, and live charting.
"""

import streamlit as st
import streamlit.components.v1 as components
import textwrap
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from patients import get_patient_detail, get_patients_with_status, get_patient_by_id
from time_predictor import predict_attention_window
from database import get_last_nurse_visit_time, insert_nurse_visit, get_vitals_last_hour, get_risk_score_history
from utils.helpers import inject_global_css, PRIMARY, TEXT_DARK, TEXT_GREY, BORDER, BG_LIGHT, BG_WHITE

# ── Chart builders ─────────────────────────────────────────────────────────────

def _vital_line_chart(df: pd.DataFrame, y_col: str, title: str, 
                      normal_color: str, threshold: float, is_lower_bound: bool,
                      y_range: list) -> go.Figure:
    fig = go.Figure()

    latest_val = df[y_col].iloc[-1] if not df.empty else 0
    if latest_val is None or pd.isna(latest_val):
        latest_val = 0
        
    is_danger = (float(latest_val) < threshold) if is_lower_bound else (float(latest_val) > threshold)
    active_color = "#D64045" if is_danger else normal_color
    
    r, g, b = int(active_color[1:3], 16), int(active_color[3:5], 16), int(active_color[5:], 16)
    
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df[y_col],
        mode="lines",
        line=dict(color=active_color, width=2.5),
        fill="tozeroy",
        fillcolor=f"rgba({r},{g},{b},0.08)",
        hovertemplate=f"<b>%{{y:.1f}}</b><extra>{title}</extra>",
    ))
    
    fig.add_hline(y=threshold, line_width=2, line_dash="dot", line_color="#D64045", opacity=0.8)

    fig.update_layout(
        title=title,
        height=220,
        margin=dict(l=5, r=5, t=30, b=5),
        paper_bgcolor=BG_WHITE,
        plot_bgcolor=BG_WHITE,
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=True, gridcolor="#EEF2F8", range=y_range),
        font=dict(family="Inter", color=TEXT_GREY, size=10),
    )
    return fig

def _risk_gauge(score: float) -> go.Figure:
    if score <= 40: color = "#3DAA6F"; label = "Safe"
    elif score <= 65: color = "#C4A000"; label = "Watch"
    elif score <= 85: color = "#E87B35"; label = "High Risk"
    else: color = "#D64045"; label = "Critical"

    fig = go.Figure(go.Indicator(
        mode="gauge",
        value=score,
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor=BORDER, tickvals=[0, 41, 66, 86, 100]),
            bar=dict(color=color, thickness=0.3),
            bgcolor=BG_WHITE,
            borderwidth=0,
            steps=[
                dict(range=[0,  40], color="#E8F6ED"),
                dict(range=[41, 65], color="#FFF9E5"),
                dict(range=[66, 85], color="#FFECE3"),
                dict(range=[86,100], color="#FFEBEB"),
            ],
            threshold=dict(line=dict(color=color, width=4), thickness=0.8, value=score),
        ),
        domain=dict(x=[0, 1], y=[0, 1]),
    ))
    fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10))
    return fig, color, label

def render():
    inject_global_css()
    st.markdown("## 👤 Patient Detail")

    patients = get_patients_with_status()
    if not patients:
        st.error("No patients found in memory.")
        return

    all_ids = [p["id"] for p in patients]
    if not all_ids:
        st.warning("No patients currently tracked. Please admit a patient first.")
        return

    sel_id = st.session_state.get("selected_patient_id", all_ids[0])
    chosen_id = st.selectbox(
        "Select Patient",
        all_ids,
        index=all_ids.index(sel_id) if sel_id in all_ids else 0,
        format_func=lambda i: next((p["name"] for p in patients if p["id"] == i), f"Patient {i}"),
        label_visibility="collapsed"
    )
    st.session_state["selected_patient_id"] = chosen_id

    patient = get_patient_detail(chosen_id)
    if not patient: return

    score = patient["risk_score"] or 0
    hist = get_vitals_last_hour(chosen_id)
    df_vitals = pd.DataFrame(hist) if hist else pd.DataFrame()
    if not df_vitals.empty and "blood_sugar" not in df_vitals.columns:
        df_vitals["blood_sugar"] = 90
    if not df_vitals.empty and "spo2" not in df_vitals.columns:
        df_vitals["spo2"] = 98

    f_idx = patient.get("frailty_index", "1/9")
    f_num = float(f_idx.split("/")[0]) if "/" in f_idx else 0
    f_pct = (f_num / 9) * 100

    col_prof, col_gauge = st.columns([1.5, 1])

    with col_prof:
        html_prof = f"""
<div style="background:{BG_LIGHT};border:1px solid {BORDER};border-radius:12px;padding:1.2rem;">
<div style="font-size:1.6rem;font-weight:800;color:{TEXT_DARK};margin-bottom:8px;">{patient['name']}</div>
<div style="display:flex;gap:1.5rem;font-size:0.9rem;color:{TEXT_GREY};margin-bottom:1rem;">
<div><strong>Age:</strong> {patient['age']}</div>
<div><strong>Gender:</strong> {patient['gender']}</div>
<div><strong>Bed:</strong> {patient['ward']} {patient['bed']}</div>
<div><strong>Admitted:</strong> {patient['admitted_on']}</div>
</div>
<hr style="margin:0.5rem 0;">
<div style="margin-bottom:1rem;">
<div style="font-size:0.8rem;font-weight:600;color:{TEXT_DARK};margin-bottom:4px;">Frailty Index: {f_idx}</div>
<div style="background:#E0E8F0;height:8px;border-radius:4px;width:100%;">
<div style="background:{PRIMARY};height:8px;border-radius:4px;width:{f_pct}%;"></div>
</div>
</div>
<table style="width:100%;font-size:0.85rem;color:{TEXT_DARK};border-spacing:0 6px;">
<tr><td style="width:130px;color:{TEXT_GREY};">EPA FRAT:</td><td>{patient.get('epa_frat','—')}</td></tr>
<tr><td style="color:{TEXT_GREY};">Medications:</td><td>{patient.get('medications','—')}</td></tr>
<tr><td style="color:{TEXT_GREY};">Mobility Base:</td><td>{patient.get('mobility','—')}</td></tr>
<tr><td style="color:{TEXT_GREY};">Toileting Base:</td><td>{patient.get('toileting','—')}</td></tr>
<tr><td style="color:{TEXT_GREY};">Confusion Score:</td><td>{patient.get('confusion','—')}</td></tr>
<tr><td style="color:{TEXT_GREY};">Fall History:</td><td>{patient.get('fall_history','—')}</td></tr>
</table>
</div>
"""
        html_prof = "".join(line.strip() for line in html_prof.splitlines())
        st.markdown(html_prof, unsafe_allow_html=True)

        # ── Persistent Medical Condition Checkboxes ──
        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(f"<div style='font-size:0.85rem;font-weight:700;color:{TEXT_DARK};margin-bottom:0.5rem;'>Active Medical Conditions</div>", unsafe_allow_html=True)
            col_ost, col_epi = st.columns(2)
            
            from database import update_patient_conditions
            
            with col_ost:
                has_ost = st.toggle("Osteoporosis", value=patient.get("has_osteoporosis", False), key=f"ost_{chosen_id}")
            with col_epi:
                has_epi = st.toggle("Epileptic Seizures", value=patient.get("has_epilepsy", False), key=f"epi_{chosen_id}")
            
            # Save if changed
            if has_ost != patient.get("has_osteoporosis") or has_epi != patient.get("has_epilepsy"):
                update_patient_conditions(chosen_id, has_ost, has_epi)
                st.toast(f"Updated clinical conditions for {patient['name']}", icon="✅")


    with col_gauge:
        fig_gauge, g_color, g_label = _risk_gauge(score)
        st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar":False})
        
        html_score = f"""
<div style="text-align:center;margin-top:-60px;">
<div style="font-size:3.5rem;font-weight:900;line-height:1;color:{g_color};">{score:.0f}</div>
<div style="font-size:1.2rem;font-weight:800;text-transform:uppercase;color:{g_color};">{g_label}</div>
</div>
"""
        html_score = "".join(l.strip() for l in html_score.splitlines())
        st.markdown(html_score, unsafe_allow_html=True)

    st.markdown("<hr style='margin:1.5rem 0;'>", unsafe_allow_html=True)

    # ── 2. Reasons and Predictor Columns ──────────────────────────────────────
    col_reasons, col_warnings = st.columns(2)

    with col_reasons:
        st.markdown("#### 🚨 Why Is This Patient At Risk")
        reasons = patient.get("reasons", [])
        if reasons:
            for r in reasons:
                st.markdown(f"⚠️ {r}")
        else:
            st.success("No elevated risk factors detected.")

    with col_warnings:
        st.markdown("#### ⏰ Attention Warnings")
        last_visit = get_last_nurse_visit_time(chosen_id)
        from database import get_latest_vitals
        curr_v = get_latest_vitals(chosen_id) or {}
        warnings = predict_attention_window(patient, curr_v, hist, datetime.now(), last_visit)
        
        if warnings:
            for w in warnings:
                st.markdown(f"🕒 {w}")
        else:
            st.info("No immediate time-based warnings.")

    st.markdown("<hr style='margin:1rem 0;'>", unsafe_allow_html=True)
    
    # ── 3. Live Digital Monitor & Charts (Fragmented for no flicker) ───────────
    @st.fragment(run_every=5)
    def render_live_data(p_id):
        # Refresh patient and vitals inside fragment
        p = get_patient_detail(p_id)
        if not p: return

        v = p.get("vitals", {}) or {}
        hr = v.get("heart_rate", "—")
        sbp = v.get("blood_pressure_systolic", "—")
        dbp = v.get("blood_pressure_diastolic", "—")
        spo2 = v.get("spo2", "—")
        
        hr_str = f"{hr:.0f}" if isinstance(hr, (int, float)) else str(hr)
        bp_str = f"{sbp:.0f}/{dbp:.0f}" if isinstance(sbp, (int, float)) else "—/—"
        spo2_str = f"{spo2:.0f}" if isinstance(spo2, (int, float)) else str(spo2)
        
        html_monitor = f"""
<div style="background:{BG_WHITE}; border:2px solid {BORDER}; border-radius:16px; padding:1.5rem; margin-bottom:1.5rem; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
    <div style="display:grid; grid-template-columns: 1fr 1.2fr 1fr; gap:20px; background:rgba(0,0,0,0.02); padding:1.5rem; border-radius:12px;">
        <div style="text-align:center;">
            <div style="font-size:0.8rem; font-weight:700; color:{TEXT_GREY}; margin-bottom:4px; text-transform:uppercase;">Heart Rate</div>
            <div style="font-size:3rem; font-weight:900; color:{PRIMARY}; font-family:'Courier New', monospace;">{hr_str}</div>
            <div style="font-size:0.75rem; font-weight:600; color:{TEXT_GREY};">BPM</div>
        </div>
        <div style="text-align:center; border-left:2px solid rgba(0,0,0,0.05); border-right:2px solid rgba(0,0,0,0.05);">
            <div style="font-size:0.8rem; font-weight:700; color:{TEXT_GREY}; margin-bottom:4px; text-transform:uppercase;">Blood Pressure (NIBP)</div>
            <div style="font-size:3rem; font-weight:900; color:{TEXT_DARK}; font-family:'Courier New', monospace;">{bp_str}</div>
            <div style="font-size:0.75rem; font-weight:600; color:{TEXT_GREY};">mmHg</div>
        </div>
        <div style="text-align:center;">
            <div style="font-size:0.8rem; font-weight:700; color:{TEXT_GREY}; margin-bottom:4px; text-transform:uppercase;">Oxygen Level (SpO2)</div>
            <div style="font-size:3rem; font-weight:900; color:#3DAA6F; font-family:'Courier New', monospace;">{spo2_str}%</div>
            <div style="font-size:0.75rem; font-weight:600; color:{TEXT_GREY};">Saturation</div>
        </div>
    </div>
</div>
"""
        html_monitor = "".join(l.strip() for l in html_monitor.splitlines())
        st.markdown(html_monitor, unsafe_allow_html=True)

        st.markdown("#### 📊 Live Vitals (Last 5 Minutes)")
        hist = get_vitals_last_hour(p_id)
        df_v = pd.DataFrame(hist) if hist else pd.DataFrame()
        
        if not df_v.empty:
            if "blood_sugar" not in df_v.columns: df_v["blood_sugar"] = 90
            if "spo2" not in df_v.columns: df_v["spo2"] = 98
            s_col = "blood_pressure_systolic" if "blood_pressure_systolic" in df_v else "systolic_bp"
            
            gv1, gv2, gv3, gv4 = st.columns(4)
            with gv1:
                st.plotly_chart(_vital_line_chart(df_v, "heart_rate", "Heart Rate (bpm)", PRIMARY, 110.0, False, [40, 160]), use_container_width=True, config={"displayModeBar":False})
            with gv2:
                st.plotly_chart(_vital_line_chart(df_v, s_col, "Systolic BP (mmHg)", PRIMARY, 90.0, True, [60, 200]), use_container_width=True, config={"displayModeBar":False})
            with gv3:
                st.plotly_chart(_vital_line_chart(df_v, "spo2", "SpO₂ (%)", PRIMARY, 90.0, True, [80, 100]), use_container_width=True, config={"displayModeBar":False})
            with gv4:
                st.plotly_chart(_vital_line_chart(df_v, "blood_sugar", "Blood Sugar (mg/dL)", PRIMARY, 65.0, True, [40, 200]), use_container_width=True, config={"displayModeBar":False})
        else:
            st.warning("No vitals data recorded yet.")

    # Call the fragment
    render_live_data(chosen_id)

    # ── 5. Risk Score History (Last 6 Hours) ───────────────────────────────────
    st.markdown("#### 📈 Risk Score Trend (Last 6 Hours)")
    df_risk = pd.DataFrame(get_risk_score_history(chosen_id))
    if not df_risk.empty:
        try:
            df_risk['timestamp'] = pd.to_datetime(df_risk['timestamp'])
            df_risk = df_risk[df_risk['timestamp'] >= (pd.Timestamp.now() - pd.Timedelta(hours=6))]
            
            fig_risk = go.Figure()
            fig_risk.add_trace(go.Scatter(
                x=df_risk["timestamp"], y=df_risk["final_score"],
                mode="lines+markers",
                line=dict(color="#2D2D2D", width=3),
                marker=dict(size=6, color="#2D2D2D"),
                hovertemplate="Score: %{y}<br>Time: %{x}<extra></extra>"
            ))
            fig_risk.add_hrect(y0=0, y1=40, fillcolor="#F0FBF5", opacity=0.3, line_width=0)
            fig_risk.add_hrect(y0=41, y1=65, fillcolor="#FFFBEA", opacity=0.3, line_width=0)
            fig_risk.add_hrect(y0=66, y1=85, fillcolor="#FFF5EE", opacity=0.3, line_width=0)
            fig_risk.add_hrect(y0=86, y1=100, fillcolor="#FFF0F0", opacity=0.3, line_width=0)

            fig_risk.update_layout(
                height=250, margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor=BG_WHITE, plot_bgcolor=BG_WHITE,
                yaxis=dict(range=[0, 100], showgrid=True, gridcolor="#EEF2F8"),
            )
            st.plotly_chart(fig_risk, use_container_width=True, config={"displayModeBar":False})
        except Exception:
            pass 

    # ── 6. Log Nurse Visit Form ────────────────────────────────────────────────
    st.markdown("<hr style='margin:1.5rem 0;'>", unsafe_allow_html=True)
    with st.popover("➕ Log Nurse Visit", use_container_width=True):
        st.markdown("##### Record Visit / Intervention")
        with st.form("nurse_visit_form", clear_on_submit=True):
            nurse = st.text_input("Nurse Name", placeholder="e.g. Sister Maria")
            action = st.text_area("Action Taken / Notes", placeholder="e.g. Assisted to bathroom, raised rails.")
            if st.form_submit_button("Save Record", use_container_width=True):
                if nurse and action:
                    insert_nurse_visit(chosen_id, nurse, action)
                    st.success("Nurse visit logged successfully!")
                    st.rerun()
                else:
                    st.error("Please fill out both fields.")
