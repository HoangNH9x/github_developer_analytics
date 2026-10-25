from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

# GitHub Developer Analytics — simple, defensive dashboard
# Place this file at the root of the project, next to the data/ folder.
ROOT = Path(__file__).resolve().parent
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"

st.set_page_config(
    page_title="GitHub Developer Analytics",
    page_icon="📊",
    layout="wide",
)

# Use a new widget key so Streamlit won't restore a stale selection from the prior app.
st.sidebar.title("GitHub Developer Analytics")
st.sidebar.caption("Assignment 1 → Assignment 2")
page = st.sidebar.radio(
    "Chọn nội dung",
    ["Tổng quan dữ liệu", "Tổng hợp theo Repository", "So sánh Việt Nam – quốc tế", "Phân bố theo quốc gia", "Độ phủ dữ liệu", "Phương pháp & câu hỏi"],
    index=0,
    key="navigation_final_v1",
)
st.sidebar.divider()
st.sidebar.caption("Nguồn: CSV trong data/processed. Ứng dụng chỉ đọc dữ liệu, không gọi GitHub API.")

st.title("GitHub Developer Analytics")
st.write("Tổng quan dữ liệu thu thập ở Giai đoạn 2 và so sánh nhóm Việt Nam với quốc tế đã nhận diện.")

CORE_FALLBACK = {
    "Repositories": 952,
    "Commits": 21646,
    "Issues": 119622,
    "Pull Requests": 222876,
}
ACTIVITY_ORDER = ["Repositories", "Commits", "Issues", "Pull Requests"]


def find_csv(filename: str) -> Path | None:
    candidates = [PROCESSED / filename, RAW / filename, ROOT / filename]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def read_csv(filename: str) -> pd.DataFrame:
    path = find_csv(filename)
    if path is None:
        return pd.DataFrame()
    try:
        return pd.read_csv(path, low_memory=False, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(path, low_memory=False, encoding="latin-1")
    except Exception as exc:
        st.warning(f"Không đọc được `{path.name}`: {exc}")
        return pd.DataFrame()


def get_col(df: pd.DataFrame, *choices: str) -> str | None:
    cols = {str(c).strip().casefold(): str(c) for c in df.columns}
    for name in choices:
        if name.casefold() in cols:
            return cols[name.casefold()]
    return None


def to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0)


def vn_label(value) -> str:
    if pd.isna(value):
        return "Chưa xác định"
    value = str(value).strip()
    mapping = {
        "Repositories": "Repositories",
        "Commits": "Commits",
        "Issues": "Issues",
        "Pull Requests": "Pull Requests",
        "Vietnam": "Việt Nam",
        "International": "Quốc tế đã nhận diện",
        "Unprofiled": "Chưa có hồ sơ",
        "Unresolved location": "Chưa xác định quốc gia",
        "Unknown": "Không rõ",
        "Other/Unknown": "Khác/không rõ",
        "Non-user account": "Không phải tài khoản User",
        "No Author Login": "Không có author login",
        "Unfiled": "Chưa phân loại",
    }
    return mapping.get(value, value)


def get_counts() -> dict:
    counts = CORE_FALLBACK.copy()
    # Prefer final audit file if available.
    audit = read_csv("final_audit_report.csv")
    if not audit.empty:
        name_col = get_col(audit, "table", "file", "dataset")
        count_col = get_col(audit, "rows", "raw_rows", "total_rows")
        if name_col and count_col:
            for _, row in audit.iterrows():
                name = str(row[name_col]).strip()
                if name in counts:
                    try:
                        counts[name] = int(float(row[count_col]))
                    except (TypeError, ValueError):
                        pass
    quality = read_csv("analysis_data_quality.csv")
    if not quality.empty:
        name_col = get_col(quality, "table")
        count_col = get_col(quality, "rows_in_research_period", "raw_rows", "rows")
        if name_col and count_col:
            for _, row in quality.iterrows():
                name = str(row[name_col]).strip()
                if name in counts:
                    try:
                        counts[name] = int(float(row[count_col]))
                    except (TypeError, ValueError):
                        pass
    return counts


