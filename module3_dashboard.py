"""
modules/module3_dashboard.py - Dashboard và biểu đồ thống kê
Phiên bản nâng cấp với FMEA Radar chi tiết
"""
import sys, os; _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, _root) if _root not in sys.path else None

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.db import get_db, get_plans, get_department_map

FOLLOW_UP_LABELS = {
    "no_action": "Không hành động thêm",
    "improvement_project": "Đề án Cải tiến CL",
    "additional_monitoring": "Giám sát Audit thêm"
}

RPN_HIGH   = 200
RPN_MED    = 100
SCORE_HIGH = 8

COLORS = {
    "critical": "#c0392b",
    "high":     "#e67e22",
    "medium":   "#f1c40f",
    "low":      "#27ae60",
    "info":     "#2980b9",
    "navy":     "#1a3a6e",
}

PERIOD_COLORS = px.colors.qualitative.Plotly


# =============================================================================
# MAIN RENDER
# =============================================================================

def render():
    st.title("📊 Module 3: Dashboard Theo dõi Kết quả Audit")

    plans = get_plans()
    if not plans:
        st.info("Chưa có dữ liệu. Vui lòng tạo kế hoạch và nhập kết quả trước.")
        return

    with st.sidebar:
        st.markdown("### 🔧 Bộ lọc Dashboard")
        years = sorted(set(p["year"] for p in plans), reverse=True)
        sel_years = st.multiselect("Năm", years, default=years[:2] if len(years) >= 2 else years)
        time_group = st.selectbox("Nhóm theo", ["Đợt", "Quý", "6 tháng", "Năm"])
        st.markdown("---")
        st.markdown("### 🎯 Chế độ FMEA Radar")
        radar_mode = st.selectbox(
            "Chọn chế độ",
            ["Tổng quan đợt", "So sánh đa đợt", "Theo mục tiêu",
             "Theo bộ phận", "Phân tích từng vấn đề", "Ma trận rủi ro"]
        )

    db = get_db()
    all_raw = db.table("v_findings_with_context").select("*").execute().data or []
    if not all_raw:
        st.info("Chưa có dữ liệu kết quả. Vui lòng nhập kết quả ở Module 2.")
        return

    df = _build_df(all_raw)
    if sel_years:
        df = df[df["year"].isin(sel_years)]
    if df.empty:
        st.warning("Không có dữ liệu cho bộ lọc đã chọn.")
        return

    _render_kpi_cards(df)
    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Điểm theo thời gian",
        "🥧 Phân loại kết quả",
        "🕸️ FMEA Radar",
        "🔢 So sánh FMEA",
        "💬 Gợi ý thêm"
    ])
    with tab1: _render_timeseries(df, time_group)
    with tab2: _render_classification(df, time_group)
    with tab3: _render_fmea_radar_hub(df, radar_mode)
    with tab4: _render_fmea_comparison(df)
    with tab5: _render_followup(df)


# =============================================================================
# DATA HELPERS
# =============================================================================

def _build_df(raw):
    df = pd.DataFrame(raw)
    df["date_from"] = pd.to_datetime(df["date_from"])
    df["period_label"] = df.apply(lambda r: f"{r['year']}-Đợt{int(r['sequence_no'])}", axis=1)
    df["period_order"] = df["year"].astype(str) + df["sequence_no"].astype(str).str.zfill(2)
    df["quarter"]      = "Q" + df["date_from"].dt.quarter.astype(str)
    df["year_quarter"] = df["year"].astype(str) + "-" + df["quarter"]
    df["year_half"]    = df.apply(lambda r: f"{r['year']}-H{'1' if r['sequence_no'] <= 6 else '2'}", axis=1)
    df["q_class"]      = df["quantitative_score"].apply(_classify)
    df["risk_level"]   = df["rpn_score"].apply(_risk)
    return df


def _classify(s):
    if pd.isna(s): return "Chưa đánh giá"
    if s < 3:      return "Dưới kỳ vọng"
    if s <= 4:     return "Tạm chấp nhận"
    return "Kết quả ổn"


def _risk(r):
    if pd.isna(r): return "Chưa đánh giá"
    if r >= RPN_HIGH: return "🔴 Nghiêm trọng"
    if r >= RPN_MED:  return "🟠 Cao"
    if r >= 50:       return "🟡 Trung bình"
    return "🟢 Thấp"


def _group_col(tg):
    return {"Đợt": "period_label", "Quý": "year_quarter",
            "6 tháng": "year_half", "Năm": "year"}.get(tg, "period_label")


def _hex_rgba(hex_c, a):
    h = hex_c.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"


# =============================================================================
# KPI CARDS
# =============================================================================

def _render_kpi_cards(df):
    fdf = df.dropna(subset=["rpn_score"])
    c = st.columns(5)
    c[0].metric("📋 Tổng vấn đề", len(df))
    c[1].metric("📊 Điểm ĐL TB",
                f"{df['quantitative_score'].mean():.2f}" if df['quantitative_score'].notna().any() else "—")
    c[2].metric("🔢 RPN TB",
                f"{fdf['rpn_score'].mean():.0f}" if not fdf.empty else "—")
    c[3].metric("🔴 RPN Nghiêm trọng",
                int((fdf["rpn_score"] >= RPN_HIGH).sum()) if not fdf.empty else 0)
    c[4].metric("🔴 Dưới kỳ vọng", int((df["quantitative_score"] < 3).sum()))


# =============================================================================
# TAB 3 – FMEA RADAR HUB
# =============================================================================

THETA5 = ["S – Nghiêm trọng", "O – Tần suất", "D – Khó phát hiện",
          "PI – Tuân thủ QT", "Q – Điểm ĐL"]

