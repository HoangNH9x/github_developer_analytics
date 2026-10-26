from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed" / "canonical"

st.set_page_config(
    page_title="GitHub Developer Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
    [data-testid="stMetric"] {border: 1px solid rgba(120,120,120,.22); padding: .8rem; border-radius: .8rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_csv(filename: str) -> pd.DataFrame:
    path = DATA_DIR / filename
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
        return pd.DataFrame()


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def safe_sum(frame: pd.DataFrame, column: str) -> int | float:
    if frame.empty or column not in frame:
        return 0
    return numeric(frame[column]).sum()


def complete_metric_total(frame: pd.DataFrame, metric: str, status_col: str) -> int | float:
    if frame.empty or metric not in frame or status_col not in frame:
        return 0
    valid = frame[frame[status_col].isin(["COMPLETE", "ZERO_CONFIRMED"])]
    return numeric(valid[metric]).sum()


def missing_files() -> list[str]:
    required = [
        "repository_country_metrics.csv",
        "vietnam_vs_other_countries_comparison.csv",
        "monthly_activity.csv",
        "data_quality_report.csv",
        "collection_errors.csv",
    ]
    return [name for name in required if not (DATA_DIR / name).exists()]


metrics = load_csv("repository_country_metrics.csv")
country_comparison = load_csv("country_repository_comparison.csv")
vn_comparison = load_csv("vietnam_vs_other_countries_comparison.csv")
monthly = load_csv("monthly_activity.csv")
developers = load_csv("developer_activity_summary.csv")
quality = load_csv("data_quality_report.csv")
dedup_audit = load_csv("deduplication_audit.csv")
collection_errors = load_csv("collection_errors.csv")

st.title("GitHub Developer Analytics")
st.caption("Phân tích hoạt động repository · So sánh Việt Nam và quốc tế · Theo dõi chất lượng dữ liệu")

with st.sidebar:
    st.header("Bộ lọc")
    st.caption("Bộ lọc chỉ ảnh hưởng đến nội dung dashboard; không làm thay đổi CSV nguồn.")

    if not metrics.empty and "owner_country" in metrics.columns:
        countries = sorted(metrics["owner_country"].dropna().astype(str).unique().tolist())
        country_options = ["Tất cả quốc gia"] + countries + ["Unknown / unresolved"]
        selected_country = st.selectbox("Quốc gia owner", country_options, index=0)
    else:
        selected_country = "Tất cả quốc gia"

    if not metrics.empty and "language" in metrics.columns:
        languages = sorted(metrics["language"].dropna().astype(str).unique().tolist())
        selected_language = st.selectbox("Ngôn ngữ chính", ["Tất cả ngôn ngữ"] + languages)
    else:
        selected_language = "Tất cả ngôn ngữ"

    if not metrics.empty and "sample_source" in metrics.columns:
        sources = sorted(metrics["sample_source"].dropna().astype(str).unique().tolist())
        selected_source = st.selectbox("Nguồn chọn mẫu", ["Tất cả nguồn"] + sources)
    else:
        selected_source = "Tất cả nguồn"

    if st.button("Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

filtered = metrics.copy()
if not filtered.empty:
    if selected_country != "Tất cả quốc gia":
        if selected_country == "Unknown / unresolved":
            filtered = filtered[filtered["owner_country"].isna()]
        else:
            filtered = filtered[filtered["owner_country"].astype(str) == selected_country]
    if selected_language != "Tất cả ngôn ngữ" and "language" in filtered:
        filtered = filtered[filtered["language"].astype(str) == selected_language]
    if selected_source != "Tất cả nguồn" and "sample_source" in filtered:
        filtered = filtered[filtered["sample_source"].astype(str) == selected_source]

missing = missing_files()
if missing:
    st.warning(
        "Chưa có đủ CSV canonical để hiển thị toàn bộ dashboard. "
        "Hãy chạy thử pipeline sau khi cấu hình token local, kiểm tra audit rồi mới triển khai website. "
        f"File hiện còn thiếu: {', '.join(missing)}"
    )

if not metrics.empty:
    start_values = metrics["study_start"].dropna().astype(str).unique().tolist() if "study_start" in metrics else []
    end_values = metrics["study_end"].dropna().astype(str).unique().tolist() if "study_end" in metrics else []
    if start_values and end_values:
        st.caption(f"Khoảng nghiên cứu: {min(start_values)} đến {max(end_values)} · Stars/Forks là snapshot tại thời điểm crawl.")

tab_overview, tab_vietnam, tab_trends, tab_repositories, tab_developers, tab_quality, tab_insights = st.tabs(
    ["Tổng quan", "Việt Nam & quốc tế", "Xu hướng thời gian", "Repository Explorer", "Developers", "Chất lượng dữ liệu", "Insights"]
)

with tab_overview:
    st.subheader("Tổng quan mẫu nghiên cứu")
    if filtered.empty:
        st.info("Chưa có dữ liệu repository canonical hoặc bộ lọc không trả về repository.")
    else:
        total_repos = filtered["repository_id"].nunique() if "repository_id" in filtered else len(filtered)
        total_stars = safe_sum(filtered, "stars_snapshot")
        total_forks = safe_sum(filtered, "forks_snapshot")
        commits_total = complete_metric_total(filtered, "commits_count_window", "commits_status")
        issues_total = complete_metric_total(filtered, "issues_created_count_window", "issues_status")
        prs_total = complete_metric_total(filtered, "prs_created_count_window", "prs_status")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Repositories", f"{int(total_repos):,}")
        c2.metric("Stars (snapshot)", f"{int(total_stars):,}")
        c3.metric("Forks (snapshot)", f"{int(total_forks):,}")
        c4.metric("Commits đã xác nhận", f"{int(commits_total):,}")
        c5, c6, c7 = st.columns(3)
        c5.metric("Issues được tạo", f"{int(issues_total):,}")
        c6.metric("Pull Requests được tạo", f"{int(prs_total):,}")
        c7.metric(
            "Owner đã nhận diện quốc gia",
            f"{int(filtered['owner_country'].notna().sum()):,}" if "owner_country" in filtered else "—",
        )
        st.caption("Các tổng hoạt động chỉ tính repository có trạng thái COMPLETE/ZERO_CONFIRMED cho metric tương ứng.")

        left, right = st.columns(2)
        with left:
            top = filtered.copy()
            if "stars_snapshot" in top:
                top["stars_snapshot"] = numeric(top["stars_snapshot"])
                top = top.nlargest(10, "stars_snapshot")
            else:
                top = top.head(0)
            if not top.empty:
                fig = px.bar(
                    top.sort_values("stars_snapshot"),
                    x="stars_snapshot", y="full_name", orientation="h",
                    title="Top repositories theo Stars snapshot",
                    labels={"stars_snapshot": "Stars tại ngày crawl", "full_name": "Repository"},
                )
                fig.update_layout(height=440, yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig, use_container_width=True)
        with right:
            if not country_comparison.empty:
                chart = country_comparison.copy()
                if selected_country != "Tất cả quốc gia":
                    chart = chart[chart["owner_country"].astype(str) == selected_country]
                if not chart.empty:
                    chart = chart.nlargest(12, "repositories_total")
                    fig = px.bar(
                        chart.sort_values("repositories_total"),
                        x="repositories_total", y="owner_country", orientation="h",
                        title="Số repository theo quốc gia owner",
                        labels={"repositories_total": "Repositories", "owner_country": "Quốc gia owner"},
                    )
                    fig.update_layout(height=440, yaxis={"categoryorder": "total ascending"})
                    st.plotly_chart(fig, use_container_width=True)

with tab_vietnam:
    st.subheader("So sánh Việt Nam và quốc tế")
    st.caption("Quốc gia được suy ra từ location công khai tự khai báo của owner. Đây là mô tả mẫu đã chọn, không phải kết luận về toàn bộ GitHub hay năng suất của cả quốc gia.")
    if vn_comparison.empty:
        st.info("Chưa có vietnam_vs_other_countries_comparison.csv.")
    else:
        display = vn_comparison.copy()
        preferred = [
            "comparison_group", "repositories_total", "stars_sum_snapshot", "stars_avg_snapshot",
            "forks_sum_snapshot", "forks_avg_snapshot", "commits_sum_complete",
            "commits_avg_per_repo_complete", "issues_sum_complete", "issues_avg_per_repo_complete",
            "prs_sum_complete", "prs_avg_per_repo_complete", "repositories_with_complete_commits",
            "repositories_with_complete_issues", "repositories_with_complete_prs",
        ]
        display = display[[col for col in preferred if col in display.columns]]
        st.dataframe(display, use_container_width=True, hide_index=True)
        chart_metric = st.selectbox(
            "Chỉ số để so sánh",
            ["repositories_total", "stars_sum_snapshot", "forks_sum_snapshot",
             "commits_sum_complete", "issues_sum_complete", "prs_sum_complete"],
            format_func=lambda x: {
                "repositories_total": "Số repositories",
                "stars_sum_snapshot": "Tổng Stars snapshot",
                "forks_sum_snapshot": "Tổng Forks snapshot",
                "commits_sum_complete": "Tổng Commits đã xác nhận",
                "issues_sum_complete": "Tổng Issues được tạo đã xác nhận",
                "prs_sum_complete": "Tổng PR được tạo đã xác nhận",
            }.get(x, x),
        )
        if chart_metric in vn_comparison.columns:
            fig = px.bar(
                vn_comparison,
                x="comparison_group", y=chart_metric, color="comparison_group",
                title="So sánh theo nhóm owner-country",
            )
            fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Giá trị")
            st.plotly_chart(fig, use_container_width=True)

with tab_trends:
    st.subheader("Xu hướng hoạt động theo tháng")
    if monthly.empty:
        st.info("Chưa có monthly_activity.csv hoặc chưa có metric hoàn chỉnh để tạo xu hướng.")
    else:
        countries_monthly = sorted(monthly["owner_country"].dropna().astype(str).unique().tolist())
        monthly_options = ["Tất cả quốc gia"] + countries_monthly
        trend_country = st.selectbox("Lọc quốc gia trong xu hướng", monthly_options, key="trend_country")
        trend = monthly.copy()
        if trend_country != "Tất cả quốc gia":
            trend = trend[trend["owner_country"].astype(str) == trend_country]
        trend = trend.groupby("activity_month", as_index=False).agg({
            "commits_count_complete": "sum",
            "issues_count_complete": "sum",
            "prs_count_complete": "sum",
        })
        if not trend.empty:
            metric_labels = {
                "commits_count_complete": "Commits",
                "issues_count_complete": "Issues được tạo",
                "prs_count_complete": "Pull Requests được tạo",
            }
            selected_metric = st.selectbox(
                "Hoạt động",
                list(metric_labels.keys()),
                format_func=lambda value: metric_labels[value],
            )
            fig = px.line(
                trend.sort_values("activity_month"),
                x="activity_month", y=selected_metric, markers=True,
                title=f"Xu hướng theo tháng — {metric_labels[selected_metric]}",
                labels={"activity_month": "Tháng", selected_metric: "Số bản ghi đã xác nhận"},
            )
            fig.update_layout(xaxis={"type": "category"})
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(trend.sort_values("activity_month", ascending=False), use_container_width=True, hide_index=True)

with tab_repositories:
    st.subheader("Repository Explorer")
    if filtered.empty:
        st.info("Không có repository phù hợp bộ lọc.")
    else:
        search = st.text_input("Tìm theo tên repository hoặc owner", "")
        explorer = filtered.copy()
        if search and "full_name" in explorer:
            explorer = explorer[explorer["full_name"].astype(str).str.contains(search, case=False, na=False)]
        order_col = st.selectbox(
            "Sắp xếp theo",
            [col for col in ["stars_snapshot", "forks_snapshot", "commits_count_window",
                             "issues_created_count_window", "prs_created_count_window", "full_name"] if col in explorer.columns],
        )
        if order_col in explorer:
            explorer = explorer.sort_values(order_col, ascending=(order_col == "full_name"), na_position="last")
        columns = [
            "full_name", "owner_login", "owner_country", "language", "stars_snapshot", "forks_snapshot",
            "commits_count_window", "commits_status", "issues_created_count_window", "issues_status",
            "prs_created_count_window", "prs_status", "sample_source", "html_url",
        ]
        columns = [col for col in columns if col in explorer.columns]
        st.dataframe(explorer[columns], use_container_width=True, hide_index=True, height=520)

with tab_developers:
    st.subheader("Contributor activity")
    st.caption("Bảng này đếm hoạt động của GitHub login được nhận diện từ commits, issues và PR trong các repository có metric hoàn chỉnh. Không gán country owner làm country của developer.")
    if developers.empty:
        st.info("Chưa có developer_activity_summary.csv hoặc chưa thu thập được contributor có login.")
    else:
        include_bots = st.checkbox("Bao gồm tài khoản bot trong leaderboard", value=False)
        developer_view = developers.copy()
        if not include_bots and "developer_login" in developer_view:
            bot_mask = developer_view["developer_login"].astype(str).str.lower().str.contains(r"\[bot\]|bot$", regex=True)
            developer_view = developer_view[~bot_mask]
        top_n = st.slider("Số contributor hiển thị", min_value=5, max_value=50, value=20, step=5)
        st.caption("Bot được tách khỏi leaderboard mặc định; bật ô trên nếu muốn xem cả bot.")
        st.dataframe(developer_view.head(top_n), use_container_width=True, hide_index=True)

with tab_quality:
    st.subheader("Data Quality & Crawl Coverage")
    if quality.empty:
        st.info("Chưa có data_quality_report.csv.")
    else:
        if "status" in quality.columns:
            st.dataframe(
                quality.sort_values(["status", "table_name", "check_name"]),
                use_container_width=True, hide_index=True, height=420,
            )
        else:
            st.dataframe(quality, use_container_width=True, hide_index=True)
    if not dedup_audit.empty:
        st.subheader("Bản ghi trùng được xử lý")
        st.dataframe(dedup_audit, use_container_width=True, hide_index=True)
    if not collection_errors.empty:
        st.subheader("Repository có metric partial/error hoặc chưa nhận diện được owner profile")
        st.dataframe(collection_errors, use_container_width=True, hide_index=True, height=320)
    if not metrics.empty:
        status_cols = [col for col in ["commits_status", "issues_status", "prs_status"] if col in metrics]
        if status_cols:
            st.subheader("Trạng thái từng metric")
            for col in status_cols:
                counts = metrics[col].fillna("NOT_RUN").value_counts().rename_axis("status").reset_index(name="repositories")
                fig = px.bar(counts, x="status", y="repositories", title=col)
                st.plotly_chart(fig, use_container_width=True)

with tab_insights:
    st.subheader("Ba insights được tính từ toàn bộ dataset")
    st.caption("Các số liệu bên dưới sử dụng repository_country_metrics.csv và monthly_activity.csv trong bộ processed đang nạp. Đây là mô tả của mẫu đã chọn, không phải kết luận đại diện cho toàn GitHub.")

    if metrics.empty:
        st.info("Chưa có repository metrics canonical để tính insights.")
    else:
        analysis = metrics.copy()
        metric_columns = [
            "commits_count_window",
            "issues_created_count_window",
            "prs_created_count_window",
        ]
        status_columns = ["commits_status", "issues_status", "prs_status"]
        for col in metric_columns:
            if col not in analysis:
                analysis[col] = pd.NA
            analysis[col] = numeric(analysis[col])

        valid_all = pd.Series(True, index=analysis.index)
        for col in status_columns:
            if col not in analysis:
                valid_all = valid_all & False
            else:
                valid_all = valid_all & analysis[col].isin(["COMPLETE", "ZERO_CONFIRMED"])
        analysis["activity_total_confirmed"] = analysis[metric_columns].sum(axis=1, min_count=3).where(valid_all)
        confirmed = analysis[analysis["activity_total_confirmed"].notna()].copy()
        event_total = numeric(confirmed["activity_total_confirmed"]).sum()
        top_repo = confirmed.sort_values("activity_total_confirmed", ascending=False).head(1)

        recognized_mask = analysis["owner_country"].notna() if "owner_country" in analysis else pd.Series(False, index=analysis.index)
        unknown_frame = confirmed[~recognized_mask.loc[confirmed.index]]
        unknown_events = numeric(unknown_frame["activity_total_confirmed"]).sum()
        unknown_share = (unknown_events / event_total * 100) if event_total else 0
        recognized_repos = int(recognized_mask.sum())
        recognized_share = (recognized_repos / analysis["repository_id"].nunique() * 100) if "repository_id" in analysis and analysis["repository_id"].nunique() else 0

        vietnam_frame = confirmed[confirmed["owner_country"].eq("Vietnam")] if "owner_country" in confirmed else confirmed.iloc[0:0]
        other_frame = confirmed[confirmed["owner_country"].notna() & confirmed["owner_country"].ne("Vietnam")] if "owner_country" in confirmed else confirmed.iloc[0:0]
        vn_avg = numeric(vietnam_frame["activity_total_confirmed"]).mean() if not vietnam_frame.empty else None
        other_avg = numeric(other_frame["activity_total_confirmed"]).mean() if not other_frame.empty else None

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Repositories (all metrics confirmed)", f"{len(confirmed):,}")
        k2.metric("Activity records confirmed", f"{int(event_total):,}")
        k3.metric("Owner-country recognized", f"{recognized_repos:,}", f"{recognized_share:.1f}%")
        k4.metric("Unknown-group activity share", f"{unknown_share:.1f}%")

        if not top_repo.empty:
            top_row = top_repo.iloc[0]
            top_share = (float(top_row["activity_total_confirmed"]) / event_total * 100) if event_total else 0
            st.markdown(
                f"**Insight 1 — Tập trung hoạt động:** {top_row.get('full_name', 'Unknown repo')} có "
                f"**{int(top_row['activity_total_confirmed']):,}** sự kiện, tương đương **{top_share:.2f}%** "
                "tổng của những repository có đủ trạng thái xác nhận. Cần hiển thị top repo cùng phân bố, tránh để một repo chi phối kết luận."
            )

        if vn_avg is not None and other_avg is not None:
            ratio = other_avg / vn_avg if vn_avg else None
            ratio_text = f"{ratio:.2f} lần" if ratio is not None else "không tính được vì mẫu Việt Nam có trung bình 0"
            st.markdown(
                f"**Insight 2 — Vietnam và quốc tế đã nhận diện:** trung bình hoạt động/repository là "
                f"**{vn_avg:,.1f}** ở Việt Nam (n={len(vietnam_frame)}) và **{other_avg:,.1f}** ở nhóm "
                f"quốc gia khác đã nhận diện (n={len(other_frame)}), chênh lệch {ratio_text}. "
                "Đây là khác biệt mô tả trong mẫu có chủ đích, không phải kết luận về năng suất quốc gia."
            )
            avg_chart = pd.DataFrame({
                "comparison_group": ["Vietnam", "Other recognized countries"],
                "average_activity_per_repo": [vn_avg, other_avg],
                "repositories": [len(vietnam_frame), len(other_frame)],
            })
            fig = px.bar(
                avg_chart,
                x="comparison_group",
                y="average_activity_per_repo",
                title="Trung bình hoạt động / repository (Unknown được loại khỏi phép so sánh)",
                text="repositories",
                labels={"comparison_group": "Nhóm owner-country", "average_activity_per_repo": "Sự kiện trung bình / repo", "repositories": "Số repository"},
            )
            st.plotly_chart(fig, use_container_width=True)

        if not monthly.empty:
            peak_specs = [
                ("commits_count_complete", "Commits"),
                ("issues_count_complete", "Issues"),
                ("prs_count_complete", "Pull Requests"),
            ]
            peaks = []
            for col, label in peak_specs:
                if col in monthly and "activity_month" in monthly:
                    values = monthly.groupby("activity_month")[col].sum()
                    if not values.empty:
                        peak_month = values.idxmax()
                        peaks.append(f"{label}: **{peak_month}** ({int(values.loc[peak_month]):,})")
            if peaks:
                st.markdown("**Insight 3 — Đỉnh hoạt động theo tháng:** " + " · ".join(peaks) + ". Tháng cuối trong cửa sổ nghiên cứu chỉ đầy đủ đến 20/10/2026.")

st.divider()
st.caption(
    "Nguồn: GitHub REST API. Hãy đọc Data Dictionary và phương pháp chọn mẫu trước khi diễn giải. "
    "Số liệu chưa hoàn chỉnh không được coi là số 0."
)