def make_inventory(counts: dict) -> pd.DataFrame:
    quality = read_csv("analysis_data_quality.csv")
    rows = []
    if not quality.empty:
        name_col = get_col(quality, "table")
        count_col = get_col(quality, "rows_in_research_period", "raw_rows", "rows")
        old_col = get_col(quality, "oldest_valid_date", "oldest_date")
        new_col = get_col(quality, "newest_valid_date", "newest_date")
        if name_col and count_col:
            for _, r in quality.iterrows():
                name = str(r[name_col]).strip()
                if name not in CORE_FALLBACK:
                    continue
                oldest = pd.to_datetime(r[old_col], errors="coerce", utc=True) if old_col else pd.NaT
                newest = pd.to_datetime(r[new_col], errors="coerce", utc=True) if new_col else pd.NaT
                rows.append({
                    "Hạng mục": vn_label(name),
                    "Số bản ghi": int(to_num(pd.Series([r[count_col]])).iloc[0]),
                    "Ngày sớm nhất": oldest.strftime("%d/%m/%Y") if pd.notna(oldest) else "—",
                    "Ngày muộn nhất": newest.strftime("%d/%m/%Y") if pd.notna(newest) else "—",
                })
    by_name = {r["Hạng mục"]: r for r in rows}
    fallbacks = {
        "Repositories": ("02/01/2020", "24/09/2026"),
        "Commits": ("30/05/2024", "14/10/2026"),
        "Issues": ("14/04/2020", "18/10/2026"),
        "Pull Requests": ("28/02/2020", "18/10/2026"),
    }
    result = []
    for name in ACTIVITY_ORDER:
        label = vn_label(name)
        r = by_name.get(label)
        if r is None:
            old, new = fallbacks[name]
            r = {"Hạng mục": label, "Số bản ghi": counts[name], "Ngày sớm nhất": old, "Ngày muộn nhất": new}
        result.append(r)
    return pd.DataFrame(result)


# PAGE 1: overview
if page == "Tổng quan dữ liệu":
    st.header("1. Tổng quan dữ liệu thu thập")
    counts = get_counts()
    total = sum(counts.values())
    kpi_cols = st.columns(5)
    for col, title, value in zip(
        kpi_cols,
        ["Repositories", "Commits", "Issues", "Pull Requests", "Tổng 4 bảng"],
        [counts["Repositories"], counts["Commits"], counts["Issues"], counts["Pull Requests"], total],
    ):
        col.metric(title, f"{value:,}")

    st.info("Developer profiles là dữ liệu hỗ trợ liên kết tác giả/location; không cộng vào tổng bốn bảng nghiệp vụ.")
    left, right = st.columns([1, 1.35])
    with left:
        st.subheader("Cơ cấu số bản ghi")
        chart_df = pd.DataFrame({"Hạng mục": list(counts.keys()), "Số bản ghi": list(counts.values())})
        chart_df["Hạng mục"] = pd.Categorical(chart_df["Hạng mục"], categories=ACTIVITY_ORDER, ordered=True)
        chart_df = chart_df.sort_values("Số bản ghi", ascending=True)
        fig = px.bar(chart_df, x="Số bản ghi", y="Hạng mục", orientation="h", text="Số bản ghi",
                     color="Hạng mục", color_discrete_map={
                         "Repositories": "#64748b", "Commits": "#2563eb", "Issues": "#0d9488", "Pull Requests": "#f97316"
                     })
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False, showlegend=False)
        fig.update_layout(height=360, margin=dict(l=5, r=35, t=10, b=5), xaxis_title="Số bản ghi", yaxis_title="")
        st.plotly_chart(fig, width="stretch")
    with right:
        st.subheader("Bảng kiểm kê và khoảng ngày")
        inventory = make_inventory(counts)
        inventory["Số bản ghi"] = inventory["Số bản ghi"].map(lambda x: f"{int(x):,}")
        st.dataframe(inventory, width="stretch", hide_index=True)
        st.caption("Khoảng ngày là mốc quan sát trong các CSV hiện có; không đồng nghĩa đã thu thập đầy đủ toàn bộ lịch sử.")

    st.subheader("Từ Giai đoạn 1 đến Giai đoạn 2")
    a, b = st.columns(2)
    with a:
        st.markdown("**Giai đoạn 1 — thử nghiệm pipeline**")
        st.write("Thu thập quy mô nhỏ để kiểm tra endpoint, tham số API, cách lưu CSV và quy trình xử lý dữ liệu.")
        st.caption("Số liệu tham chiếu từ lần chạy ban đầu; không cộng vào tổng Giai đoạn 2.")
    with b:
        st.markdown("**Giai đoạn 2 — mở rộng và so sánh**")
        st.write(f"Mở rộng lên {counts['Repositories']:,} repositories và phân tích commits, issues, pull requests cùng hồ sơ developer.")