def _render_fmea_radar_hub(df, radar_mode):
    fdf = df.dropna(subset=["severity_score", "occurrence_score", "detection_score"])
    if fdf.empty:
        st.info("Chưa có đủ dữ liệu FMEA (S, O, D). Vui lòng nhập ở Module 2.")
        return

    with st.expander("ℹ️ Hướng dẫn đọc biểu đồ FMEA Radar", expanded=False):
        st.markdown("""
| Trục | Ký hiệu | Ý nghĩa | Điểm cảnh báo |
|------|---------|---------|--------------|
| **S** | Severity – Nghiêm trọng | Mức độ ảnh hưởng nếu lỗi xảy ra | ≥ 8 |
| **O** | Occurrence – Tần suất | Khả năng nguyên nhân lỗi xuất hiện | ≥ 8 |
| **D** | Detection – Khó phát hiện | Độ khó phát hiện lỗi (cao = nguy hiểm) | ≥ 8 |
| **PI** | Process Indicator | Mức tuân thủ quy trình (cao = tốt) | < 5 |
| **Q** | Điểm Định lượng | Điểm đánh giá tổng thể (quy đổi 0-10) | < 6 |

> **RPN = S × O × D** &nbsp;|&nbsp; 🟢 <50 &nbsp;·&nbsp; 🟡 50–99 &nbsp;·&nbsp; 🟠 100–199 &nbsp;·&nbsp; 🔴 ≥200
        """)

    st.markdown("---")

    dispatch = {
        "Tổng quan đợt":        _radar_overview,
        "So sánh đa đợt":       _radar_multi,
        "Theo mục tiêu":        _radar_by_obj,
        "Theo bộ phận":         _radar_by_dept,
        "Phân tích từng vấn đề": _radar_per_finding,
        "Ma trận rủi ro":       _risk_matrix,
    }
    dispatch.get(radar_mode, _radar_overview)(fdf)


# ------- helpers shared by all radar modes -----------------------------------

def _avg_vals(sub):
    s  = sub["severity_score"].mean()
    o  = sub["occurrence_score"].mean()
    d  = sub["detection_score"].mean()
    pi = sub["process_indicator_score"].mean() if "process_indicator_score" in sub.columns else 5
    q  = (sub["quantitative_score"].mean() / 5 * 10) if sub["quantitative_score"].notna().any() else 5
    return [s, o, d,
            pi if not pd.isna(pi) else 5,
            q  if not pd.isna(q)  else 5]


def _add_zones(fig, n=5):
    """Transparent concentric zone rings: green/yellow/orange/red."""
    rings = [(10, "rgba(192,57,43,0.06)"),
             (8,  "rgba(230,126,34,0.06)"),
             (6,  "rgba(241,196,15,0.06)"),
             (4,  "rgba(39,174,96,0.06)")]
    for r_max, color in rings:
        fig.add_trace(go.Scatterpolar(
            r=[r_max] * (n + 1), theta=list(range(n)) + [0],
            fill="toself", fillcolor=color,
            line=dict(color="rgba(0,0,0,0)", width=0),
            showlegend=False, hoverinfo="skip", mode="lines"
        ))


def _polar_layout(title, h=500):
    return dict(
        polar=dict(radialaxis=dict(
            visible=True, range=[0, 10],
            tickvals=[2, 4, 6, 8, 10],
            gridcolor="#e0e0e0", linecolor="#ccc"
        ), angularaxis=dict(gridcolor="#e0e0e0")),
        title=dict(text=title, font=dict(size=14)),
        height=h,
        margin=dict(t=70, b=50, l=60, r=60)
    )


def _single_radar_trace(vals, label, color, theta=None):
    theta = theta or THETA5
    vc = vals + [vals[0]]
    tc = theta + [theta[0]]
    return go.Scatterpolar(
        r=vc, theta=tc, fill="toself",
        fillcolor=_hex_rgba(color, 0.15),
        line=dict(color=color, width=2.5),
        mode="lines+markers",
        marker=dict(size=7, color=color),
        name=label,
        hovertemplate="%{theta}: <b>%{r:.1f}</b><extra></extra>"
    )


def _badge(val, invert=False):
    if pd.isna(val): return "—"
    icon = ("🟢" if val >= 7 else "🟡" if val >= 5 else "🔴") if invert \
           else ("🔴" if val >= SCORE_HIGH else "🟡" if val >= 6 else "🟢")
    return f"{icon} **{val:.1f}** / 10"


def _sorted_periods(df):
    return sorted(df["period_label"].unique(),
                  key=lambda x: df[df["period_label"] == x]["period_order"].iloc[0])


# ── Mode 1: Tổng quan đợt ────────────────────────────────────────────────────

