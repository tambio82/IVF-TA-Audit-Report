"""
modules/module4_export.py - Xuất báo cáo
"""
import sys, os; _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, _root) if _root not in sys.path else None

import streamlit as st
import pandas as pd
from io import BytesIO
from utils.db import (
    get_db, get_plans, get_objectives_for_plan,
    get_kpis_for_objective, get_department_map
)
from modules.module1_planning import AUDIT_LEVELS, AUDIT_NATURES, ISSUE_TYPES


def render():
    st.title("📤 Module 4: Xuất Báo Cáo")

    plans = get_plans()
    if not plans:
        st.warning("Chưa có dữ liệu để xuất.")
        return

    tab1, tab2, tab3 = st.tabs([
        "📋 Xuất Kế hoạch",
        "📊 Xuất Kết quả Audit",
        "📦 Xuất Excel toàn bộ"
    ])

    with tab1:
        render_export_plan(plans)

    with tab2:
        render_export_results(plans)

    with tab3:
        render_export_all(plans)


# ── Helper ────────────────────────────────────────────────────────────────────

def select_plan(plans, key_prefix=""):
    col1, col2 = st.columns(2)
    years = sorted(set(p["year"] for p in plans), reverse=True)
    with col1:
        sel_year = st.selectbox("Năm", years, key=f"{key_prefix}_year")
    year_plans = [p for p in plans if p["year"] == sel_year]
    with col2:
        opts = {p["id"]: f"Đợt {p['sequence_no']} ({p['date_from']})" for p in year_plans}
        sel_id = st.selectbox("Đợt", list(opts.keys()), format_func=lambda x: opts[x],
                               key=f"{key_prefix}_plan")
    return next((p for p in plans if p["id"] == sel_id), None)


# ── Export Plan ───────────────────────────────────────────────────────────────

