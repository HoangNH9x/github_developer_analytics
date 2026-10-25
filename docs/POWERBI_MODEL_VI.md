# Thiết kế Power BI Final — GitHub Developer Analytics

Tài liệu này hướng dẫn dựng semantic model sau khi canonical CSV đã được crawl và audit. Không sử dụng dữ liệu trong data/processed cũ làm nguồn thay thế cho data/processed/canonical.

## 1. Nguồn dữ liệu

Nạp các file:
- repository_country_metrics.csv — một dòng cho mỗi repository; bảng trung tâm cho KPI, danh sách repo và so sánh owner-country.
- monthly_activity.csv — một dòng cho mỗi country + month; xu hướng đã loại repository có metric chưa hoàn chỉnh.
- vietnam_vs_other_countries_comparison.csv — bảng so sánh 3 nhóm đã được tổng hợp từ repository metrics.
- country_repository_comparison.csv — bảng phân tích sâu theo từng country.
- developer_activity_summary.csv — xếp hạng contributor theo các record hoạt động đã thu thập hoàn chỉnh.
- data_quality_report.csv và deduplication_audit.csv — kiểm toán coverage và trùng lặp.

Không nối các bảng event-level Commit × Issue × PR với nhau trước khi tổng hợp. Join nhiều-nhiều trực tiếp có thể nhân bản activity.

## 2. Mô hình quan hệ đề xuất

### Quy tắc cha–con bắt buộc
`DimRepository` là bảng cha (một dòng cho mỗi `repository_id`). Các bảng chi tiết `FactCommits`, `FactIssues` và `FactPullRequests` là bảng con, mỗi bảng có nhiều dòng trên một repository và giữ `repository_id` làm khóa ngoại.

```text
DimRepository[repository_id] 1 ─── * FactCommits[repository_id]
DimRepository[repository_id] 1 ─── * FactIssues[repository_id]
DimRepository[repository_id] 1 ─── * FactPullRequests[repository_id]
```

Các file raw canonical `commits.csv`, `issues.csv` và `pull_requests.csv` là nguồn bản ghi con; mỗi file có khóa sự kiện riêng (`commit_sha`, `issue_id`, `pr_id`). Metadata, owner-country, Stars/Forks snapshot và sample_source thuộc bảng cha.

### Cách dựng model an toàn
- Tạo `DimRepository` từ `repository_country_metrics.csv`, giữ một dòng duy nhất cho mỗi `repository_id` và các thuộc tính repo/owner.
- Dùng `repository_country_metrics.csv` như bảng summary cấp repository cho KPI snapshot và các counts đã kiểm định. Không nối summary và mọi bảng chi tiết vào cùng một visual để tính tổng lần nữa.
- Nếu cần drill-through tới từng sự kiện, nạp các bảng con đã khử trùng (`commits.csv`, `issues.csv`, `pull_requests.csv`) và tạo ba quan hệ 1:* một chiều từ `DimRepository`. Không tạo quan hệ trực tiếp giữa các bảng con.
- Dùng `monthly_activity.csv` cho trend; dùng `developer_activity_summary.csv` cho contributor. Hai bảng này là bảng tổng hợp riêng, không được cộng chồng với bảng sự kiện con.
- Dùng `country_repository_comparison.csv` và `vietnam_vs_other_countries_comparison.csv` cho visual tổng hợp; không join chúng vào bảng sự kiện.
- Có thể tạo `DimCountry` và `DimMonth` riêng khi cần star schema mở rộng; tránh các quan hệ many-to-many và quan hệ hai chiều không cần thiết.

## 3. Các measures DAX mẫu

Các ví dụ giả định tên bảng trung tâm là repository_country_metrics. Nếu Power BI tự sửa tên, đổi sang đúng tên trong model.

### KPI repository và snapshot

~~~dax
Total Repositories =
DISTINCTCOUNT ( repository_country_metrics[repository_id] )

Stars Snapshot =
SUM ( repository_country_metrics[stars_snapshot] )

Forks Snapshot =
SUM ( repository_country_metrics[forks_snapshot] )
~~~

### Commits, Issues, PRs chỉ tính metric hoàn chỉnh