def _radar_overview(df):
    st.subheader("🕸️ Tổng quan FMEA – Một đợt")

    periods = _sorted_periods(df)
    sel = st.selectbox("Chọn đợt", periods, key="ov_period")
    sub = df[df["period_label"] == sel]

    vals = _avg_vals(sub)
    rpn_avg = sub["rpn_score"].mean()
    color = COLORS["critical"] if rpn_avg >= RPN_HIGH else \
            COLORS["high"] if rpn_avg >= RPN_MED else COLORS["low"]

    col_r, col_i = st.columns([3, 2])

    with col_r:
        fig = go.Figure()
        _add_zones(fig)
        fig.add_trace(_single_radar_trace(vals, sel, color))
        fig.update_layout(**_polar_layout(f"FMEA Radar – {sel}"))
        st.plotly_chart(fig, use_container_width=True)

    with col_i:
        st.markdown(f"#### 📊 Chỉ số – {sel}")
        st.markdown("---")
        s, o, d, pi, q = vals
        st.write(f"**S – Nghiêm trọng:** {_badge(s)}")
        st.caption("Mức độ ảnh hưởng nếu lỗi xảy ra")
        st.write(f"**O – Tần suất:** {_badge(o)}")
        st.caption("Khả năng lỗi xuất hiện")
        st.write(f"**D – Khó phát hiện:** {_badge(d)}")
        st.caption("Độ khó phát hiện lỗi (cao = nguy hiểm)")
        st.write(f"**PI – Tuân thủ QT:** {_badge(pi, invert=True)}")
        st.caption("Mức tuân thủ quy trình")
        st.markdown("---")
        rpn_icon = "🔴" if rpn_avg >= RPN_HIGH else "🟠" if rpn_avg >= RPN_MED else "🟡" if rpn_avg >= 50 else "🟢"
        st.metric(f"{rpn_icon} RPN Trung bình", f"{rpn_avg:.0f}")
        st.metric("📋 Số vấn đề", len(sub))

        worst = sub.loc[sub["rpn_score"].idxmax()] if sub["rpn_score"].notna().any() else None
        if worst is not None:
            st.markdown("---")
            st.warning(f"⚠️ **RPN cao nhất:**\n\n{worst.get('finding_name','')}\n\nRPN = **{worst['rpn_score']:.0f}**")

    # Breakdown bar
    st.markdown("---")
    st.subheader("Phân bố S / O / D cho từng vấn đề")
    sub_s = sub.sort_values("rpn_score", ascending=False).copy()
    sub_s["lbl"] = sub_s["finding_name"].str[:35] + "…"
    fig2 = go.Figure()
    for col_name, c, lbl in [
        ("severity_score",   COLORS["critical"], "S"),
        ("occurrence_score", COLORS["high"],     "O"),
        ("detection_score",  COLORS["info"],     "D")
    ]:
        fig2.add_trace(go.Bar(name=f"{lbl} – {col_name.split('_')[0].capitalize()}",
                              x=sub_s["lbl"], y=sub_s[col_name],
                              marker_color=c, text=sub_s[col_name].round(0), textposition="outside"))
    fig2.add_hline(y=SCORE_HIGH, line_dash="dash", line_color="red",
                   annotation_text=f"Ngưỡng cảnh báo ({SCORE_HIGH})")
    fig2.update_layout(barmode="group", height=400, yaxis_range=[0, 11],
                        xaxis_title="Vấn đề", yaxis_title="Điểm (1-10)")
    st.plotly_chart(fig2, use_container_width=True)


# ── Mode 2: So sánh đa đợt ───────────────────────────────────────────────────

def _radar_multi(df):
    st.subheader("🕸️ So sánh FMEA qua nhiều đợt (Radar chồng)")

    periods = _sorted_periods(df)
    if len(periods) < 2:
        st.info("Cần ít nhất 2 đợt để so sánh.")

    sel = st.multiselect("Chọn đợt so sánh (tối đa 6)",
                          periods, default=periods[-4:] if len(periods) > 4 else periods)
    if not sel: return
    sel = sel[:6]

    fig = go.Figure()
    _add_zones(fig)

    trend_rows = []
    for i, period in enumerate(sel):
        sub = df[df["period_label"] == period]
        vals = _avg_vals(sub)
        color = PERIOD_COLORS[i % len(PERIOD_COLORS)]
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=THETA5 + [THETA5[0]],
            fill="toself",
            line=dict(color=color, width=2.5),
            name=period,
            hovertemplate=f"<b>{period}</b><br>%{{theta}}: %{{r:.1f}}"
                          f"<br>RPN TB: {sub['rpn_score'].mean():.0f}<extra></extra>"
        ))
        s, o, d, pi, _ = vals
        trend_rows.append({"Đợt": period,
                            "S – Nghiêm trọng": s, "O – Tần suất": o,
                            "D – Khó phát hiện": d, "PI – Tuân thủ QT": pi,
                            "RPN TB": sub["rpn_score"].mean()})

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 10],
                                   tickvals=[2, 4, 6, 8, 10], gridcolor="#e0e0e0")),
        showlegend=True,
        title="So sánh FMEA – Radar chồng các đợt",
        height=560,
        legend=dict(orientation="h", yanchor="bottom", y=-0.28)
    )
    st.plotly_chart(fig, use_container_width=True)

    # Trend lines
    st.markdown("---")
    st.subheader("📈 Xu hướng S / O / D / PI qua thời gian")
    df_trend = pd.DataFrame(trend_rows)
    df_melt = df_trend.melt(id_vars=["Đợt"],
                             value_vars=["S – Nghiêm trọng", "O – Tần suất",
                                         "D – Khó phát hiện", "PI – Tuân thủ QT"],
                             var_name="Chỉ số", value_name="Điểm TB")
    c_map = {"S – Nghiêm trọng": COLORS["critical"],
             "O – Tần suất":     COLORS["high"],
             "D – Khó phát hiện":COLORS["info"],
             "PI – Tuân thủ QT": COLORS["low"]}
    fig_t = px.line(df_melt, x="Đợt", y="Điểm TB", color="Chỉ số",
                    markers=True, color_discrete_map=c_map,
                    title="Xu hướng S / O / D / PI", height=370)
    fig_t.add_hline(y=SCORE_HIGH, line_dash="dot", line_color="red",
                    annotation_text=f"Cảnh báo ({SCORE_HIGH})")
    fig_t.update_layout(yaxis_range=[0, 11])
    st.plotly_chart(fig_t, use_container_width=True)

    fig_rpn = px.area(df_trend, x="Đợt", y="RPN TB",
                      title="Xu hướng RPN Trung bình",
                      color_discrete_sequence=[COLORS["critical"]], height=320)
    fig_rpn.add_hline(y=RPN_HIGH, line_dash="dash", line_color="red",
                      annotation_text=f"Nghiêm trọng ({RPN_HIGH})")
    fig_rpn.add_hline(y=RPN_MED, line_dash="dot", line_color="orange",
                      annotation_text=f"Cao ({RPN_MED})")
    st.plotly_chart(fig_rpn, use_container_width=True)

    # Period-over-period delta table
    if len(df_trend) >= 2:
        st.markdown("---")
        st.subheader("📉 Thay đổi S / O / D so với đợt trước")
        df_delta = df_trend.copy()
        for col_n in ["S – Nghiêm trọng", "O – Tần suất", "D – Khó phát hiện", "RPN TB"]:
            df_delta[f"Δ {col_n}"] = df_delta[col_n].diff().round(2)
        st.dataframe(df_delta.fillna("—"), use_container_width=True, hide_index=True)


