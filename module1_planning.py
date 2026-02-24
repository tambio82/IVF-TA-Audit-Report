"""
modules/module1_planning.py - Quản lý mục tiêu và kế hoạch Quality Audit
"""
import sys, os; _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, _root) if _root not in sys.path else None

import streamlit as st
from datetime import date
from utils.db import (
    get_db, fetch_all, insert_record, update_record, delete_record,
    get_plans, get_objectives_for_plan, get_kpis_for_objective,
    get_departments, get_department_map
)
from utils.auth import is_admin

ISSUE_TYPES = {
    "new_objective": "🆕 Mục tiêu mới",
    "additional_monitoring": "🔍 Vấn đề Giám sát Audit thêm"
}

AUDIT_LEVELS = {
    "urgent": "🔴 Urgent - Khẩn cấp",
    "moderate": "🟡 Moderate - Thông thường",
    "intensive": "🟢 Intensive - Chuyên đề kết hợp đào tạo",
    "rtac": "🔵 RTAC - Tiêu chuẩn quốc tế"
}

AUDIT_NATURES = {
    "supplementary": "📎 Bổ sung",
    "mandatory_periodic": "📋 Bắt buộc - Định kỳ",
    "on_request": "📝 Theo yêu cầu"
}

YEARS = [2025, 2026, 2027, 2028, 2029]


def render():
    st.title("📋 Module 1: Quản lý Kế hoạch Quality Audit")

    tab_list, tab_create, tab_edit = st.tabs(["📂 Danh sách đợt", "➕ Tạo đợt mới", "✏️ Chỉnh sửa"])

    with tab_list:
        render_plan_list()

    with tab_create:
        render_create_plan()

    with tab_edit:
        render_edit_plan()


# ── List Plans ────────────────────────────────────────────────────────────────

def render_plan_list():
    st.subheader("Danh sách các đợt Audit")

    col1, col2 = st.columns([2, 3])
    with col1:
        filter_year = st.selectbox("Lọc theo năm", [None] + YEARS,
                                   format_func=lambda x: "Tất cả" if x is None else str(x),
                                   key="list_filter_year")

    plans = get_plans(filter_year)
    if not plans:
        st.info("Chưa có đợt audit nào. Hãy tạo đợt mới.")
        return

    for plan in plans:
        level_label = AUDIT_LEVELS.get(plan["audit_level"], plan["audit_level"])
        nature_label = AUDIT_NATURES.get(plan["audit_nature"], plan["audit_nature"])
        issue_label = ISSUE_TYPES.get(plan["issue_type"], plan["issue_type"])

        with st.expander(
            f"📅 {plan['year']} - Đợt {plan['sequence_no']} | "
            f"{plan['date_from']} → {plan['date_to']} | {level_label}"
        ):
            col1, col2, col3 = st.columns(3)
            col1.metric("Năm", plan["year"])
            col2.metric("Đợt số", plan["sequence_no"])
            col3.metric("Trạng thái", plan.get("status", "planned").upper())

            st.write(f"**Phân loại vấn đề:** {issue_label}")
            st.write(f"**Cấp độ:** {level_label}")
            st.write(f"**Tính chất:** {nature_label}")

            # Show objectives
            objectives = get_objectives_for_plan(plan["id"])
            if objectives:
                st.markdown("**Mục tiêu:**")
                dept_map = get_department_map()
                for obj in objectives:
                    dept_names = [dept_map.get(d, d) for d in (obj.get("department_ids") or [])]
                    st.write(f"  **{obj['objective_no']}.** {obj['objective_text']}")
                    if dept_names:
                        st.caption(f"     🏢 Bộ phận: {', '.join(dept_names)}")
                    kpis = get_kpis_for_objective(obj["id"])
                    for kpi in kpis:
                        st.write(f"     📌 **KPI:** {kpi['kpi_text']}")
                        if kpi.get("expected_outcome"):
                            st.write(f"     🎯 **Outcome dự kiến:** {kpi['expected_outcome']}")

            if is_admin():
                if st.button("🗑️ Xóa đợt này", key=f"del_plan_{plan['id']}"):
                    delete_record("audit_plans", plan["id"])
                    st.success("Đã xóa!")
                    st.rerun()


# ── Create Plan ───────────────────────────────────────────────────────────────

