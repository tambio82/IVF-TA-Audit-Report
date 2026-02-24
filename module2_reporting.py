"""
modules/module2_reporting.py - Báo cáo kết quả công việc Audit
"""
import streamlit as st
from utils.db import (
    get_db, insert_record, update_record, delete_record, fetch_view,
    get_plans, get_objectives_for_plan, get_kpis_for_objective, get_department_map
)
from utils.auth import current_user

FOLLOW_UP_OPTIONS = {
    "no_action": "✅ Không hành động gì thêm",
    "improvement_project": "💡 Vấn đề là ý tưởng cho đề án Cải tiến chất lượng",
    "additional_monitoring": "🔍 Cần Giám sát Audit thêm cho đợt sau"
}

SCORE_OPTIONS = [round(x * 0.5, 1) for x in range(0, 11)]  # 0, 0.5, 1.0, ... 5.0


def classify_score(score):
    if score is None:
        return "—"
    if score < 3:
        return "🔴 Dưới kỳ vọng"
    elif score <= 4:
        return "🟡 Tạm chấp nhận"
    else:
        return "🟢 Kết quả ổn"


def render():
    st.title("📝 Module 2: Báo cáo Kết quả Audit")

    # ── Part 1: Select Plan ───────────────────────────────────────────────────
    st.markdown("### 📌 Phần 1: Chọn đợt Audit")

    plans = get_plans()
    if not plans:
        st.warning("Chưa có đợt Audit nào. Vui lòng tạo kế hoạch ở Module 1.")
        return

    col1, col2 = st.columns(2)
    with col1:
        years = sorted(set(p["year"] for p in plans), reverse=True)
        sel_year = st.selectbox("Năm", years, key="m2_year")

    year_plans = [p for p in plans if p["year"] == sel_year]
    with col2:
        plan_opts = {p["id"]: f"Đợt {p['sequence_no']} ({p['date_from']} → {p['date_to']})" for p in year_plans}
        if not plan_opts:
            st.info("Không có đợt nào trong năm này.")
            return
        sel_plan_id = st.selectbox("Đợt", options=list(plan_opts.keys()),
                                    format_func=lambda x: plan_opts[x], key="m2_plan")

    sel_plan = next((p for p in plans if p["id"] == sel_plan_id), None)
    if not sel_plan:
        return

    # Show plan summary
    from modules.module1_planning import AUDIT_LEVELS, AUDIT_NATURES, ISSUE_TYPES
    with st.container():
        col1, col2, col3 = st.columns(3)
        col1.info(f"**Cấp độ:** {AUDIT_LEVELS.get(sel_plan['audit_level'], '')}")
        col2.info(f"**Tính chất:** {AUDIT_NATURES.get(sel_plan['audit_nature'], '')}")
        col3.info(f"**Loại:** {ISSUE_TYPES.get(sel_plan['issue_type'], '')}")

    # ── Part 2: Objectives and Findings ───────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 Phần 2: Ghi nhận Kết quả")

    objectives = get_objectives_for_plan(sel_plan_id)
    if not objectives:
        st.warning("Chưa có mục tiêu nào cho đợt này. Vui lòng thêm mục tiêu ở Module 1.")
        return

    dept_map = get_department_map()

    for obj in objectives:
        dept_names = [dept_map.get(d, d) for d in (obj.get("department_ids") or [])]
        kpis = get_kpis_for_objective(obj["id"])

        with st.expander(
            f"🎯 Mục tiêu {obj['objective_no']}: {obj['objective_text'][:80]}...",
            expanded=True
        ):
            if dept_names:
                st.caption(f"🏢 Bộ phận: {', '.join(dept_names)}")

            for kpi in kpis:
                st.markdown(f"**📌 KPI:** {kpi['kpi_text']}")
                if kpi.get("expected_outcome"):
                    st.caption(f"🎯 Outcome dự kiến: {kpi['expected_outcome']}")

                # Show existing findings for this KPI
                db = get_db()
                existing_findings = db.table("audit_findings").select("*")\
                    .eq("plan_id", sel_plan_id)\
                    .eq("kpi_id", kpi["id"])\
                    .execute().data or []

                for finding in existing_findings:
                    render_finding_card(finding, plans)
                    st.markdown("---")

                # Add new finding
                render_add_finding_form(sel_plan_id, obj["id"], kpi["id"], plans)

            # Also allow findings directly on objective (no KPI)
            st.markdown("**➕ Thêm phát hiện không thuộc KPI cụ thể:**")
            no_kpi_findings = db.table("audit_findings").select("*")\
                .eq("plan_id", sel_plan_id)\
                .eq("objective_id", obj["id"])\
                .is_("kpi_id", "null")\
                .execute().data or []

            for finding in no_kpi_findings:
                render_finding_card(finding, plans)
                st.markdown("---")

            render_add_finding_form(sel_plan_id, obj["id"], None, plans, suffix="nokpi")