# ── Mode 3: Theo mục tiêu ─────────────────────────────────────────────────────

def _radar_by_obj(df):
    st.subheader("🕸️ FMEA Radar – Theo Mục tiêu")

    periods = _sorted_periods(df)
    sel_period = st.selectbox("Chọn đợt", periods, key="obj_period")
    sub = df[df["period_label"] == sel_period]
    objs = sub["objective_text"].dropna().unique()

    if len(objs) == 0:
        st.info("Không có mục tiêu trong đợt này.")
        return

    n = len(objs)
    cols_per_row = 2
    rows_n = (n + cols_per_row - 1) // cols_per_row

    fig = make_subplots(
        rows=rows_n, cols=cols_per_row,
        specs=[[{"type": "polar"}] * cols_per_row for _ in range(rows_n)],
        subplot_titles=[o[:55] + ("…" if len(o) > 55 else "") for o in objs]
    )

    summary = []
    for idx, obj in enumerate(objs):
        row_idx = idx // cols_per_row + 1
        col_idx = idx % cols_per_row + 1
        s_obj = sub[sub["objective_text"] == obj]
        vals = _avg_vals(s_obj)
        rpn_avg = s_obj["rpn_score"].mean()
        risk_color = COLORS["critical"] if rpn_avg >= RPN_HIGH else \
                     COLORS["high"] if rpn_avg >= RPN_MED else COLORS["low"]

        fig.add_trace(
            go.Scatterpolar(
                r=vals + [vals[0]], theta=THETA5 + [THETA5[0]],
                fill="toself",
                fillcolor=_hex_rgba(risk_color, 0.15),
                line=dict(color=risk_color, width=2),
                name=obj[:30],
                hovertemplate=f"<b>{obj[:40]}</b><br>%{{theta}}: %{{r:.1f}}"
                              f"<br>RPN TB: {rpn_avg:.0f}<extra></extra>"
            ), row=row_idx, col=col_idx
        )
        summary.append({"Mục tiêu": obj[:60], "Số VĐ": len(s_obj),
                         "S TB": round(vals[0], 1), "O TB": round(vals[1], 1),
                         "D TB": round(vals[2], 1), "RPN TB": round(rpn_avg, 0),
                         "Mức rủi ro": _risk(rpn_avg),
                         "Điểm ĐL TB": round(s_obj["quantitative_score"].mean(), 2)})

    polar_cfg = dict(radialaxis=dict(range=[0, 10], tickvals=[2, 4, 6, 8, 10], gridcolor="#ddd"),
                     angularaxis=dict(gridcolor="#ddd"))
    for i in range(n):
        key = "polar" if i == 0 else f"polar{i+1}"
        fig.update_layout(**{key: polar_cfg})

    fig.update_layout(height=420 * rows_n, showlegend=False,
                       title=f"FMEA Radar theo Mục tiêu – {sel_period}")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Bảng tóm tắt FMEA theo Mục tiêu")
    df_s = pd.DataFrame(summary).sort_values("RPN TB", ascending=False)
    st.dataframe(df_s, use_container_width=True, hide_index=True)

    # Radar overlay: all objectives on one chart
    st.markdown("---")
    st.subheader("🕸️ Radar chồng: So sánh tất cả Mục tiêu")
    fig2 = go.Figure()
    _add_zones(fig2)
    for i, obj in enumerate(objs):
        s_obj = sub[sub["objective_text"] == obj]
        vals = _avg_vals(s_obj)
        c = PERIOD_COLORS[i % len(PERIOD_COLORS)]
        fig2.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=THETA5 + [THETA5[0]],
            fill="toself", line=dict(color=c, width=2),
            name=obj[:35] + ("…" if len(obj) > 35 else "")
        ))
    fig2.update_layout(
        polar=dict(radialaxis=dict(range=[0, 10], tickvals=[2, 4, 6, 8, 10])),
        title=f"Tất cả Mục tiêu – {sel_period}", height=520,
        legend=dict(orientation="h", yanchor="bottom", y=-0.35)
    )
    st.plotly_chart(fig2, use_container_width=True)


# ── Mode 4: Theo bộ phận ─────────────────────────────────────────────────────

