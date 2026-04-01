"""
utils/helpers.py — Shared design tokens and UI components for SafeStep.
"""

import streamlit as st

# ── Color Palette ─────────────────────────────────────────────────────────────
PRIMARY = "#4A90D9"       # Light blue accents
BG_WHITE = "#FFFFFF"      # Pure white background
BG_LIGHT = "#F8FAFC"      # Subtle greyish-white for cards
TEXT_DARK = "#2D2D2D"     # Dark charcoal text
TEXT_GREY = "#6B6B6B"     # Secondary grey text
BORDER = "#E2E8F0"        # Light borders

# Risk level colors
RISK_COLORS = {
    "Safe": "#3DAA6F",
    "Watch": "#C4A000",
    "High Risk": "#E87B35",
    "Critical": "#D64045",
    "Pending": "#9CA3AF"
}

RISK_BG = {
    "Safe": "#F0FBF5",
    "Watch": "#FFFBEA",
    "High Risk": "#FFF5EE",
    "Critical": "#FFF0F0",
    "Pending": "#F3F4F6"
}


# ── Global CSS ────────────────────────────────────────────────────────────────
def inject_global_css():
    """Injects core typography and layout styling."""
    css = f"""
    <style>
    /* Typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
        color: {TEXT_DARK};
    }}
    
    /* Global Background */
    .stApp {{
        background-color: {BG_WHITE};
    }}

    /* Sidebar Styling */
    [data-testid="stSidebar"] {{
        background-color: {BG_LIGHT};
        border-right: 1px solid {BORDER};
    }}

    /* Button Styling */
    .stButton>button {{
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.2s;
    }}
    
    /* Remove default Streamlit top padding */
    .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# ── Reusable UI Components ────────────────────────────────────────────────────
def page_header(title: str, subtitle: str = "") -> None:
    html = f"""
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1rem;">
    <div>
        <h1 style="color:{TEXT_DARK};font-weight:800;margin:0;padding:0;font-size:2.2rem;line-height:1.2;">{title}</h1>
        <div style="color:{TEXT_GREY};font-weight:500;font-size:1rem;margin-top:0.2rem;">{subtitle}</div>
    </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


def risk_badge(level: str, score: float = None) -> str:
    color = RISK_COLORS.get(level, RISK_COLORS["Pending"])
    bg = RISK_BG.get(level, RISK_BG["Pending"])
    
    score_text = f" &nbsp;|&nbsp; {score:.0f}" if score is not None else ""
    
    html = f"""
<div style="background-color:{bg};color:{color};border:1px solid {color}50;
            padding:0.4rem 0.8rem;border-radius:20px;font-weight:700;
            font-size:0.85rem;display:inline-block;">
    {level}{score_text}
</div>
"""
    return html


def info_box(text: str, color: str = PRIMARY, icon: str = "ℹ️") -> str:
    html = f"""
<div style="background:{BG_LIGHT};border-left:4px solid {color};
            border-radius:8px;padding:0.8rem 1rem;font-size:0.87rem;
            color:{TEXT_DARK};margin:0.5rem 0;">
    {icon} {text}
</div>
"""
    return html