def render_create_plan():
    st.subheader("Tạo đợt Audit mới")

    with st.form("form_create_plan", clear_on_submit=False):
        st.markdown("#### 📌 Thông tin chung")
        col1, col2 = st.columns(2)
        with col1:
            year = st.selectbox("Năm *", YEARS, index=1)
            sequence_no = st.selectbox("Thứ tự đợt *", list(range(1, 13)))
        with col2:
            date_from = st.date_input("Từ ngày *", value=date.today())
            date_to = st.date_input("Đến ngày *", value=date.today())

        col1, col2, col3 = st.columns(3)
        with col1:
            issue_type = st.selectbox(
                "Phân loại vấn đề *",
                list(ISSUE_TYPES.keys()),
                format_func=lambda x: ISSUE_TYPES[x]
            )
        with col2:
            audit_level = st.selectbox(
                "Cấp độ *",
                list(AUDIT_LEVELS.keys()),
                format_func=lambda x: AUDIT_LEVELS[x]
            )
        with col3:
            audit_nature = st.selectbox(
                "Tính chất *",
                list(AUDIT_NATURES.keys()),
                format_func=lambda x: AUDIT_NATURES[x]
            )

        notes = st.text_area("Ghi chú thêm")

        st.markdown("---")
        st.markdown("#### 🎯 Mục tiêu Audit")

        # Dynamic objectives using session state
        if "new_plan_objectives" not in st.session_state:
            st.session_state.new_plan_objectives = [{"text": "", "dept_ids": [], "kpis": [{"kpi": "", "outcome": ""}]}]

        submitted = st.form_submit_button("💾 Lưu Kế hoạch", use_container_width=True)

        if submitted:
            if date_to < date_from:
                st.error("Ngày kết thúc phải sau ngày bắt đầu.")
                return

            # Check duplicate
            db = get_db()
            existing = db.table("audit_plans").select("id").eq("year", year).eq("sequence_no", sequence_no).execute()
            if existing.data:
                st.error(f"Đợt {sequence_no} năm {year} đã tồn tại!")
                return

            plan_data = {
                "year": year,
                "sequence_no": sequence_no,
                "date_from": str(date_from),
                "date_to": str(date_to),
                "issue_type": issue_type,
                "audit_level": audit_level,
                "audit_nature": audit_nature,
                "notes": notes,
                "status": "planned"
            }
            new_plan = insert_record("audit_plans", plan_data)
            if new_plan:
                st.success(f"✅ Tạo thành công đợt {sequence_no} năm {year}!")
                st.session_state.new_plan_id = new_plan["id"]
                st.session_state.new_plan_objectives = [{"text": "", "dept_ids": [], "kpis": [{"kpi": "", "outcome": ""}]}]

    # Objective editor outside form (dynamic add/remove)
    if st.session_state.get("new_plan_id"):
        render_objectives_editor(st.session_state.new_plan_id)


def render_objectives_editor(plan_id: str):
    """Dynamic objectives editor after plan creation."""
    st.markdown("---")
    st.subheader("🎯 Thêm Mục tiêu cho Đợt Audit")

    departments = get_departments()
    dept_options = {d["id"]: d["name"] for d in departments}

    objectives = get_objectives_for_plan(plan_id)
    next_no = max([o["objective_no"] for o in objectives], default=0) + 1

    with st.expander(f"➕ Thêm Mục tiêu #{next_no}", expanded=True):
        with st.form(f"form_obj_{plan_id}_{next_no}"):
            obj_text = st.text_area(f"Nội dung Mục tiêu #{next_no} *")
            dept_ids = st.multiselect(
                "Bộ phận liên quan",
                options=list(dept_options.keys()),
                format_func=lambda x: dept_options.get(x, x)
            )
            st.markdown("**KPIs cho mục tiêu này:**")
            kpi_text = st.text_area("KPI")
            expected_outcome = st.text_area("Kết quả mong đợi (Outcome)")
            save_obj = st.form_submit_button("💾 Lưu Mục tiêu")

            if save_obj and obj_text.strip():
                new_obj = insert_record("audit_objectives", {
                    "plan_id": plan_id,
                    "objective_no": next_no,
                    "objective_text": obj_text.strip(),
                    "department_ids": dept_ids
                })
                if new_obj and kpi_text.strip():
                    insert_record("audit_kpis", {
                        "objective_id": new_obj["id"],
                        "kpi_text": kpi_text.strip(),
                        "expected_outcome": expected_outcome.strip()
                    })
                st.success(f"✅ Đã lưu Mục tiêu #{next_no}")
                st.rerun()

    # Show existing objectives
    if objectives:
        st.markdown("**Mục tiêu đã lưu:**")
        dept_map = get_department_map()
        for obj in objectives:
            dept_names = [dept_map.get(d, d) for d in (obj.get("department_ids") or [])]
            with st.container():
                st.write(f"**{obj['objective_no']}.** {obj['objective_text']}")
                if dept_names:
                    st.caption(f"🏢 {', '.join(dept_names)}")
                kpis = get_kpis_for_objective(obj["id"])
                for kpi in kpis:
                    st.write(f"  📌 {kpi['kpi_text']}")
                    if kpi.get("expected_outcome"):
                        st.caption(f"  🎯 {kpi['expected_outcome']}")

                col1, col2 = st.columns([5, 1])
                with col2:
                    if st.button("🗑️", key=f"del_obj_{obj['id']}", help="Xóa mục tiêu"):
                        delete_record("audit_objectives", obj["id"])
                        st.rerun()
                st.markdown("---")