def _radar_by_dept(df):
    st.subheader("🕸️ FMEA Radar – Theo Bộ phận")

    dept_map = get_department_map()
    dept_rows = []
    for _, row in df.iterrows():
        for did in (row.get("department_ids") or []):
            r = row.to_dict()
            r["dept_name"] = dept_map.get(did, did)
            dept_rows.append(r)

    if not dept_rows:
        st.info("Không có dữ liệu phân bộ phận. Đảm bảo mục tiêu đã gán bộ phận ở Module 1.")
        return

    df_d = pd.DataFrame(dept_rows)
    col1, col2 = st.columns(2)
    with col1:
        periods = _sorted_periods(df)
        sel_p = st.selectbox("Chọn đợt", periods, key="dept_period")
    with col2:
        all_depts = sorted(df_d["dept_name"].unique())
        sel_depts = st.multiselect("Bộ phận (để trống = tất cả)", all_depts, key="dept_sel")

    sub_d = df_d[df_d["period_label"] == sel_p]
    if sel_depts:
        sub_d = sub_d[sub_d["dept_name"].isin(sel_depts)]

    depts = sub_d["dept_name"].unique()
    if len(depts) == 0:
        st.warning("Không có bộ phận nào trong bộ lọc.")
        return

    # Radar overlay
    fig = go.Figure()
    _add_zones(fig)
    summary = []
    for i, dept in enumerate(depts):
        d = sub_d[sub_d["dept_name"] == dept]
        vals = _avg_vals(d)
        rpn_avg = d["rpn_score"].mean()
        c = PERIOD_COLORS[i % len(PERIOD_COLORS)]
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=THETA5 + [THETA5[0]],
            fill="toself", line=dict(color=c, width=2.5),
            name=dept,
            hovertemplate=f"<b>{dept}</b><br>%{{theta}}: %{{r:.1f}}"
                          f"<br>RPN TB: {rpn_avg:.0f}<extra></extra>"
        ))
        summary.append({"Bộ phận": dept, "Số VĐ": len(d),
                         "S TB": round(vals[0], 1), "O TB": round(vals[1], 1),
                         "D TB": round(vals[2], 1), "RPN TB": round(rpn_avg, 0),
                         "Mức rủi ro": _risk(rpn_avg)})

    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 10], tickvals=[2, 4, 6, 8, 10])),
        title=f"FMEA Radar theo Bộ phận – {sel_p}",
        height=520, showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3)
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    col_tbl, col_heat = st.columns(2)
    with col_tbl:
        st.subheader("📋 Bảng so sánh")
        st.dataframe(pd.DataFrame(summary).sort_values("RPN TB", ascending=False),
                     use_container_width=True, hide_index=True)
    with col_heat:
        st.subheader("🟥 Heatmap S / O / D")
        heat = pd.DataFrame([{"Bộ phận": r["Bộ phận"],
                               "S": r["S TB"], "O": r["O TB"], "D": r["D TB"]}
                              for r in summary]).set_index("Bộ phận")
        fig_h = px.imshow(heat, color_continuous_scale="RdYlGn_r",
                           zmin=1, zmax=10, text_auto=True,
                           labels={"x": "Chỉ số", "y": "Bộ phận", "color": "Điểm TB"})
        fig_h.update_traces(textfont_size=13)
        st.plotly_chart(fig_h, use_container_width=True)

    # Radar lịch sử theo bộ phận
    if len(periods) >= 2:
        st.markdown("---")
        st.subheader("📈 Lịch sử FMEA theo Bộ phận")
        sel_dept_hist = st.selectbox("Chọn bộ phận", sorted(df_d["dept_name"].unique()), key="dept_hist")
        df_hist = df_d[df_d["dept_name"] == sel_dept_hist]
        hist_rows = []
        for p in _sorted_periods(df_d):
            pp = df_hist[df_hist["period_label"] == p]
            if not pp.empty:
                v = _avg_vals(pp)
                hist_rows.append({"Đợt": p,
                                   "S": round(v[0], 1), "O": round(v[1], 1),
                                   "D": round(v[2], 1), "RPN": round(pp["rpn_score"].mean(), 0)})
        if hist_rows:
            df_ht = pd.DataFrame(hist_rows)
            df_ht_m = df_ht.melt(id_vars=["Đợt"], value_vars=["S", "O", "D"], var_name="Chỉ số", value_name="Điểm")
            fig_hl = px.line(df_ht_m, x="Đợt", y="Điểm", color="Chỉ số", markers=True,
                              title=f"Xu hướng S/O/D – {sel_dept_hist}",
                              color_discrete_map={"S": COLORS["critical"],
                                                   "O": COLORS["high"], "D": COLORS["info"]})
            fig_hl.add_hline(y=SCORE_HIGH, line_dash="dot", line_color="red")
            fig_hl.update_layout(yaxis_range=[0, 11], height=350)
            st.plotly_chart(fig_hl, use_container_width=True)


# ── Mode 5: Phân tích từng vấn đề ────────────────────────────────────────────