def render_export_plan(plans):
    st.subheader("📋 Xuất Kế hoạch Audit (trình Lãnh đạo)")
    plan = select_plan(plans, "ep")
    if not plan:
        return

    dept_map = get_department_map()
    objectives = get_objectives_for_plan(plan["id"])

    # Build HTML report
    html = build_plan_html(plan, objectives, dept_map)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "⬇️ Tải về HTML",
            data=html.encode("utf-8"),
            file_name=f"KH_Audit_{plan['year']}_Dot{plan['sequence_no']}.html",
            mime="text/html",
            use_container_width=True
        )
    with col2:
        # Excel plan
        excel_data = build_plan_excel(plan, objectives, dept_map)
        st.download_button(
            "⬇️ Tải về Excel",
            data=excel_data,
            file_name=f"KH_Audit_{plan['year']}_Dot{plan['sequence_no']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # Preview
    st.markdown("---")
    st.markdown("**Preview:**")
    st.markdown(html, unsafe_allow_html=True)


def build_plan_html(plan, objectives, dept_map):
    level = AUDIT_LEVELS.get(plan["audit_level"], plan["audit_level"])
    nature = AUDIT_NATURES.get(plan["audit_nature"], plan["audit_nature"])
    issue = ISSUE_TYPES.get(plan["issue_type"], plan["issue_type"])

    obj_rows = ""
    for obj in objectives:
        kpis = get_kpis_for_objective(obj["id"])
        dept_names = [dept_map.get(d, d) for d in (obj.get("department_ids") or [])]
        kpi_html = "".join(f"<tr><td>{k['kpi_text']}</td><td>{k.get('expected_outcome','')}</td></tr>"
                            for k in kpis)
        obj_rows += f"""
        <tr>
          <td>{obj['objective_no']}</td>
          <td>{obj['objective_text']}</td>
          <td>{', '.join(dept_names)}</td>
          <td>
            <table border='1' cellpadding='4' width='100%'>
              <tr><th>KPI</th><th>Outcome mong đợi</th></tr>
              {kpi_html}
            </table>
          </td>
        </tr>"""

    return f"""
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Kế hoạch Quality Audit</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
  h1 {{ color: #1a5276; text-align: center; }}
  h2 {{ color: #2874a6; border-bottom: 2px solid #2874a6; padding-bottom: 5px; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
  th {{ background: #2874a6; color: white; padding: 8px; }}
  td {{ padding: 8px; border: 1px solid #ddd; vertical-align: top; }}
  tr:nth-child(even) {{ background: #f5f7fa; }}
  .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
  .info-box {{ background: #eaf2ff; padding: 10px; border-radius: 6px; }}
  .label {{ color: #666; font-size: 12px; }}
  .value {{ font-weight: bold; font-size: 14px; }}
</style>
</head>
<body>
<h1>🏥 IVF Tâm Anh HN – Quality Audit System</h1>
<h2>KẾ HOẠCH QUALITY AUDIT – NĂM {plan['year']} – ĐỢT {plan['sequence_no']}</h2>

<div class='info-grid'>
  <div class='info-box'>
    <div class='label'>Thời gian</div>
    <div class='value'>{plan['date_from']} → {plan['date_to']}</div>
  </div>
  <div class='info-box'>
    <div class='label'>Phân loại vấn đề</div>
    <div class='value'>{issue}</div>
  </div>
  <div class='info-box'>
    <div class='label'>Cấp độ Audit</div>
    <div class='value'>{level}</div>
  </div>
  <div class='info-box'>
    <div class='label'>Tính chất</div>
    <div class='value'>{nature}</div>
  </div>
</div>

<h2>MỤC TIÊU AUDIT</h2>
<table border='1'>
  <tr>
    <th>#</th>
    <th>Mục tiêu</th>
    <th>Bộ phận</th>
    <th>KPIs & Outcomes</th>
  </tr>
  {obj_rows}
</table>

{"<p><b>Ghi chú:</b> " + plan['notes'] + "</p>" if plan.get('notes') else ""}

<p style='text-align:center; color:#999; font-size:12px; margin-top:40px;'>
  Tài liệu nội bộ - IVF Tâm Anh HN | Quality Audit System
</p>
</body>
</html>"""


def build_plan_excel(plan, objectives, dept_map):
    rows = []
    for obj in objectives:
        kpis = get_kpis_for_objective(obj["id"])
        dept_names = ", ".join([dept_map.get(d, d) for d in (obj.get("department_ids") or [])])
        if kpis:
            for kpi in kpis:
                rows.append({
                    "Năm": plan["year"],
                    "Đợt": plan["sequence_no"],
                    "Từ ngày": plan["date_from"],
                    "Đến ngày": plan["date_to"],
                    "Cấp độ": AUDIT_LEVELS.get(plan["audit_level"], ""),
                    "Tính chất": AUDIT_NATURES.get(plan["audit_nature"], ""),
                    "Loại": ISSUE_TYPES.get(plan["issue_type"], ""),
                    "STT Mục tiêu": obj["objective_no"],
                    "Mục tiêu": obj["objective_text"],
                    "Bộ phận": dept_names,
                    "KPI": kpi["kpi_text"],
                    "Outcome dự kiến": kpi.get("expected_outcome", "")
                })
        else:
            rows.append({
                "Năm": plan["year"],
                "Đợt": plan["sequence_no"],
                "Từ ngày": plan["date_from"],
                "Đến ngày": plan["date_to"],
                "Cấp độ": AUDIT_LEVELS.get(plan["audit_level"], ""),
                "Tính chất": AUDIT_NATURES.get(plan["audit_nature"], ""),
                "Loại": ISSUE_TYPES.get(plan["issue_type"], ""),
                "STT Mục tiêu": obj["objective_no"],
                "Mục tiêu": obj["objective_text"],
                "Bộ phận": dept_names,
                "KPI": "", "Outcome dự kiến": ""
            })

    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Kế hoạch Audit", index=False)
    return buf.getvalue()


# ── Export Results ────────────────────────────────────────────────────────────

def render_export_results(plans):
    st.subheader("📊 Xuất Báo cáo Kết quả Audit")
    plan = select_plan(plans, "er")
    if not plan:
        return

    db = get_db()
    findings = db.table("v_findings_with_context").select("*").eq("plan_id", plan["id"]).execute().data or []

    if not findings:
        st.info("Chưa có dữ liệu kết quả cho đợt này.")
        return

    html = build_results_html(plan, findings)
    excel_data = build_results_excel(plan, findings)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "⬇️ Tải báo cáo HTML",
            data=html.encode("utf-8"),
            file_name=f"KQ_Audit_{plan['year']}_Dot{plan['sequence_no']}.html",
            mime="text/html",
            use_container_width=True
        )
    with col2:
        st.download_button(
            "⬇️ Tải báo cáo Excel",
            data=excel_data,
            file_name=f"KQ_Audit_{plan['year']}_Dot{plan['sequence_no']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    st.markdown("---")
    df = pd.DataFrame(findings)
    st.dataframe(df, use_container_width=True)


def build_results_html(plan, findings):
    rows_html = ""
    for f in findings:
        rpn = f.get("rpn_score", "—")
        q = f.get("quantitative_score", "—")
        follow_map = {
            "no_action": "Không hành động thêm",
            "improvement_project": "Đề án Cải tiến CL",
            "additional_monitoring": "Giám sát Audit thêm"
        }
        rows_html += f"""
        <tr>
          <td>{f.get('objective_no','')}</td>
          <td>{f.get('objective_text','')}</td>
          <td>{f.get('finding_name','')}</td>
          <td>{q}/5</td>
          <td>S={f.get('severity_score','?')} O={f.get('occurrence_score','?')} D={f.get('detection_score','?')}<br><b>RPN={rpn}</b></td>
          <td>{f.get('corrective_action','')}</td>
          <td>{follow_map.get(f.get('follow_up_option',''), '')}</td>
        </tr>"""

    return f"""
<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8">
<title>Báo cáo Kết quả Audit</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 40px; }}
  h1 {{ color: #1a5276; text-align: center; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  th {{ background: #2874a6; color: white; padding: 8px; }}
  td {{ padding: 7px; border: 1px solid #ddd; vertical-align: top; }}
  tr:nth-child(even) {{ background: #f8f9fa; }}
</style></head><body>
<h1>BÁO CÁO KẾT QUẢ QUALITY AUDIT</h1>
<h2>Năm {plan['year']} – Đợt {plan['sequence_no']} | {plan['date_from']} → {plan['date_to']}</h2>
<table><tr>
  <th>#MT</th><th>Mục tiêu</th><th>Vấn đề phát hiện</th>
  <th>Điểm ĐL</th><th>FMEA (RPN)</th><th>Giải pháp</th><th>Gợi ý</th>
</tr>{rows_html}</table>
<p style='color:#999;text-align:center;font-size:12px;margin-top:30px;'>
  IVF Tâm Anh HN – Quality Audit System</p>
</body></html>"""


def build_results_excel(plan, findings):
    if not findings:
        return BytesIO().getvalue()
    df = pd.DataFrame(findings)
    keep = ["year", "sequence_no", "date_from", "date_to", "objective_no", "objective_text",
            "kpi_text", "finding_name", "impact_consequence", "qualitative_assessment",
            "evidence_link", "quantitative_score", "quantitative_classification",
            "severity_score", "occurrence_score", "detection_score", "rpn_score",
            "process_indicator_score", "corrective_action", "follow_up_option"]
    avail = [c for c in keep if c in df.columns]
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df[avail].to_excel(writer, sheet_name="Kết quả Audit", index=False)
    return buf.getvalue()


# ── Export All ────────────────────────────────────────────────────────────────

def render_export_all(plans):
    st.subheader("📦 Xuất toàn bộ dữ liệu ra Excel")

    db = get_db()
    dept_map = get_department_map()

    if st.button("🔄 Tạo file Excel tổng hợp", use_container_width=True):
        with st.spinner("Đang tổng hợp dữ liệu..."):
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                # Sheet 1: Plans
                plan_rows = []
                for p in plans:
                    plan_rows.append({
                        "ID": p["id"],
                        "Năm": p["year"],
                        "Đợt": p["sequence_no"],
                        "Từ ngày": p["date_from"],
                        "Đến ngày": p["date_to"],
                        "Loại": ISSUE_TYPES.get(p["issue_type"], ""),
                        "Cấp độ": AUDIT_LEVELS.get(p["audit_level"], ""),
                        "Tính chất": AUDIT_NATURES.get(p["audit_nature"], ""),
                        "Trạng thái": p.get("status", ""),
                        "Ghi chú": p.get("notes", "")
                    })
                pd.DataFrame(plan_rows).to_excel(writer, sheet_name="Kế hoạch", index=False)

                # Sheet 2: Objectives + KPIs
                obj_rows = []
                for p in plans:
                    for obj in get_objectives_for_plan(p["id"]):
                        dept_names = ", ".join([dept_map.get(d, d) for d in (obj.get("department_ids") or [])])
                        for kpi in get_kpis_for_objective(obj["id"]) or [{}]:
                            obj_rows.append({
                                "Năm": p["year"],
                                "Đợt": p["sequence_no"],
                                "STT MT": obj["objective_no"],
                                "Mục tiêu": obj["objective_text"],
                                "Bộ phận": dept_names,
                                "KPI": kpi.get("kpi_text", ""),
                                "Outcome dự kiến": kpi.get("expected_outcome", "")
                            })
                pd.DataFrame(obj_rows).to_excel(writer, sheet_name="Mục tiêu & KPI", index=False)

                # Sheet 3: All findings
                all_findings = db.table("v_findings_with_context").select("*").execute().data or []
                if all_findings:
                    pd.DataFrame(all_findings).to_excel(writer, sheet_name="Kết quả Audit", index=False)

            st.download_button(
                "⬇️ Tải về file Excel tổng hợp",
                data=buf.getvalue(),
                file_name="IVF_TamAnh_QualityAudit_Data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
