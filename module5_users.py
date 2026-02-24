"""
modules/module5_users.py - Quản lý người dùng
"""
import sys, os; _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, _root) if _root not in sys.path else None

import streamlit as st
from utils.db import get_db, fetch_all, insert_record, update_record, delete_record
from utils.auth import hash_password, is_admin, current_user

ROLES = {
    "admin": "👑 Admin (toàn quyền)",
    "auditor": "📝 Auditor (nhập liệu)",
    "viewer": "👁️ Viewer (chỉ xem)"
}


def render():
    st.title("👥 Module 5: Quản lý Người dùng")

    if not is_admin():
        st.error("⛔ Chỉ Admin mới có quyền quản lý người dùng.")
        return

    tab_list, tab_create = st.tabs(["📋 Danh sách Users", "➕ Tạo User mới"])

    with tab_list:
        render_user_list()

    with tab_create:
        render_create_user()


def render_user_list():
    st.subheader("Danh sách người dùng")
    users = fetch_all("audit_users", order="created_at")
    me = current_user()

    if not users:
        st.info("Chưa có người dùng nào.")
        return

    for user in users:
        is_me = me and user["id"] == me["id"]
        status_badge = "🟢" if user["is_active"] else "🔴"
        role_label = ROLES.get(user["role"], user["role"])

        with st.expander(
            f"{status_badge} {user.get('full_name', user['username'])} "
            f"(@{user['username']}) — {role_label} {'[Bạn]' if is_me else ''}",
            expanded=False
        ):
            with st.form(f"form_edit_user_{user['id']}"):
                col1, col2 = st.columns(2)
                with col1:
                    full_name = st.text_input("Tên hiển thị", value=user.get("full_name", ""))
                    role = st.selectbox("Vai trò", list(ROLES.keys()),
                                        index=list(ROLES.keys()).index(user["role"]) if user["role"] in ROLES else 1,
                                        format_func=lambda x: ROLES[x])
                with col2:
                    is_active = st.checkbox("Kích hoạt tài khoản", value=user["is_active"])
                    new_password = st.text_input("Mật khẩu mới (để trống = không đổi)", type="password")

                col_save, col_del = st.columns([3, 1])
                with col_save:
                    if st.form_submit_button("💾 Lưu thay đổi", use_container_width=True):
                        update_data = {
                            "full_name": full_name,
                            "role": role,
                            "is_active": is_active
                        }
                        if new_password:
                            update_data["password_hash"] = hash_password(new_password)
                        update_record("audit_users", user["id"], update_data)
                        st.success("✅ Đã cập nhật!")
                        st.rerun()

                with col_del:
                    if not is_me:
                        if st.form_submit_button("🗑️ Xóa", use_container_width=True):
                            delete_record("audit_users", user["id"])
                            st.success("Đã xóa!")
                            st.rerun()
                    else:
                        st.caption("Không thể tự xóa bản thân")


def render_create_user():
    st.subheader("Tạo tài khoản mới")

    with st.form("form_create_user", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("Tên đăng nhập *")
            full_name = st.text_input("Tên hiển thị")
        with col2:
            password = st.text_input("Mật khẩu *", type="password")
            role = st.selectbox("Vai trò", list(ROLES.keys()), format_func=lambda x: ROLES[x])

        if st.form_submit_button("✅ Tạo tài khoản", use_container_width=True):
            if not username.strip():
                st.error("Tên đăng nhập không được để trống!")
                return
            if len(password) < 6:
                st.error("Mật khẩu phải có ít nhất 6 ký tự!")
                return

            db = get_db()
            existing = db.table("audit_users").select("id").eq("username", username).execute()
            if existing.data:
                st.error(f"Tên đăng nhập '{username}' đã tồn tại!")
                return

            insert_record("audit_users", {
                "username": username.strip(),
                "password_hash": hash_password(password),
                "full_name": full_name.strip(),
                "role": role,
                "is_active": True
            })
            st.success(f"✅ Tạo thành công tài khoản: {username}")