def _radar_per_finding(df):
    st.subheader("🕸️ FMEA Radar – Từng Vấn đề")

    col1, col2 = st.columns(2)
    with col1:
        sel_p = st.selectbox("Chọn đợt", _sorted_periods(df), key="pf_p")
    sub = df[df["period_label"] == sel_p]
    findings = sub["finding_name"].dropna().tolist()
    with col2:
        sel_f = st.selectbox("Chọn vấn đề", findings, key="pf_f")

    row = sub[sub["finding_name"] == sel_f].iloc[0]
    s  = float(row.get("severity_score")   or 5)
    o  = float(row.get("occurrence_score") or 5)
    d  = float(row.get("detection_score")  or 5)
    pi = float(row.get("process_indicator_score") or 5)
    q  = float(row.get("quantitative_score") or 2.5) / 5 * 10
    rpn = float(row.get("rpn_score") or (s * o * d))

    avg_vals_period = _avg_vals(sub)

    color = COLORS["critical"] if rpn >= RPN_HIGH else \
            COLORS["high"] if rpn >= RPN_MED else COLORS["low"]

    col_r, col_i = st.columns([3, 2])
    with col_r:
        fig = go.Figure()
        _add_zones(fig)
        fig.add_trace(_single_radar_trace([s, o, d, pi, q], sel_f[:40], color))
        # Period average as reference
        fig.add_trace(go.Scatterpolar(
            r=avg_vals_period + [avg_vals_period[0]],
            theta=THETA5 + [THETA5[0]],
            line=dict(color="#aaa", width=1.5, dash="dot"),
            fill=None, name=f"TB Đợt ({sel_p})", hoverinfo="skip"
        ))
        fig.update_layout(**_polar_layout(f"FMEA – {sel_f[:50]}"))
        st.plotly_chart(fig, use_container_width=True)

    with col_i:
        st.markdown("#### 📋 Chi tiết FMEA")
        st.markdown("---")
        rpn_icon = "🔴" if rpn >= RPN_HIGH else "🟠" if rpn >= RPN_MED else "🟡" if rpn >= 50 else "🟢"
        st.metric(f"{rpn_icon} RPN = S × O × D", f"{rpn:.0f}", f"= {s:.0f}×{o:.0f}×{d:.0f}")
        st.markdown("---")
        st.write(f"**S – Nghiêm trọng:** {_badge(s)}")
        st.write(f"**O – Tần suất:** {_badge(o)}")
        st.write(f"**D – Khó phát hiện:** {_badge(d)}")
        st.write(f"**PI – Tuân thủ QT:** {_badge(pi, invert=True)}")
        st.write(f"**Q – Điểm ĐL:** {row.get('quantitative_score', '—')} / 5")
        st.markdown("---")
        warnings = []
        if s >= SCORE_HIGH: warnings.append("⚠️ Mức nghiêm trọng cao")
        if o >= SCORE_HIGH: warnings.append("⚠️ Tần suất xảy ra thường xuyên")
        if d >= SCORE_HIGH: warnings.append("⚠️ Rất khó phát hiện lỗi")
        for w in warnings: st.error(w)
        if not warnings: st.success("✅ Các chỉ số ở mức kiểm soát được")
        if row.get("corrective_action"):
            st.markdown("---")
            st.info(f"💡 **Giải pháp:** {row['corrective_action']}")

    # Gauge charts S / O / D
    st.markdown("---")
    st.subheader("🎯 Gauge Charts – S / O / D")
    gcols = st.columns(3)
    for gc, (title, val, note) in zip(gcols, [
        ("S – Severity", s, "Ảnh hưởng của lỗi"),
        ("O – Occurrence", o, "Tần suất lỗi"),
        ("D – Detection", d, "Độ khó phát hiện")
    ]):
        gauge_color = COLORS["critical"] if val >= SCORE_HIGH else \
                      COLORS["high"] if val >= 6 else COLORS["low"]
        fig_g = go.Figure(go.Indicator(
            mode="gauge+number",
            value=val,
            title={"text": f"{title}<br><span style='font-size:11px;color:gray'>{note}</span>"},
            gauge=dict(
                axis=dict(range=[0, 10], tickvals=[0, 2, 4, 6, 8, 10]),
                bar=dict(color=gauge_color),
                steps=[dict(range=[0, 4], color="#e8f8f5"),
                       dict(range=[4, 7], color="#fef9e7"),
                       dict(range=[7, 10], color="#fdedec")],
                threshold=dict(line=dict(color="red", width=3), value=SCORE_HIGH)
            )
        ))
        fig_g.update_layout(height=270, margin=dict(t=80, b=20, l=20, r=20))
        gc.plotly_chart(fig_g, use_container_width=True)

    # Scatter: this finding vs all findings in period
    st.markdown("---")
    st.subheader(f"📍 Vị trí vấn đề trong Đợt {sel_p}")
    sub_plot = sub.copy()
    sub_plot["highlight"] = sub_plot["finding_name"].apply(
        lambda n: "📌 Vấn đề đang xem" if n == sel_f else "Các vấn đề khác")
    sub_plot["size"] = sub_plot["rpn_score"].clip(10, 1000)
    fig_sc = px.scatter(sub_plot, x="severity_score", y="occurrence_score",
                         size="size", color="highlight",
                         hover_name="finding_name",
                         hover_data={"rpn_score": True, "detection_score": True, "size": False},
                         color_discrete_map={"📌 Vấn đề đang xem": "#e74c3c",
                                              "Các vấn đề khác": "#3498db"},
                         title=f"S vs O – Kích thước = RPN | {sel_p}",
                         labels={"severity_score": "S – Nghiêm trọng",
                                  "occurrence_score": "O – Tần suất"},
                         size_max=50, height=420)
    fig_sc.add_vline(x=SCORE_HIGH, line_dash="dash", line_color="red")
    fig_sc.add_hline(y=SCORE_HIGH, line_dash="dash", line_color="red")
    fig_sc.add_shape(type="rect", x0=SCORE_HIGH, y0=SCORE_HIGH, x1=10.5, y1=10.5,
                      fillcolor="rgba(231,76,60,0.08)", line_width=0)
    fig_sc.update_layout(xaxis_range=[0, 11], yaxis_range=[0, 11])
    st.plotly_chart(fig_sc, use_container_width=True)


# ── Mode 6: Ma trận rủi ro ───────────────────────────────────────────────────

