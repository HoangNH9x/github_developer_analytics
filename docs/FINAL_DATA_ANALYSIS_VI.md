# Phân tích dữ liệu Final — GitHub Developer Analytics

**Nguồn:** processed CSV do nhóm cung cấp trong gói Final_processed_dataset.zip.  
**Khoảng hoạt động:** 2020-01-01 đến hết 2026-10-20.  
**Nguyên tắc mô hình:** Repository là bảng cha; Commits, Issues, Pull Requests là các bảng con liên kết bằng `repository_id`.

## 1. Tóm tắt dữ liệu

| Chỉ số | Kết quả |
|---|---:|
| Repository duy nhất | 47 |
| Commits | 46.811 |
| Issues tạo mới | 18.762 |
| Pull Requests tạo mới | 32.415 |
| Tổng activity records | 97.988 |
| Owner-country nhận diện | 45/47 (95,7%) |
| Duplicates removed: commits/issues/PR | 0 / 0 / 0 |
| Collection errors | 0 dòng |

Tất cả 47 repository có trạng thái `COMPLETE` hoặc `ZERO_CONFIRMED` cho từng metric. Cụ thể: Commits 43 COMPLETE + 4 ZERO_CONFIRMED; Issues 38 COMPLETE + 9 ZERO_CONFIRMED; PRs 41 COMPLETE + 6 ZERO_CONFIRMED. Đây là trạng thái của bộ CSV hiện tại, không phải bằng chứng rằng mẫu đại diện toàn GitHub.

## 2. Thành phần mẫu

| Nguồn chọn mẫu | Repository | Activity records | Tỷ lệ activity |
|---|---:|---:|---:|
| Global seed ban đầu | 3 | 49.558 | 50,6% |
| Global owner discovery | 30 | 44.946 | 45,9% |
| Vietnam owner discovery | 14 | 3.484 | 3,6% |

Đây là mẫu có chủ đích, không phải mẫu ngẫu nhiên. Global owner discovery giới hạn khoảng Stars và ngôn ngữ; Vietnam owner discovery dựa trên location công khai của owner. Tiêu chí chọn mẫu giữa hai nhóm chưa hoàn toàn đồng nhất.

## 3. Ba insights chính

### Insight 1 — Hoạt động tập trung vào một repository và hai owner chưa xác định country

`coder/coder` có 47.493 sự kiện, tương đương 48,47% tổng activity. Hai repository chưa xác định country owner có tổng cộng 47.970 sự kiện (48,95%). Tổng activity toàn mẫu vì thế bị chi phối mạnh bởi vài repository lớn. Giữ nhóm Unknown riêng và hiển thị cả tổng lẫn trung bình/repository khi phân tích.

### Insight 2 — Khác biệt mô tả giữa Việt Nam và các quốc gia khác đã nhận diện

| Nhóm | Repos | Commits (TB/repo) | Issues (TB/repo) | PRs (TB/repo) | Tổng activity TB/repo |
|---|---:|---:|---:|---:|---:|
| Vietnam | 14 | 2.640 (188,6) | 499 (35,6) | 345 (24,6) | 248,9 |
| Other recognized countries | 31 | 26.752 (863,0) | 10.705 (345,3) | 9.077 (292,8) | 1.501,1 |
| Unknown / unresolved | 2 | 17.419 (8.709,5) | 7.558 (3.779,0) | 22.993 (11.496,5) | 23.985,0 |

Trong mẫu, trung bình activity/repository của nhóm quốc tế đã nhận diện cao khoảng 6,03 lần nhóm Việt Nam. Đây là mô tả của mẫu đã chọn, **không** chứng minh năng suất quốc gia; khác biệt về tiêu chí lấy mẫu, loại dự án, độ phổ biến và quy mô repository ảnh hưởng kết quả. Nhóm Unknown được loại khỏi phép so sánh chính.

### Insight 3 — Đỉnh theo tháng khác nhau theo loại sự kiện

- Commits cao nhất: tháng 03/2026, 1.529.
- Pull Requests cao nhất: tháng 03/2026, 1.579.
- Issues tạo mới cao nhất: tháng 06/2022, 561.

Tháng 10/2026 chỉ có dữ liệu đến ngày 20/10, nên là tháng chưa đầy đủ. Các đỉnh phản ánh mẫu 47 repository, không đại diện tất cả GitHub.

## 4. Chất lượng và mô hình dữ liệu

- `repository_country_metrics.csv`: 47 dòng, 47 `repository_id` duy nhất; là bảng summary ở grain repository.
- `commits.csv`, `issues.csv`, `pull_requests.csv`: bảng con, khóa sự kiện lần lượt là `commit_sha`, `issue_id`, `pr_id`; mỗi record con liên kết về Repository qua `repository_id`.
- Không JOIN trực tiếp ba bảng con với nhau trước tổng hợp vì quan hệ nhiều-nhiều có thể nhân bản sự kiện.
- Stars/Forks là snapshot lúc crawl, không phải lượng tăng trong giai đoạn.
- Owner-country được suy ra từ public profile location tự khai báo; không phải vị trí được xác minh độc lập và không tương đương author-country.
- `developer_activity_summary.csv` có 7.946 login và bao gồm bot như `dependabot[bot]`; phải tách bot nếu xây leaderboard dành riêng cho người.

## 5. Khuyến nghị sử dụng trong Final

1. Power BI trang Overview: KPI, top repositories, source/sample coverage và metric status.
2. Trang Monthly Trends: Commit, Issue, PR theo tháng; ghi rõ tháng cuối chỉ đến 20/10/2026.
3. Trang Vietnam vs International: so sánh Vietnam với Other recognized countries, giữ Unknown riêng và hiển thị cả số repository cùng trung bình/repo.
4. Streamlit và Power BI phải dùng cùng phiên bản processed CSV. Không diễn giải tương quan mô tả như quan hệ nhân quả.
5. Công bố giới hạn chọn mẫu và ảnh hưởng tập trung của `coder/coder` khi bảo vệ.

## 6. Kết luận

Bộ dữ liệu hiện có 47 repository và 97.988 activity records, với khóa định danh duy nhất và trạng thái metric được xác nhận trong audit. Đây là cơ sở phù hợp cho dashboard mô tả và minh họa pipeline API, xử lý dữ liệu và mô hình cha–con; kết luận Việt Nam–quốc tế cần ở mức mô tả do tiêu chí lấy mẫu khác nhau.

**Tài liệu API:** https://docs.github.com/en/rest