def render_finding_card(finding: dict, all_plans: list):
    """Display an existing finding with edit/delete options."""
    score = finding.get("quantitative_score")
    rpn = finding.get("rpn_score")

    with st.container():
        st.markdown(f"**🔍 Vấn đề:** {finding.get('finding_name', '')}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Điểm định lượng", f"{score}/5" if score is not None else "—")
        col1.caption(classify_score(score))
        if rpn:
            col2.metric("RPN (FMEA)", rpn)
            s, o, d = finding.get("severity_score"), finding.get("occurrence_score"), finding.get("detection_score")
            col2.caption(f"S={s} × O={o} × D={d}")
        col3.metric("Process Indicator", finding.get("process_indicator_score", "—"))

        follow_up = finding.get("follow_up_option", "no_action")
        st.caption(f"💬 {FOLLOW_UP_OPTIONS.get(follow_up, follow_up)}")

        col_edit, col_del = st.columns([5, 1])
        with col_del:
            if st.button("🗑️", key=f"del_finding_{finding['id']}", help="Xóa"):
                delete_record("audit_findings", finding["id"])
                st.rerun()
        with col_edit:
            with st.expander("✏️ Chỉnh sửa"):
                render_finding_form(finding, all_plans, edit_mode=True)


def render_add_finding_form(plan_id, objective_id, kpi_id, all_plans, suffix=""):
    form_key = f"form_add_finding_{plan_id}_{objective_id}_{kpi_id}_{suffix}"
    with st.expander("➕ Thêm vấn đề phát hiện mới"):
        render_finding_form(None, all_plans, edit_mode=False,
                            plan_id=plan_id, objective_id=objective_id,
                            kpi_id=kpi_id, form_key=form_key)