def _risk_matrix(df):
    st.subheader("📊 Ma trận Rủi ro FMEA")

    fdf = df.dropna(subset=["severity_score", "occurrence_score", "detection_score"]).copy()
    col1, col2 = st.columns(2)
    AX = {"severity_score": "S – Nghiêm trọng",
          "occurrence_score": "O – Tần suất",
          "detection_score": "D – Khó phát hiện"}
    with col1:
        x_ax = st.selectbox("Trục X", list(AX.keys()), format_func=lambda x: AX[x])
    with col2:
        y_ax = st.selectbox("Trục Y", list(AX.keys()),
                             index=1, format_func=lambda x: AX[x])

    fdf["short"] = fdf["finding_name"].str[:30] + "…"
    fdf["rpn_sz"] = fdf["rpn_score"].clip(10, 1000)

    fig = px.scatter(
        fdf, x=x_ax, y=y_ax, size="rpn_sz", color="period_label",
        hover_name="finding_name",
        hover_data={"rpn_score": True, "severity_score": True,
                    "occurrence_score": True, "detection_score": True, "rpn_sz": False},
        title=f"Bubble Chart: {AX[x_ax]} vs {AX[y_ax]}<br>"
              f"<sup>Kích thước = RPN | Màu = Đợt audit</sup>",
        labels={x_ax: AX[x_ax], y_ax: AX[y_ax], "period_label": "Đợt"},
        size_max=55, height=530
    )
    fig.add_vline(x=SCORE_HIGH, line_dash="dash", line_color="red",
                  annotation_text=f"Ngưỡng ({SCORE_HIGH})")
    fig.add_hline(y=SCORE_HIGH, line_dash="dash", line_color="red",
                  annotation_text=f"Ngưỡng ({SCORE_HIGH})")
    fig.add_shape(type="rect", x0=SCORE_HIGH, y0=SCORE_HIGH, x1=10.5, y1=10.5,
                  fillcolor="rgba(231,76,60,0.08)", line_width=0)
    fig.add_annotation(x=9.2, y=9.5, text="⚠️ Vùng rủi ro cao",
                       showarrow=False, font=dict(color="red", size=12))
    fig.update_layout(xaxis_range=[0, 11], yaxis_range=[0, 11])
    st.plotly_chart(fig, use_container_width=True)

    # Heatmap RPN: Period × Objective
    st.markdown("---")
    st.subheader("🟥 Heatmap RPN – Đợt × Mục tiêu")
    pivot = fdf.groupby(["period_label", "objective_text"])["rpn_score"].mean().reset_index()
    if not pivot.empty:
        pw = pivot.pivot(index="objective_text", columns="period_label", values="rpn_score")
        pw.index = pw.index.str[:40] + "…"
        fig_h = px.imshow(pw, color_continuous_scale="RdYlGn_r",
                           zmin=0, zmax=1000, text_auto=".0f",
                           title="RPN Trung bình – Mục tiêu × Đợt",
                           labels={"x": "Đợt", "y": "Mục tiêu", "color": "RPN TB"},
                           aspect="auto")
        fig_h.update_traces(textfont_size=11)
        fig_h.update_layout(height=max(300, 80 * len(pw)))
        st.plotly_chart(fig_h, use_container_width=True)

    # Top 10
    st.markdown("---")
    st.subheader("🏆 Top 10 Vấn đề RPN cao nhất")
    top10 = fdf.nlargest(10, "rpn_score")[
        ["period_label", "objective_text", "finding_name",
         "severity_score", "occurrence_score", "detection_score",
         "rpn_score", "risk_level"]
    ].rename(columns={"period_label": "Đợt", "objective_text": "Mục tiêu",
                       "finding_name": "Vấn đề", "severity_score": "S",
                       "occurrence_score": "O", "detection_score": "D",
                       "rpn_score": "RPN", "risk_level": "Mức rủi ro"})
    top10["Mục tiêu"] = top10["Mục tiêu"].str[:40] + "…"
    top10["Vấn đề"]   = top10["Vấn đề"].str[:50] + "…"
    st.dataframe(top10, use_container_width=True, hide_index=True)

    # RPN distribution histogram
    st.markdown("---")
    st.subheader("📊 Phân phối RPN toàn bộ")
    fig_hist = px.histogram(fdf.dropna(subset=["rpn_score"]), x="rpn_score",
                             nbins=25, color="period_label",
                             title="Phân phối RPN theo đợt",
                             labels={"rpn_score": "RPN", "count": "Số vấn đề",
                                      "period_label": "Đợt"}, barmode="overlay",
                             opacity=0.7, height=380)
    fig_hist.add_vline(x=RPN_MED, line_dash="dash", line_color="orange",
                        annotation_text=f"Cao ({RPN_MED})")
    fig_hist.add_vline(x=RPN_HIGH, line_dash="dash", line_color="red",
                        annotation_text=f"Nghiêm trọng ({RPN_HIGH})")
    st.plotly_chart(fig_hist, use_container_width=True)


# =============================================================================
# TABS 1, 2, 4, 5 – Unchanged from previous version
# =============================================================================

def _render_timeseries(df, time_group):
    st.subheader("📈 Điểm đánh giá theo thời gian")
    gc = _group_col(time_group)
    objs = df["objective_text"].dropna().unique()
    sel = st.multiselect("Chọn mục tiêu", objs.tolist(),
                          default=objs[:3].tolist() if len(objs) >= 3 else objs.tolist())
    sub = df[df["objective_text"].isin(sel)] if sel else df
    agg = sub.groupby([gc, "objective_text"])["quantitative_score"].mean().reset_index()
    if not agg.empty:
        fig = px.line(agg, x=gc, y="quantitative_score", color="objective_text",
                      markers=True, title="Điểm định lượng TB", range_y=[0, 5.5])
        fig.add_hline(y=3, line_dash="dash", line_color="red", annotation_text="Ngưỡng (3)")
        fig.add_hline(y=4, line_dash="dot", line_color="orange", annotation_text="Tốt (4)")
        st.plotly_chart(fig, use_container_width=True)
    agg_r = sub.groupby(gc)["rpn_score"].mean().reset_index()
    if not agg_r.empty and agg_r["rpn_score"].notna().any():
        st.markdown("---")
        fig2 = px.bar(agg_r, x=gc, y="rpn_score", title="RPN TB",
                      color="rpn_score", color_continuous_scale="RdYlGn_r")
        st.plotly_chart(fig2, use_container_width=True)