# ── Edit Plan ─────────────────────────────────────────────────────────────────

def render_edit_plan():
    st.subheader("✏️ Chỉnh sửa đợt Audit")

    plans = get_plans()
    if not plans:
        st.info("Chưa có đợt nào.")
        return

    plan_options = {p["id"]: f"{p['year']} - Đợt {p['sequence_no']} ({p['date_from']})" for p in plans}
    selected_id = st.selectbox("Chọn đợt cần chỉnh sửa",
                                options=list(plan_options.keys()),
                                format_func=lambda x: plan_options[x])

    plan = next((p for p in plans if p["id"] == selected_id), None)
    if not plan:
        return

    with st.form("form_edit_plan"):
        col1, col2 = st.columns(2)
        with col1:
            year = st.selectbox("Năm", YEARS, index=YEARS.index(plan["year"]) if plan["year"] in YEARS else 1)
            sequence_no = st.selectbox("Thứ tự đợt", list(range(1, 13)), index=plan["sequence_no"] - 1)
        with col2:
            date_from = st.date_input("Từ ngày", value=date.fromisoformat(plan["date_from"]))
            date_to = st.date_input("Đến ngày", value=date.fromisoformat(plan["date_to"]))

        col1, col2, col3 = st.columns(3)
        issue_keys = list(ISSUE_TYPES.keys())
        level_keys = list(AUDIT_LEVELS.keys())
        nature_keys = list(AUDIT_NATURES.keys())

        with col1:
            issue_type = st.selectbox("Phân loại vấn đề",
                                       issue_keys,
                                       index=issue_keys.index(plan["issue_type"]) if plan["issue_type"] in issue_keys else 0,
                                       format_func=lambda x: ISSUE_TYPES[x])
        with col2:
            audit_level = st.selectbox("Cấp độ",
                                        level_keys,
                                        index=level_keys.index(plan["audit_level"]) if plan["audit_level"] in level_keys else 0,
                                        format_func=lambda x: AUDIT_LEVELS[x])
        with col3:
            audit_nature = st.selectbox("Tính chất",
                                         nature_keys,
                                         index=nature_keys.index(plan["audit_nature"]) if plan["audit_nature"] in nature_keys else 0,
                                         format_func=lambda x: AUDIT_NATURES[x])

        status_options = ["planned", "in_progress", "completed"]
        status = st.selectbox("Trạng thái",
                               status_options,
                               index=status_options.index(plan.get("status", "planned")))
        notes = st.text_area("Ghi chú", value=plan.get("notes", ""))

        if st.form_submit_button("💾 Cập nhật", use_container_width=True):
            update_record("audit_plans", plan["id"], {
                "year": year, "sequence_no": sequence_no,
                "date_from": str(date_from), "date_to": str(date_to),
                "issue_type": issue_type, "audit_level": audit_level,
                "audit_nature": audit_nature, "status": status, "notes": notes
            })
            st.success("✅ Đã cập nhật!")
            st.rerun()

    st.markdown("---")
    st.subheader("📝 Quản lý Mục tiêu")
    render_objectives_editor(selected_id)