def render_finding_form(finding: dict | None, all_plans: list, edit_mode: bool,
                         plan_id=None, objective_id=None, kpi_id=None, form_key=None):
    """Shared form for add/edit finding."""
    fid = finding["id"] if finding else None
    fk = form_key or f"form_finding_{fid}"

    with st.form(fk):
        finding_name = st.text_area("🔍 Tên vấn đề phát hiện *",
                                     value=finding.get("finding_name", "") if finding else "")
        impact = st.text_area("⚠️ Ảnh hưởng / Hậu quả có thể gây nên",
                               value=finding.get("impact_consequence", "") if finding else "")
        qualitative = st.text_area("📊 Đánh giá kết quả định tính (kết quả, hiệu suất, cấu trúc)",
                                    value=finding.get("qualitative_assessment", "") if finding else "")
        evidence = st.text_input("🔗 Minh chứng (link Google Drive)",
                                  value=finding.get("evidence_link", "") if finding else "")

        st.markdown("---")
        st.markdown("**📏 Đánh giá định lượng**")
        col1, col2 = st.columns(2)
        with col1:
            q_score = st.select_slider(
                "Điểm định lượng (0-5, mỗi mức 0.5)",
                options=SCORE_OPTIONS,
                value=finding.get("quantitative_score", 2.5) if finding else 2.5
            )
        with col2:
            q_class = classify_score(q_score)
            st.metric("Phân loại", q_class)

        st.markdown("---")
        st.markdown("**🧮 Đánh giá FMEA**")
        col1, col2, col3 = st.columns(3)
        with col1:
            severity = st.slider("S - Mức độ nghiêm trọng",
                                  1, 10, value=finding.get("severity_score", 5) if finding else 5,
                                  help="1=Không đáng kể, 10=Nghiêm trọng nhất")
        with col2:
            occurrence = st.slider("O - Tần suất xảy ra",
                                    1, 10, value=finding.get("occurrence_score", 5) if finding else 5,
                                    help="1=Rất hiếm, 10=Rất thường xuyên")
        with col3:
            detection = st.slider("D - Khả năng phát hiện",
                                   1, 10, value=finding.get("detection_score", 5) if finding else 5,
                                   help="1=Phát hiện dễ dàng, 10=Rất khó phát hiện")

        rpn = severity * occurrence * detection
        st.metric("🔢 RPN = S × O × D", rpn,
                  delta=f"Rủi ro {'Cao' if rpn > 200 else 'Trung bình' if rpn > 100 else 'Thấp'}")

        # Previous FMEA reference
        st.markdown("---")
        st.markdown("**📅 So sánh FMEA đợt trước**")
        prev_plans = [p for p in all_plans if not finding or p["id"] != (finding.get("plan_id", ""))]
        prev_plan_opts = {None: "— Không chọn —"}
        prev_plan_opts.update({p["id"]: f"{p['year']} - Đợt {p['sequence_no']}" for p in prev_plans})

        prev_plan_id = st.selectbox("Chọn đợt trước để so sánh",
                                     options=list(prev_plan_opts.keys()),
                                     format_func=lambda x: prev_plan_opts.get(x, ""),
                                     key=f"prev_plan_{fk}")
        prev_finding_id = None
        if prev_plan_id:
            db = get_db()
            prev_findings = db.table("audit_findings").select("id, finding_name, rpn_score")\
                .eq("plan_id", prev_plan_id).execute().data or []
            if prev_findings:
                pf_opts = {None: "— Không chọn —"}
                pf_opts.update({f["id"]: f"{f['finding_name']} (RPN={f.get('rpn_score','?')})"
                                for f in prev_findings})
                prev_finding_id = st.selectbox("Chọn vấn đề tương ứng",
                                                options=list(pf_opts.keys()),
                                                format_func=lambda x: pf_opts.get(x, ""),
                                                key=f"prev_finding_{fk}")

        st.markdown("---")
        process_ind = st.slider("📋 Process Indicator (tuân thủ quy trình)",
                                 1, 10, value=finding.get("process_indicator_score", 5) if finding else 5)

        corrective = st.text_area("💡 Đề xuất giải pháp khắc phục",
                                   value=finding.get("corrective_action", "") if finding else "")

        follow_up = st.radio(
            "📌 Gợi ý thêm",
            options=list(FOLLOW_UP_OPTIONS.keys()),
            format_func=lambda x: FOLLOW_UP_OPTIONS[x],
            index=list(FOLLOW_UP_OPTIONS.keys()).index(
                finding.get("follow_up_option", "no_action")) if finding else 0,
            horizontal=False
        )

        submitted = st.form_submit_button("💾 Lưu" if not edit_mode else "💾 Cập nhật")

        if submitted:
            if not finding_name.strip():
                st.error("Tên vấn đề không được để trống!")
                return

            user = current_user()
            data = {
                "finding_name": finding_name.strip(),
                "impact_consequence": impact.strip(),
                "qualitative_assessment": qualitative.strip(),
                "evidence_link": evidence.strip(),
                "quantitative_score": q_score,
                "severity_score": severity,
                "occurrence_score": occurrence,
                "detection_score": detection,
                "process_indicator_score": process_ind,
                "corrective_action": corrective.strip(),
                "follow_up_option": follow_up,
                "previous_finding_id": prev_finding_id,
                "auditor_id": user["id"] if user else None
            }

            if edit_mode and fid:
                update_record("audit_findings", fid, data)
                st.success("✅ Đã cập nhật!")
            else:
                data.update({
                    "plan_id": plan_id,
                    "objective_id": objective_id,
                    "kpi_id": kpi_id
                })
                insert_record("audit_findings", data)
                st.success("✅ Đã lưu vấn đề mới!")
            st.rerun()