# PAGE 2: Vietnam vs international
elif page == "So sánh Việt Nam – quốc tế":
    st.header("2. So sánh Việt Nam và quốc tế đã nhận diện")
    st.caption("Nhóm quốc tế đã nhận diện không đại diện cho toàn bộ cộng đồng GitHub quốc tế.")
    compare = read_csv("vietnam_vs_international_summary.csv")
    if compare.empty:
        st.error(f"Chưa đọc được vietnam_vs_international_summary.csv. Kiểm tra file tại: {PROCESSED}")
    else:
        c_type = get_col(compare, "activity_type")
        c_group = get_col(compare, "group")
        c_records = get_col(compare, "records")
        c_authors = get_col(compare, "unique_authors")
        c_repos = get_col(compare, "repositories")
        if not (c_type and c_group and c_records):
            st.error("CSV so sánh chưa có đủ cột activity_type, group, records. Các cột đọc được: " + ", ".join(map(str, compare.columns)))
        else:
            data = compare.copy()
            data["Loại hoạt động"] = data[c_type].map(vn_label)
            data["Nhóm"] = data[c_group].map(vn_label)
            data["Số bản ghi"] = to_num(data[c_records]).astype(int)
            data = data[data[c_type].isin(["Issues", "Pull Requests"]) & data[c_group].isin(["Vietnam", "International"])].copy()
            if data.empty:
                st.warning("CSV đã đọc được nhưng không có dòng mang group=Vietnam/International và activity_type=Issues/Pull Requests.")
                st.write("Các giá trị group hiện có:", sorted(compare[c_group].dropna().astype(str).unique().tolist()))
                st.write("Các giá trị activity_type hiện có:", sorted(compare[c_type].dropna().astype(str).unique().tolist()))
            else:
                order_type = ["Issues", "Pull Requests"]
                data["Loại hoạt động"] = pd.Categorical(data["Loại hoạt động"], categories=[vn_label(x) for x in order_type], ordered=True)
                fig = px.bar(data, x="Số bản ghi", y="Loại hoạt động", color="Nhóm", barmode="group", orientation="h",
                             text="Số bản ghi", color_discrete_map={"Việt Nam": "#dc2626", "Quốc tế đã nhận diện": "#2563eb"})
                fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
                fig.update_layout(height=420, margin=dict(l=5, r=50, t=10, b=5), xaxis_title="Số bản ghi", yaxis_title="", legend_title="Nhóm")
                st.plotly_chart(fig, width="stretch")
                display = pd.DataFrame({"Loại hoạt động": data["Loại hoạt động"].astype(str), "Nhóm": data["Nhóm"], "Số bản ghi": data["Số bản ghi"]})
                if c_authors:
                    display["Tác giả duy nhất"] = to_num(data[c_authors]).astype(int).values
                if c_repos:
                    display["Số repository"] = to_num(data[c_repos]).astype(int).values
                st.subheader("Bảng số liệu đối chiếu")
                st.dataframe(display, width="stretch", hide_index=True)
                for activity in order_type:
                    group_rows = data[data[c_type] == activity]
                    vn = group_rows[group_rows[c_group] == "Vietnam"]["Số bản ghi"].sum()
                    intl = group_rows[group_rows[c_group] == "International"]["Số bản ghi"].sum()
                    if vn + intl > 0:
                        st.write(f"**{vn_label(activity)}:** nhóm Việt Nam chiếm {vn / (vn + intl) * 100:.2f}% trong hai nhóm đã nhận diện.")
    st.warning("Location được người dùng tự khai báo. Các số liệu phản ánh dữ liệu phân loại được, không đại diện đầy đủ cho toàn bộ GitHub.")