~~~dax
Repositories With Complete Commits =
CALCULATE (
    DISTINCTCOUNT ( repository_country_metrics[repository_id] ),
    repository_country_metrics[commits_status] IN { "COMPLETE", "ZERO_CONFIRMED" }
)

Commits Total Confirmed =
CALCULATE (
    SUM ( repository_country_metrics[commits_count_window] ),
    repository_country_metrics[commits_status] IN { "COMPLETE", "ZERO_CONFIRMED" }
)

Issues Created Total Confirmed =
CALCULATE (
    SUM ( repository_country_metrics[issues_created_count_window] ),
    repository_country_metrics[issues_status] IN { "COMPLETE", "ZERO_CONFIRMED" }
)

Pull Requests Created Total Confirmed =
CALCULATE (
    SUM ( repository_country_metrics[prs_created_count_window] ),
    repository_country_metrics[prs_status] IN { "COMPLETE", "ZERO_CONFIRMED" }
)

Commits Collection Coverage % =
DIVIDE ( [Repositories With Complete Commits], [Total Repositories] )
~~~

Tạo measures tương tự cho coverage Issues và PRs bằng cách thay status column.

### Trung bình trên repository có dữ liệu hoàn chỉnh

~~~dax
Average Commits Per Complete Repository =
DIVIDE ( [Commits Total Confirmed], [Repositories With Complete Commits] )
~~~

Không dùng AVERAGE trực tiếp trên tất cả dòng nếu có metric PARTIAL, ERROR hoặc NOT_RUN. Các giá trị này trong CSV để trống; coverage cũng phải hiện cạnh KPI.

### Thống kê Việt Nam

~~~dax
Vietnam Repositories =
CALCULATE (
    [Total Repositories],
    repository_country_metrics[owner_country] = "Vietnam"
)

Vietnam Commits Confirmed =
CALCULATE (
    [Commits Total Confirmed],
    repository_country_metrics[owner_country] = "Vietnam"
)
~~~

Để so sánh phần quốc tế chính xác, giữ Unknown / unresolved thành nhóm riêng; không gộp unknown vào Other recognized countries.

## 4. Bố cục báo cáo 3 trang

### Trang 1 — Tổng quan
- Cards: Total Repositories, Stars Snapshot, Forks Snapshot, Commits Total Confirmed, Issues Created Total Confirmed, Pull Requests Created Total Confirmed.
- KPI phụ: Commits / Issues / PRs Collection Coverage %.
- Bar chart Top 10 repositories theo Stars.
- Bar chart số repository theo owner-country hoặc language.
- Table repository có hyperlink và status columns.

### Trang 2 — Xu hướng thời gian
- Line chart: commits, issues created, PRs created theo activity_month.
- Slicer owner-country (Vietnam, quốc gia cụ thể hoặc Unknown).
- Hiện số repository covered cho từng metric để người xem không hiểu nhầm độ phủ khác nhau.
- Không nối Stars/Forks snapshot vào đường xu hướng theo tháng.

### Trang 3 — Việt Nam và quốc tế
- Bar chart nhóm: Vietnam, Other recognized countries, Unknown / unresolved.
- Table các chỉ số: repository count, Stars/Forks snapshot, total/average activity trên repo complete, coverage từng metric.
- Visual theo country owner riêng với số lượng repo và coverage.
- Textbox ghi rõ location là public profile tự khai báo và mẫu không đại diện ngẫu nhiên toàn GitHub.

## 5. Kiểm tra trước khi nộp

- Repository count trong Power BI khớp số repository_id duy nhất trong canonical CSV.
- Các tổng activity không vượt qua bộ dữ liệu event-level đã thu thập; các metric chưa hoàn chỉnh bị loại khỏi tổng.
- Một repository không bị nhân đôi sau relationship.
- Stars/Forks được gắn nhãn snapshot.
- Unknown country không bị coi như Vietnam hoặc Other recognized.
- Word, PowerPoint, Power BI và Streamlit dùng cùng phiên bản các canonical processed CSV.
- Power Query không dùng đường dẫn tuyệt đối tới máy cá nhân; refresh thành công trên máy khác.
