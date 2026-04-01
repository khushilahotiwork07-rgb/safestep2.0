"""
page_modules/login.py — SafeStep Hospital Login Interface.
A professional, secure-looking entrance for demonstration purposes.
"""

import streamlit as st
from utils.helpers import PRIMARY, TEXT_DARK, TEXT_GREY, BG_LIGHT, inject_global_css

def render():
    inject_global_css()
    
    # Custom CSS for the login card
    st.markdown("""
    <style>
    .login-container {
        max-width: 450px;
        margin: 5rem auto;
        padding: 2.5rem;
        background: white;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        border: 1px solid #E2E8F0;
    }
    .stSelectbox, .stTextInput {
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Creating a centered layout
    _, col, _ = st.columns([1, 2, 1])

    with col:
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 2rem;">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🏥</div>
            <h1 style="color: {PRIMARY}; font-weight: 800; margin: 0; font-size: 2rem;">SafeStep</h1>
            <p style="color: {TEXT_GREY}; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">
                Patient Fall Risk System
            </p>
        </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown(f"<h3 style='color:{TEXT_DARK}; font-weight:700; margin-bottom:1.5rem; border-bottom:1px solid #EEE; padding-bottom:0.5rem;'>Clinical Staff Login</h3>", unsafe_allow_html=True)
            
            hospital = st.selectbox(
                "Select Hospital Facility",
                [
                    "St. Mary's General Hospital",
                    "City Central Medical Center",
                    "Green Valley Specialty Clinic",
                    "Metropolitan Health Institute",
                    "Sunrise Community Hospital"
                ],
                index=0
            )
            
            username = st.text_input("Username", placeholder="e.g. admin").strip()
            password = st.text_input("Password", type="password", placeholder="••••••••").strip()
            
            st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
            st.info("Demo credentials: `admin` / `safestep2026`", icon="🔑")
            
            if st.button("Access Dashboard", use_container_width=True, type="primary"):
                # Simple demonstration authentication logic
                if username == "admin" and password == "safestep2026":
                    st.session_state["logged_in"] = True
                    st.session_state["hospital_name"] = hospital
                    st.session_state["username"] = username
                    st.success("Login successful! Redirecting...")
                    st.rerun()
                elif not username or not password:
                    st.warning("Please enter your credentials.")
                else:
                    st.error("Invalid username or password.")

        st.markdown(f"""
        <div style="text-align: center; margin-top: 2rem; color: {TEXT_GREY}; font-size: 0.8rem;">
            © 2026 SafeStep Clinical Analytics. All rights reserved.<br>
            Authorized medical staff access only.
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    render()