# PAGE 3: country distribution
elif page == "Phân bố theo quốc gia":
    st.header("3. Phân bố hoạt động theo quốc gia/vùng")
    st.caption("Thống kê theo thông tin location có thể liên kết và chuẩn hóa từ hồ sơ developer; không đại diện cho toàn bộ GitHub.")
    by_country = read_csv("activity_by_country.csv")
    if by_country.empty:
        st.error(f"Chưa đọc được activity_by_country.csv. Hãy kiểm tra file tại: {PROCESSED}")
        st.info("Ứng dụng cần file data/processed/activity_by_country.csv để hiển thị tên từng quốc gia.")
    else:
        country_col = get_col(by_country, "country_or_region", "country", "country_region", "country_or_location")
        activity_count_col = get_col(by_country, "records", "activity_records", "total_records", "record_count", "count", "rows")
        if not country_col or not activity_count_col:
            st.error("CSV phân bố quốc gia chưa có cột nhận diện được. Cần country_or_region và records (hoặc cột số tương đương).")
            st.write("Các cột hiện có:", list(by_country.columns))
        else:
            countries = by_country[[country_col, activity_count_col]].copy()
            countries.columns = ["Quốc gia/vùng", "Số bản ghi hoạt động"]
            countries["Quốc gia/vùng"] = countries["Quốc gia/vùng"].astype("string").str.strip()
            countries["Số bản ghi hoạt động"] = to_num(countries["Số bản ghi hoạt động"]).astype(int)
            countries = countries.dropna(subset=["Quốc gia/vùng"])
            countries = countries[countries["Quốc gia/vùng"].str.len() > 0]
            # Exclude categories that do not identify a country; show them separately below if present.
            unknown_labels = {
                "unprofiled", "unknown", "other/unknown", "unresolved location",
                "no author login", "non-user account", "unfiled", "none", "nan"
            }
            normalized = countries["Quốc gia/vùng"].str.casefold()
            known = countries[~normalized.isin(unknown_labels)].copy()
            known = known.groupby("Quốc gia/vùng", as_index=False)["Số bản ghi hoạt động"].sum()
            known = known.sort_values("Số bản ghi hoạt động", ascending=False)
            vn_mask = known["Quốc gia/vùng"].str.casefold().isin({"vietnam", "viet nam", "việt nam"})
            total_known = int(known["Số bản ghi hoạt động"].sum())
            vn_count = int(known.loc[vn_mask, "Số bản ghi hoạt động"].sum())
            k1, k2, k3 = st.columns(3)
            k1.metric("Quốc gia/vùng được nhận diện", f"{len(known):,}")
            k2.metric("Hoạt động gắn với Việt Nam", f"{vn_count:,}")
            k3.metric("Tổng hoạt động ở nhóm đã nhận diện", f"{total_known:,}")
            top_n = st.selectbox("Số quốc gia/vùng muốn xem", [10, 15, 20, 30, 50], index=1)
            top = known.head(top_n).copy()
            # Keep the selected list sorted for a horizontal bar chart; highlight Vietnam separately.
            top = top.sort_values("Số bản ghi hoạt động", ascending=True)
            top["Nhóm màu"] = top["Quốc gia/vùng"].apply(
                lambda x: "Việt Nam" if str(x).casefold() in {"vietnam", "viet nam", "việt nam"} else "Các quốc gia/vùng khác"
            )
            fig_country = px.bar(
                top, x="Số bản ghi hoạt động", y="Quốc gia/vùng", orientation="h",
                color="Nhóm màu", text="Số bản ghi hoạt động",
                color_discrete_map={"Việt Nam": "#dc2626", "Các quốc gia/vùng khác": "#2563eb"},
                title=f"Top {top_n} quốc gia/vùng theo số bản ghi hoạt động đã nhận diện",
            )
            fig_country.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
            fig_country.update_layout(height=max(400, 28 * len(top) + 130), margin=dict(l=5, r=50, t=55, b=5), xaxis_title="Số bản ghi hoạt động", yaxis_title="", legend_title="")
            st.plotly_chart(fig_country, width="stretch")
            table_country = known.sort_values("Số bản ghi hoạt động", ascending=False).copy()
            table_country["Tỷ trọng trong nhóm đã nhận diện"] = (
                table_country["Số bản ghi hoạt động"] / total_known * 100 if total_known else 0
            )
            table_country["Tỷ trọng trong nhóm đã nhận diện"] = table_country["Tỷ trọng trong nhóm đã nhận diện"].map(lambda x: f"{x:.2f}%")
            st.subheader("Bảng phân bố theo quốc gia/vùng")
            st.dataframe(table_country, width="stretch", hide_index=True)
            unknown = countries[normalized.isin(unknown_labels)].groupby("Quốc gia/vùng", as_index=False)["Số bản ghi hoạt động"].sum().sort_values("Số bản ghi hoạt động", ascending=False)
            if not unknown.empty:
                with st.expander("Xem thêm các nhóm chưa xác định quốc gia"):
                    st.dataframe(unknown, width="stretch", hide_index=True)
            st.info("Các số liệu đếm bản ghi hoạt động được phân loại theo location; một developer có thể có nhiều bản ghi. Không diễn giải đây là số developer duy nhất hoặc tổng hoạt động của toàn bộ quốc gia.")

