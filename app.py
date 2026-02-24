"""
app.py - IVF Tâm Anh HN | Quality Audit System
Main Streamlit Application
"""
import sys
import os

# Fix: đảm bảo thư mục gốc của project luôn có trong sys.path
# (cần thiết khi deploy trên Streamlit Cloud)
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import streamlit as st

# ── Page config (MUST be first Streamlit command) ─────────────────────────────
st.set_page_config(
    page_title="Quality Audit | IVF Tâm Anh HN",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Sidebar styling */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a3a6e 0%, #2c6db5 100%);
}
[data-testid="stSidebar"] * {
    color: white !important;
}
[data-testid="stSidebar"] .stRadio > label {
    color: white !important;
}

/* Header */
.main-header {
    background: linear-gradient(90deg, #1a3a6e, #2c6db5);
    color: white;
    padding: 15px 25px;
    border-radius: 10px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.main-header h1 {
    margin: 0;
    font-size: 22px;
    font-weight: 700;
}
.main-header p {
    margin: 0;
    font-size: 13px;
    opacity: 0.85;
}

/* Cards */
.metric-card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 15px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

/* Tab styling */
.stTabs [data-baseweb="tab"] {
    font-weight: 600;
}

/* Buttons */
.stButton > button {
    border-radius: 8px;
    font-weight: 600;
}

/* Forms */
.stForm {
    background: #f8f9fa;
    border-radius: 10px;
    padding: 10px;
}
</style>
""", unsafe_allow_html=True)

# ── Imports ────────────────────────────────────────────────────────────────────
from utils.auth import require_login, is_admin, current_user, logout, init_session

# Initialize session
init_session()

# Require authentication
require_login()

# ── Import modules ─────────────────────────────────────────────────────────────
from modules import module1_planning
from modules import module2_reporting
from modules import module3_dashboard
from modules import module4_export
from modules import module5_users
from modules import module6_options

# ── Sidebar Navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 10px 0 20px 0;'>
        <div style='font-size: 36px;'>🏥</div>
        <div style='font-size: 15px; font-weight: 700; line-height: 1.3;'>
            IVF Tâm Anh HN
        </div>
        <div style='font-size: 11px; opacity: 0.8; margin-top: 3px;'>
            Quality Audit System
        </div>
    </div>
    """, unsafe_allow_html=True)

    user = current_user()
    if user:
        st.markdown(f"""
        <div style='background: rgba(255,255,255,0.15); border-radius: 8px; 
                    padding: 8px 12px; margin-bottom: 15px; font-size: 13px;'>
            👤 <b>{user.get('full_name', user['username'])}</b><br>
            <span style='opacity:0.8; font-size:11px;'>{user.get('role','').upper()}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**📌 Menu**")

    PAGES = {
        "📋 Kế hoạch Audit": "module1",
        "📝 Kết quả Audit": "module2",
        "📊 Dashboard": "module3",
        "📤 Xuất Báo cáo": "module4",
        "👥 Quản lý Users": "module5",
        "⚙️ Cấu hình": "module6"
    }

    # Filter pages based on role
    if not is_admin():
        PAGES.pop("👥 Quản lý Users", None)

    selected_page = st.radio(
        "Chọn module",
        list(PAGES.keys()),
        label_visibility="collapsed"
    )

    st.markdown("---")
    if st.button("🚪 Đăng xuất", use_container_width=True):
        logout()
        st.rerun()

    st.markdown("""
    <div style='text-align:center; font-size:10px; opacity:0.6; margin-top:20px;'>
        v1.0.0 | IVF Tâm Anh HN<br>Quality Audit System
    </div>
    """, unsafe_allow_html=True)

# ── Main Content ───────────────────────────────────────────────────────────────

# Header bar
user = current_user()
st.markdown(f"""
<div class="main-header">
    <div>
        <h1>🏥 Quality Audit System</h1>
        <p>IVF Tâm Anh HN – Hệ thống Quản lý Kiểm tra Chất lượng</p>
    </div>
    <div style='text-align:right; font-size:13px; opacity:0.9;'>
        {selected_page}
    </div>
</div>
""", unsafe_allow_html=True)

# Route to correct module
page_key = PAGES[selected_page]

if page_key == "module1":
    module1_planning.render()
elif page_key == "module2":
    module2_reporting.render()
elif page_key == "module3":
    module3_dashboard.render()
elif page_key == "module4":
    module4_export.render()
elif page_key == "module5":
    module5_users.render()
elif page_key == "module6":
    module6_options.render()
