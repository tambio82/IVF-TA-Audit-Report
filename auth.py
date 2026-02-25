"""
auth.py - Authentication helpers
"""
import bcrypt
import streamlit as st
from db import get_db, fetch_all, insert_record, update_record, delete_record


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


def login(username: str, password: str) -> dict | None:
    db = get_db()
    result = db.table("audit_users").select("*").eq("username", username).eq("is_active", True).execute()
    users = result.data
    if not users:
        return None
    user = users[0]
    if verify_password(password, user["password_hash"]):
        return user
    return None


def init_session():
    if "user" not in st.session_state:
        st.session_state.user = None


def is_logged_in() -> bool:
    return st.session_state.get("user") is not None


def is_admin() -> bool:
    u = st.session_state.get("user")
    return u and u.get("role") == "admin"


def current_user() -> dict | None:
    return st.session_state.get("user")


def logout():
    st.session_state.user = None


def require_login():
    init_session()
    if not is_logged_in():
        show_login_page()
        st.stop()


def show_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🏥 IVF Tâm Anh HN")
        st.markdown("#### Quality Audit System")
        st.markdown("---")

        with st.form("login_form"):
            username = st.text_input("👤 Tên đăng nhập")
            password = st.text_input("🔒 Mật khẩu", type="password")
            submitted = st.form_submit_button("Đăng nhập", use_container_width=True)

        if submitted:
            user = login(username, password)
            if user:
                st.session_state.user = user
                st.success(f"Chào mừng, {user.get('full_name', username)}!")
                st.rerun()
            else:
                st.error("Sai tên đăng nhập hoặc mật khẩu.")

    # Auto-create default admin if no users exist
    db = get_db()
    count = db.table("audit_users").select("id", count="exact").execute().count
    if count == 0:
        st.info("💡 Chưa có tài khoản. Tạo admin mặc định: **admin / Admin@123**")
        insert_record("audit_users", {
            "username": "admin",
            "password_hash": hash_password("Admin@123"),
            "full_name": "Administrator",
            "role": "admin",
            "is_active": True
        })