# PAGE 4: coverage
elif page == "Độ phủ dữ liệu":
    st.header("4. Độ phủ và chất lượng dữ liệu")
    coverage = read_csv("country_activity_coverage.csv")
    if coverage.empty:
        st.error(f"Chưa đọc được country_activity_coverage.csv. Kiểm tra file tại: {PROCESSED}")
    else:
        c_table = get_col(coverage, "table")
        c_total = get_col(coverage, "total_rows")
        c_known = get_col(coverage, "rows_with_recognized_country")
        c_unknown = get_col(coverage, "rows_unknown_or_unprofiled")
        c_vn = get_col(coverage, "rows_vietnam")
        if not all([c_table, c_total, c_known, c_unknown]):
            st.error("CSV độ phủ thiếu cột cần thiết. Các cột đọc được: " + ", ".join(map(str, coverage.columns)))
        else:
            cov = coverage.copy()
            cov["Hạng mục"] = cov[c_table].map(vn_label)
            cov["Tổng số bản ghi"] = to_num(cov[c_total]).astype(int)
            cov["Đã nhận diện quốc gia"] = to_num(cov[c_known]).astype(int)
            cov["Chưa xác định/chưa có hồ sơ"] = to_num(cov[c_unknown]).astype(int)
            cov["Tỷ lệ nhận diện"] = cov["Đã nhận diện quốc gia"] / cov["Tổng số bản ghi"].replace(0, pd.NA) * 100
            plot_data = cov.melt(id_vars=["Hạng mục"], value_vars=["Đã nhận diện quốc gia", "Chưa xác định/chưa có hồ sơ"], var_name="Trạng thái", value_name="Số bản ghi")
            fig = px.bar(plot_data, x="Số bản ghi", y="Hạng mục", color="Trạng thái", barmode="stack", orientation="h",
                         title="Độ phủ nhận diện quốc gia theo hạng mục dữ liệu",
                         color_discrete_map={"Đã nhận diện quốc gia": "#0d9488", "Chưa xác định/chưa có hồ sơ": "#cbd5e1"})
            fig.update_layout(height=380, margin=dict(l=5, r=25, t=45, b=5), xaxis_title="Số bản ghi", yaxis_title="", legend_title="")
            st.plotly_chart(fig, width="stretch")
            out = pd.DataFrame({
                "Hạng mục": cov["Hạng mục"],
                "Tổng số bản ghi": cov["Tổng số bản ghi"],
                "Đã nhận diện quốc gia": cov["Đã nhận diện quốc gia"],
                "Chưa xác định/chưa có hồ sơ": cov["Chưa xác định/chưa có hồ sơ"],
                "Tỷ lệ nhận diện": cov["Tỷ lệ nhận diện"].map(lambda x: f"{x:.2f}%"),
            })
            if c_vn:
                out["Trong đó — Việt Nam"] = to_num(cov[c_vn]).astype(int)
            st.dataframe(out, width="stretch", hide_index=True)
    st.info("Location là thông tin tự khai báo. Không trùng khóa trong CSV không đồng nghĩa đã thu thập đầy đủ toàn bộ lịch sử.")