def _render_classification(df, time_group):
    gc = _group_col(time_group)
    df = df.copy()
    df["q_class"] = df["quantitative_score"].apply(_classify)
    CM = {"Kết quả ổn": "#2ecc71", "Tạm chấp nhận": "#f39c12",
          "Dưới kỳ vọng": "#e74c3c", "Chưa đánh giá": "#95a5a6"}
    col1, col2 = st.columns(2)
    with col1:
        c = df["q_class"].value_counts().reset_index()
        c.columns = ["Phân loại", "Số lượng"]
        st.plotly_chart(px.pie(c, names="Phân loại", values="Số lượng",
                                color="Phân loại", color_discrete_map=CM,
                                title="Tỷ lệ tổng thể"), use_container_width=True)
    with col2:
        agg = df.groupby([gc, "q_class"]).size().reset_index(name="count")
        if not agg.empty:
            st.plotly_chart(px.bar(agg, x=gc, y="count", color="q_class",
                                    color_discrete_map=CM, barmode="stack",
                                    title=f"Phân bố theo {time_group}"),
                             use_container_width=True)


def _render_fmea_comparison(df):
    st.subheader("🔢 So sánh FMEA (RPN cũ vs mới)")
    if "previous_finding_id" not in df.columns or df["previous_finding_id"].isna().all():
        st.info("Chưa có dữ liệu so sánh FMEA qua đợt.")
        if df["rpn_score"].notna().any():
            fig = px.histogram(df.dropna(subset=["rpn_score"]), x="rpn_score",
                                nbins=20, title="Phân phối RPN hiện tại",
                                color_discrete_sequence=[COLORS["critical"]])
            fig.add_vline(x=RPN_MED, line_dash="dash", annotation_text=f"Cao ({RPN_MED})")
            fig.add_vline(x=RPN_HIGH, line_dash="dash", line_color="red",
                           annotation_text=f"Nghiêm trọng ({RPN_HIGH})")
            st.plotly_chart(fig, use_container_width=True)
        return
    df_p = df[df["previous_finding_id"].notna()].copy()
    db = get_db()
    prev = {}
    for pid in df_p["previous_finding_id"].dropna().unique():
        r = db.table("audit_findings").select(
            "id,rpn_score,finding_name,severity_score,occurrence_score,detection_score"
        ).eq("id", pid).execute().data
        if r: prev[pid] = r[0]
    df_p["prev_rpn"] = df_p["previous_finding_id"].map(lambda x: prev.get(x, {}).get("rpn_score"))
    df_c = df_p.dropna(subset=["rpn_score", "prev_rpn"])
    if df_c.empty:
        st.info("Chưa tìm được dữ liệu đợt trước để so sánh.")
        return
    df_c = df_c.copy()
    df_c["delta"] = df_c["rpn_score"] - df_c["prev_rpn"]
    col1, col2, col3 = st.columns(3)
    col1.metric("✅ Cải thiện", int((df_c["delta"] < 0).sum()))
    col2.metric("❌ Tệ hơn", int((df_c["delta"] > 0).sum()))
    col3.metric("➡️ Không đổi", int((df_c["delta"] == 0).sum()))
    fig = go.Figure()
    for _, r in df_c.iterrows():
        c = COLORS["low"] if r["delta"] < 0 else COLORS["critical"]
        fig.add_trace(go.Bar(name=r["finding_name"][:35],
                              x=["RPN Cũ", "RPN Mới"],
                              y=[r["prev_rpn"], r["rpn_score"]],
                              text=[f"{r['prev_rpn']:.0f}", f"{r['rpn_score']:.0f}"],
                              textposition="auto",
                              marker_color=[COLORS["info"], c]))
    fig.update_layout(barmode="group", title="So sánh RPN: Cũ vs Mới")
    st.plotly_chart(fig, use_container_width=True)


def _render_followup(df):
    if "follow_up_option" not in df.columns:
        st.info("Không có dữ liệu.")
        return
    df = df.copy()
    df["follow_lbl"] = df["follow_up_option"].map(FOLLOW_UP_LABELS)
    c = df["follow_lbl"].value_counts().reset_index()
    c.columns = ["Gợi ý", "Số lượng"]
    c["Tỷ lệ %"] = (c["Số lượng"] / c["Số lượng"].sum() * 100).round(1)
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(px.pie(c, names="Gợi ý", values="Số lượng",
                                title="Tỷ lệ Gợi ý Thêm",
                                color_discrete_sequence=px.colors.qualitative.Set3),
                         use_container_width=True)
    with col2:
        st.dataframe(c, use_container_width=True, hide_index=True)
    if "period_label" in df.columns:
        st.markdown("---")
        agg = df.groupby(["period_label", "follow_lbl"]).size().reset_index(name="count")
        st.plotly_chart(px.bar(agg, x="period_label", y="count", color="follow_lbl",
                                barmode="stack", title="Gợi ý thêm qua các đợt"),
                         use_container_width=True)
    st.markdown("---")
    st.subheader("🔍 Vấn đề cần Giám sát tiếp")
    needs = df[df["follow_up_option"] == "additional_monitoring"]
    if needs.empty:
        st.success("Không có vấn đề nào cần giám sát thêm.")
    else:
        cols = ["year", "sequence_no", "objective_text", "finding_name",
                "quantitative_score", "rpn_score"]
        st.dataframe(needs[[c for c in cols if c in needs.columns]],
                     use_container_width=True, hide_index=True)
