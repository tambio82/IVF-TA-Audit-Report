"""
modules/module6_options.py - Quản lý cấu hình và biến số
"""
import streamlit as st
from db import get_db, insert_record, update_record, delete_record, fetch_all
from auth import is_admin


def render():
    st.title("⚙️ Module 6: Quản lý Cấu hình")

    if not is_admin():
        st.warning("⚠️ Một số tùy chỉnh chỉ Admin mới thực hiện được.")

    tab_dept, tab_options = st.tabs(["🏢 Bộ phận", "⚙️ Tùy chỉnh khác"])

    with tab_dept:
        render_departments()

    with tab_options:
        render_general_options()


def render_departments():
    st.subheader("🏢 Quản lý Bộ phận")

    departments = fetch_all("departments", order="sort_order")

    # Display existing
    for dept in departments:
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        with col1:
            st.write(dept["name"])
        with col2:
            st.caption(dept.get("code", ""))
        with col3:
            status = "🟢 Hoạt động" if dept["is_active"] else "🔴 Tắt"
            st.write(status)
        with col4:
            if is_admin():
                if st.button("✏️", key=f"edit_dept_{dept['id']}", help="Sửa"):
                    st.session_state[f"editing_dept"] = dept["id"]

        # Inline edit
        if st.session_state.get("editing_dept") == dept["id"]:
            with st.form(f"form_edit_dept_{dept['id']}"):
                new_name = st.text_input("Tên bộ phận", value=dept["name"])
                new_code = st.text_input("Mã bộ phận", value=dept.get("code", ""))
                new_sort = st.number_input("Thứ tự hiển thị", value=dept.get("sort_order", 0), step=1)
                new_active = st.checkbox("Đang hoạt động", value=dept["is_active"])
                col_s, col_c = st.columns(2)
                with col_s:
                    if st.form_submit_button("💾 Lưu"):
                        update_record("departments", dept["id"], {
                            "name": new_name, "code": new_code,
                            "sort_order": int(new_sort), "is_active": new_active
                        })
                        st.session_state.pop("editing_dept", None)
                        st.success("✅ Đã cập nhật!")
                        st.rerun()
                with col_c:
                    if st.form_submit_button("✖️ Hủy"):
                        st.session_state.pop("editing_dept", None)
                        st.rerun()

        st.divider()

    # Add new department
    st.markdown("---")
    st.subheader("➕ Thêm Bộ phận mới")
    if is_admin():
        with st.form("form_add_dept", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                new_name = st.text_input("Tên bộ phận *")
            with col2:
                new_code = st.text_input("Mã bộ phận")
            with col3:
                new_sort = st.number_input("Thứ tự", value=len(departments) + 1, step=1)

            if st.form_submit_button("➕ Thêm", use_container_width=True):
                if not new_name.strip():
                    st.error("Tên không được để trống!")
                else:
                    insert_record("departments", {
                        "name": new_name.strip(),
                        "code": new_code.strip(),
                        "sort_order": int(new_sort),
                        "is_active": True
                    })
                    st.success(f"✅ Đã thêm bộ phận: {new_name}")
                    st.rerun()
    else:
        st.info("Chỉ Admin mới có thể thêm bộ phận mới.")


def render_general_options():
    st.subheader("⚙️ Cài đặt chung")

    db = get_db()
    configs = db.table("audit_config").select("*").execute().data or []
    config_map = {c["config_key"]: c for c in configs}

    # Available years setting
    st.markdown("**📅 Năm Audit**")
    current_years = config_map.get("available_years", {}).get("config_value", [2025, 2026, 2027, 2028])
    if not isinstance(current_years, list):
        current_years = [2025, 2026, 2027, 2028]

    with st.form("form_years_config"):
        years_text = st.text_input("Các năm (cách nhau bởi dấu phẩy)",
                                    value=", ".join(map(str, current_years)))
        if st.form_submit_button("💾 Lưu"):
            try:
                new_years = [int(y.strip()) for y in years_text.split(",") if y.strip()]
                if "available_years" in config_map:
                    update_record("audit_config", config_map["available_years"]["id"],
                                   {"config_value": new_years})
                else:
                    insert_record("audit_config", {
                        "config_key": "available_years",
                        "config_value": new_years,
                        "description": "Danh sách năm audit"
                    })
                st.success("✅ Đã lưu!")
                st.rerun()
            except ValueError:
                st.error("Định dạng không hợp lệ. Vui lòng nhập số năm cách nhau bởi dấu phẩy.")

    st.markdown("---")
    st.markdown("**ℹ️ Hướng dẫn cấu hình thang điểm FMEA**")
    st.markdown("""
    | Chỉ số | Ý nghĩa | Thang điểm |
    |--------|---------|------------|
    | **S** - Severity | Mức độ nghiêm trọng của sai lỗi | 1 (Không đáng kể) → 10 (Nguy hiểm) |
    | **O** - Occurrence | Tần suất xảy ra nguyên nhân | 1 (Rất hiếm) → 10 (Rất thường xuyên) |
    | **D** - Detection | Khả năng phát hiện lỗi | 1 (Dễ phát hiện) → 10 (Rất khó phát hiện) |
    | **RPN** | Risk Priority Number | RPN = S × O × D (1-1000) |
    """)
    st.info("💡 RPN > 200: Cần hành động khẩn cấp | 100-200: Cần cải thiện | < 100: Theo dõi")

    st.markdown("---")
    st.markdown("**📊 Thang điểm Định lượng**")
    st.markdown("""
    | Điểm | Phân loại |
    |------|-----------|
    | < 3.0 | 🔴 Dưới kỳ vọng |
    | 3.0 - 4.0 | 🟡 Tạm chấp nhận |
    | > 4.0 | 🟢 Kết quả ổn |
    """)