# PAGE 5: methods
elif page == "Phương pháp & câu hỏi":
    st.header("5. Phương pháp và câu hỏi nghiên cứu")
    st.subheader("Quy trình từ Giai đoạn 1 đến Giai đoạn 2")
    st.markdown("""
    1. **Giai đoạn 1 — thử nghiệm:** dùng tập nhỏ để kiểm tra endpoint GitHub REST API, tham số phân trang, lưu CSV và xử lý dữ liệu.
    2. **Giai đoạn 2 — mở rộng:** tăng danh sách repository; thu thập Repositories, Commits, Issues, Pull Requests và hồ sơ Developer.
    3. **Kiểm kê chất lượng:** kiểm tra khóa định danh, giá trị thiếu/trùng và khoảng ngày quan sát được.
    4. **So sánh:** đối chiếu bản ghi, tác giả duy nhất và repository của Việt Nam với nhóm quốc tế đã nhận diện.
    5. **Trình bày:** Power BI và ứng dụng Streamlit.
    """)
    st.subheader("Câu hỏi nghiên cứu")
    st.markdown("""
    - Thu thập được bao nhiêu bản ghi cho từng hạng mục, chứa những trường gì và có khoảng ngày quan sát nào?
    - Trong những bản ghi xác định được quốc gia, quy mô Issues và Pull Requests của Việt Nam khác nhóm quốc tế đã nhận diện ra sao?
    - Số tác giả duy nhất và số repository của hai nhóm khác nhau như thế nào?
    - Dữ liệu thiếu location hoặc chưa liên kết được Developer profile giới hạn kết luận ra sao?
    """)
    st.subheader("Giới hạn cần công bố")
    st.markdown("""
    - Location do người dùng tự khai báo, chưa được xác minh độc lập.
    - “Quốc tế đã nhận diện” không đại diện cho toàn bộ hoạt động quốc tế trên GitHub.
    - Commits hiện quan sát từ năm 2024, không phủ toàn bộ giai đoạn mục tiêu từ năm 2020.
    - Số bản ghi hoạt động không đồng nghĩa số developer duy nhất.
    """)

# PAGE 2: repository-centric summary
elif page == "Tổng hợp theo Repository":
    st.header("2. Tổng hợp theo Repository")
    st.caption("Mỗi dòng tương ứng một repository. Commits, Issues và Pull Requests được đếm riêng rồi ghép vào bảng metadata repository.")
    summary = read_csv("repository_summary.csv")
    if summary.empty:
        st.error("Chưa đọc được repository_summary.csv trong data/processed. Kiểm tra file ở nhánh streamlit-final-dashboard.")
    else:
        # Keep the repository grain explicit and prevent accidental fan-out.
        if "repo_id" in summary.columns:
            summary["repo_id"] = summary["repo_id"].astype("string")
        for col in ["stars", "forks", "open_issues", "commits_observed_count", "issues_observed_count", "pull_requests_observed_count"]:
            if col in summary.columns:
                summary[col] = to_num(summary[col]).astype("int64")
        if "full_name" in summary.columns:
            summary = summary.drop_duplicates(subset=["repo_id"] if "repo_id" in summary.columns else ["full_name"], keep="first")
        commits_col = "commits_observed_count"
        issues_col = "issues_observed_count"
        prs_col = "pull_requests_observed_count"
        kpi = st.columns(4)
        kpi[0].metric("Repositories", f"{summary['repo_id'].nunique() if 'repo_id' in summary.columns else summary['full_name'].nunique():,}")
        kpi[1].metric("Commits quan sát", f"{int(summary[commits_col].sum()):,}")
        kpi[2].metric("Issues quan sát", f"{int(summary[issues_col].sum()):,}")
        kpi[3].metric("Pull Requests quan sát", f"{int(summary[prs_col].sum()):,}")
        st.warning("Các count là số dòng đã có trong CSV. Nhiều repository còn Partial/Pending; count bằng 0 ở trạng thái chưa hoàn tất không có nghĩa repository thật sự không có hoạt động.")
        st.subheader("Tìm kiếm và lọc repository")
        f1, f2, f3, f4 = st.columns([2.0, 1.1, 1.0, 1.2])
        with f1:
            search = st.text_input("Tên repository hoặc owner", placeholder="Ví dụ: openclaw/openclaw")
        with f2:
            langs = ["Tất cả"] + sorted(summary["language"].fillna("Unknown").astype(str).replace("", "Unknown").unique().tolist()) if "language" in summary.columns else ["Tất cả"]
            lang_filter = st.selectbox("Ngôn ngữ", langs)
        with f3:
            sort_metric = st.selectbox("Sắp xếp theo", ["stars", "forks", "commits_observed_count", "issues_observed_count", "pull_requests_observed_count"], format_func=lambda v: {"stars":"Stars", "forks":"Forks", "commits_observed_count":"Commits", "issues_observed_count":"Issues", "pull_requests_observed_count":"Pull Requests"}[v])
        with f4:
            min_stars = st.number_input("Stars tối thiểu", min_value=0, max_value=int(summary["stars"].max()) if "stars" in summary.columns and not summary.empty else 0, value=0, step=100)
        view = summary.copy()
        if search:
            name_series = view.get("full_name", pd.Series("", index=view.index)).fillna("").astype(str)
            owner_series = view.get("owner_login", pd.Series("", index=view.index)).fillna("").astype(str)
            view = view[name_series.str.contains(search, case=False, regex=False) | owner_series.str.contains(search, case=False, regex=False)]
        if lang_filter != "Tất cả" and "language" in view.columns:
            view = view[view["language"].fillna("Unknown").astype(str).replace("", "Unknown") == lang_filter]
        if "stars" in view.columns:
            view = view[view["stars"] >= min_stars]
        view = view.sort_values(sort_metric, ascending=False, na_position="last")
        st.caption(f"Đang hiển thị {len(view):,} / {len(summary):,} repository")
        table_cols = [c for c in [
            "repo_id", "full_name", "owner_login", "owner_type", "language", "stars", "forks", "open_issues",
            "commits_observed_count", "commits_collection_status", "issues_observed_count", "issues_collection_status",
            "pull_requests_observed_count", "pull_requests_collection_status", "created_at", "updated_at", "html_url"
        ] if c in view.columns]
        st.dataframe(view[table_cols], width="stretch", hide_index=True, height=470,
                     column_config={"html_url": st.column_config.LinkColumn("Repository URL")})
        st.download_button("Tải bảng tổng hợp đã lọc (CSV)", data=view[table_cols].to_csv(index=False).encode("utf-8-sig"),
                           file_name="repository_summary_filtered.csv", mime="text/csv")
        st.subheader("Hoạt động theo repository")
        m1, m2 = st.columns([1, 2])
        with m1:
            activity_metric = st.selectbox("Chỉ số hoạt động", ["commits_observed_count", "issues_observed_count", "pull_requests_observed_count"],
                format_func=lambda v: {"commits_observed_count":"Commits quan sát", "issues_observed_count":"Issues quan sát", "pull_requests_observed_count":"Pull Requests quan sát"}[v])
            top_n = st.slider("Số repository trên biểu đồ", min_value=10, max_value=50, value=20, step=5)
        status_col = {"commits_observed_count":"commits_collection_status", "issues_observed_count":"issues_collection_status", "pull_requests_observed_count":"pull_requests_collection_status"}[activity_metric]
        with m2:
            top = view.sort_values(activity_metric, ascending=False).head(top_n).copy()
            if not top.empty:
                fig = px.bar(top.sort_values(activity_metric), x=activity_metric, y="full_name", orientation="h",
                    color=status_col if status_col in top.columns else None, hover_data=[c for c in ["stars", "forks", "language", "owner_login"] if c in top.columns],
                    title="Top repository theo số bản ghi đã thu thập")
                fig.update_layout(height=max(450, 26 * len(top) + 100), margin=dict(l=5, r=20, t=55, b=5), xaxis_title="Số bản ghi", yaxis_title="")
                st.plotly_chart(fig, width="stretch")
        st.subheader("Giai đoạn 1 và Giai đoạn 2 — kiểm kê bản ghi")
        stage1_files = {"Repositories":"repositories.csv", "Commits":"commits.csv", "Issues":"issues.csv"}
        stage1_counts = {}
        for label, filename in stage1_files.items():
            path = ROOT / "Ass_GD1" / filename
            if path.is_file():
                try:
                    stage1_counts[label] = len(pd.read_csv(path, low_memory=False, encoding="utf-8-sig"))
                except Exception:
                    stage1_counts[label] = None
            else:
                stage1_counts[label] = None
        stage2_counts = {
            "Repositories": int(summary["repo_id"].nunique()) if "repo_id" in summary.columns else len(summary),
            "Commits": int(summary[commits_col].sum()),
            "Issues": int(summary[issues_col].sum()),
            "Pull Requests": int(summary[prs_col].sum()),
        }
        comp_rows = []
        for label in ["Repositories", "Commits", "Issues", "Pull Requests"]:
            old_count = stage1_counts.get(label)
            comp_rows.append({
                "Dataset": label,
                "Giai đoạn 1 - số dòng CSV": f"{old_count:,}" if old_count is not None else "Không có file",
                "Giai đoạn 2 - số dòng quan sát": f"{stage2_counts[label]:,}",
                "Ghi chú": "Pull Requests được bổ sung ở Giai đoạn 2" if label == "Pull Requests" else "Các số đếm phản ánh file CSV hiện có"
            })
        st.dataframe(pd.DataFrame(comp_rows), width="stretch", hide_index=True)
        st.info("Bảng này giúp trình bày quy mô dữ liệu qua hai giai đoạn. Không dùng chênh lệch trực tiếp làm tăng trưởng nếu bộ dữ liệu hoặc quy tắc crawl giữa hai giai đoạn khác nhau.")

st.divider()
st.caption("GitHub Developer Analytics · Đối chiếu số liệu với các CSV audit trước khi nộp.")
