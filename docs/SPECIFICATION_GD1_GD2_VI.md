# Tài liệu đặc tả — GitHub Developer Analytics (Giai đoạn 1 và 2)

**Phiên bản tài liệu:** 26/10/2026  
**Khoảng thời gian hoạt động:** 01/01/2020–20/10/2026  
**Nguồn dữ liệu:** GitHub REST API, dữ liệu công khai.

## 1. Mô tả nguồn dữ liệu thu thập (Giai đoạn 1)

### 1.1 Mục tiêu

Giai đoạn 1 thiết lập cách thu thập dữ liệu GitHub bằng Python/API thay vì nhập thủ công. Mục tiêu là xác định repository làm đối tượng trung tâm, lấy dữ liệu hoạt động có thể liên kết về repository, lưu CSV và kiểm tra dữ liệu trước khi mở rộng ở Giai đoạn 2.

### 1.2 Nguồn dữ liệu

Đề tài lấy dữ liệu công khai từ GitHub REST API; không sử dụng dữ liệu Kaggle. Repository được chọn từ danh sách seed ban đầu và được bổ sung trong Giai đoạn 2 bằng tìm kiếm repository/owner công khai. Các trường profile như location do owner tự khai báo; hệ thống chỉ phân giải quốc gia khi nhận diện đủ rõ và giữ Unknown nếu không chắc chắn.

| Nhóm dữ liệu | Endpoint chính | Trường / mục đích |
|---|---|---|
| Repository metadata | GET /repos/{owner}/{repo} | ID, full_name, owner, mô tả, ngôn ngữ, ngày tạo/cập nhật, Stars, Forks |
| Owner profile | GET /users/{username} hoặc GET /orgs/{org} | owner login/type và location công khai |
| Commits | GET /repos/{owner}/{repo}/commits | SHA, ngày commit và thông tin contributor khi API cung cấp; lọc since/until |
| Issues và Pull Requests | GET /repos/{owner}/{repo}/issues | Lấy danh sách phân trang; nhận diện PR bằng trường pull_request, phân loại riêng và lọc created_at theo kỳ |
| Tìm mẫu | GET /search/repositories và GET /search/users | Tìm repository/owner công khai làm candidate; xác minh owner-country bằng profile |

### 1.3 Khoảng thời gian và định nghĩa

Khoảng nghiên cứu hoạt động là từ 01/01/2020 đến hết 20/10/2026. Commits được lọc bằng thời gian since/until của endpoint. Issues và PR được tách riêng; Issues là issue thông thường, không bao gồm PR. Stars/Forks là snapshot tại thời điểm crawl, không phải số tăng thêm trong cả khoảng nghiên cứu.

Giai đoạn 1 ban đầu ghi nhận xấp xỉ 10 repository, 5.000 commit và 4.950 issue trong các CSV/log thử nghiệm ban đầu. Những số này mô tả quy mô thử nghiệm ban đầu, không được cộng vào hoặc so sánh trực tiếp với Giai đoạn 2 nếu bộ lọc, mẫu và khoảng thời gian không đồng nhất.

## 2. Cách triển khai code để thu thập dữ liệu (phần bổ sung)

### 2.1 Công nghệ

- Python để điều phối thu thập, chuẩn hóa, kiểm tra và tổng hợp dữ liệu.
- requests để gọi GitHub REST API; pandas để xử lý CSV và tổng hợp.
- GitHub Personal Access Token được lưu ở file .env trên máy chạy crawl, không commit lên GitHub.
- Streamlit và Plotly cung cấp giao diện tương tác cho dữ liệu processed.

### 2.2 Luồng xử lý

1. Đọc danh sách repository đầu vào hoặc tìm mẫu owner/repository.
2. Lấy metadata repository và profile công khai của owner.
3. Lấy Commits theo phân trang; lấy Issues và PR qua một luồng phân trang rồi tách theo trường pull_request.
4. Chuẩn hóa trường và ngày; liên kết record với repository bằng repository_id.
5. Khử trùng theo khóa sự kiện, lưu raw CSV và checkpoint để có thể tiếp tục khi bị gián đoạn.
6. Tổng hợp các bảng repository/country/month/contributor; tạo data-quality report, deduplication audit và collection errors.
7. Đọc các bảng processed trong Streamlit và Power BI.

### 2.3 Cách chạy code và nơi xem giải thích chi tiết

Điểm chạy chính là `run_pipeline.py`; trước khi thu thập, dùng `check_github_connection.py` để xác minh token local mà không in token ra màn hình.

1. Tạo môi trường Python và cài thư viện theo `pyproject.toml` / `requirements.txt`.
2. Tạo file `.env` từ `.env.example`, đặt `GITHUB_TOKEN` cục bộ và không đưa file này lên GitHub.
3. Chạy `python check_github_connection.py` để kiểm tra kết nối.
4. Chạy `python run_pipeline.py --seed .\\smoke_test_3_seed.csv --limit-repos 3` cho lượt thử nhỏ.
5. Khi mẫu và cấu hình đã được kiểm tra, mới sử dụng các tham số `--discover-global` và `--discover-vietnam` để mở rộng mẫu.
6. Kiểm tra output trong `data/raw/canonical/` và `data/processed/canonical/`; đọc `data_quality_report.csv`, `deduplication_audit.csv`, và `collection_errors.csv` trước khi phân tích.

Phần giải thích trực quan từng module Python, các bộ lọc và kết quả dashboard được đặt trong Streamlit ở tab **Nguồn dữ liệu & phương pháp**, phù hợp cho phần demo/vấn đáp Giai đoạn 2.

### 2.4 Cấu hình bảo mật và giới hạn API

Token được đọc từ biến môi trường hoặc .env ở máy thu thập. Không đưa token, .env, raw event data hoặc checkpoint lên Streamlit Cloud. Pipeline phân trang theo Link header, có retry/throttling và ghi checkpoint sau khi xử lý từng repository. GitHub áp dụng rate limit riêng cho Search API và REST API thông thường; khi gặp 403/429 cần tuân thủ thông tin retry/reset và không cố vượt qua giới hạn.

### 2.5 Mô hình dữ liệu — Repository là bảng cha

Repository là thực thể cha và dùng repository_id làm khóa chính. Commits, Issues và Pull Requests là các bảng con, mỗi bản ghi con giữ repository_id làm khóa ngoại.

- Bảng cha / summary: repository_country_metrics.csv — đúng một dòng cho mỗi repository_id.
- Bảng con Commits: commits.csv — khóa sự kiện commit_sha.
- Bảng con Issues: issues.csv — khóa sự kiện issue_id.
- Bảng con Pull Requests: pull_requests.csv — khóa sự kiện pr_id.

Quan hệ là 1:N từ Repository đến mỗi bảng con. Không JOIN trực tiếp ba bảng con với nhau trước khi tổng hợp vì quan hệ nhiều-nhiều có thể nhân bản record. Quốc gia owner không phải quốc gia của tác giả commit.

## 3. Kết quả dữ liệu thu thập được (Giai đoạn 2)

### 3.1 Quy mô bộ dữ liệu

| Chỉ số | Kết quả |
|---|---:|
| Repository duy nhất | 47 |
| Commits | 46.811 |
| Issues tạo trong kỳ | 18.762 |
| Pull Requests tạo trong kỳ | 32.415 |
| Tổng hoạt động | 97.988 |
| Owner-country nhận diện được | 45/47 (95,7%) |

### 3.2 Thành phần mẫu

| Nguồn chọn mẫu | Số repository | Số hoạt động | Tỷ lệ hoạt động |
|---|---:|---:|---:|
| Global seed ban đầu | 3 | 49.558 | 50,6% |
| Global owner discovery | 30 | 44.946 | 45,9% |
| Vietnam owner discovery | 14 | 3.484 | 3,6% |
| Tổng | 47 | 97.988 | 100% |

Đây là mẫu có chủ đích, không phải mẫu ngẫu nhiên đại diện cho toàn bộ GitHub. Nhóm global được chọn qua các query tìm repository công khai theo ngôn ngữ và khoảng Stars, sau đó lọc owner-country nhận diện được. Nhóm Vietnam được tìm từ owner có public location được phân giải là Việt Nam. Hai cách chọn mẫu không hoàn toàn đối xứng, nên so sánh quốc gia chỉ mang tính mô tả.

### 3.3 Độ phủ quốc gia

Có 14 repository Việt Nam, 31 repository thuộc các quốc gia khác đã nhận diện và 2 repository Unknown. Tổng cộng 17 nhãn country/nhóm được báo cáo, trong đó các quốc gia phổ biến nhất theo số repository là Việt Nam (14), Hoa Kỳ (6) và Trung Quốc (6). Location được tự khai báo công khai; đây không phải xác minh độc lập về nơi cư trú.

### 3.4 Chất lượng dữ liệu

| Metric | COMPLETE | ZERO_CONFIRMED | Tổng repository |
|---|---:|---:|---:|
| Commits | 43 | 4 | 47 |
| Issues | 38 | 9 | 47 |
| Pull Requests | 41 | 6 | 47 |

Audit ghi nhận 47 repository_id duy nhất, 46.811 commit_sha duy nhất, 18.762 issue_id duy nhất và 32.415 pr_id duy nhất. Số bản ghi trùng bị loại lần lượt là 0 cho Commits, Issues và Pull Requests. collection_errors.csv rỗng tại thời điểm xuất bộ processed hiện tại.

ZERO_CONFIRMED có nghĩa pipeline đã xác nhận không có record thuộc loại đó trong cửa sổ nghiên cứu; không phải lỗi API. Metric PARTIAL/ERROR/NOT_RUN nếu xuất hiện ở lần chạy khác phải được giữ là chưa hoàn chỉnh, không đổi thành số 0.

### 3.5 Ba insight mô tả

**Insight 1 — Hoạt động tập trung vào một số repository.** coder/coder có 47.493 sự kiện, tương đương 48,5% tổng hoạt động. Hai repository chưa nhận diện được quốc gia owner cộng lại có 47.970 sự kiện, tương đương khoảng 49,0% tổng hoạt động. Vì vậy cần trình bày top repository và cả trung bình/repository, không chỉ dùng tổng nhóm.

**Insight 2 — Khác biệt trung bình hoạt động giữa nhóm Việt Nam và nhóm quốc tế đã nhận diện.** Trung bình tổng hoạt động trên mỗi repository là khoảng 248,9 ở Việt Nam (14 repo) và 1.501,1 ở các quốc gia khác đã nhận diện (31 repo), tương đương khoảng 6,03 lần. Đây chỉ là khác biệt trong mẫu có chủ đích; không thể suy ra năng suất của cả quốc gia vì loại dự án, mức phổ biến và tiêu chí chọn mẫu khác nhau.

**Insight 3 — Đỉnh hoạt động theo tháng khác nhau theo loại event.** Commits đạt đỉnh ở 03/2026 với 1.529; Pull Requests đạt đỉnh ở 03/2026 với 1.579; Issues tạo mới đạt đỉnh ở 06/2022 với 561. Tháng 10/2026 chỉ có dữ liệu đến ngày 20/10 nên chưa phải tháng đầy đủ.

### 3.6 Hạn chế và cách diễn giải

- Sample có chủ đích, không đại diện ngẫu nhiên cho toàn GitHub.
- Location owner là thông tin tự khai báo và có thể thiếu hoặc không chính xác.
- Stars/Forks là snapshot tại thời điểm crawl.
- Repository có số sự kiện lớn có thể chi phối tổng; cần hiển thị số repository và trung bình/repository.
- Contributor login quan sát được trong mẫu không đồng nghĩa với toàn bộ hoạt động của người đó.
- Không diễn giải tương quan mô tả thành quan hệ nhân quả.

## 4. Các file kết quả chính

| File | Mục đích |
|---|---|
| repository_country_metrics.csv | Một dòng/repository, metadata, owner-country, các count và status |
| country_repository_comparison.csv | Tổng hợp theo từng owner-country |
| vietnam_vs_other_countries_comparison.csv | So sánh Vietnam / Other recognized countries / Unknown |
| monthly_activity.csv | Xu hướng theo tháng và số repository được bao phủ |
| developer_activity_summary.csv | Hoạt động theo contributor login quan sát được |
| data_quality_report.csv | Kiểm định số dòng, khóa duy nhất, status và coverage |
| deduplication_audit.csv | Số bản ghi trước/sau khử trùng |
| collection_errors.csv | Repository có lỗi/partial; hiện rỗng trong bản dữ liệu này |

## 5. Tài liệu tham khảo chính thức

1. GitHub REST API overview: https://docs.github.com/en/rest
2. Issues endpoint (bao gồm PR; nhận diện qua trường pull_request): https://docs.github.com/en/rest/issues/issues
3. Commits endpoint và tham số since/until/per_page: https://docs.github.com/en/rest/commits/commits
4. REST API pagination bằng Link header: https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api
5. REST API rate limits và retry/backoff: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api

**Kết luận:** Bộ dữ liệu Giai đoạn 2 hiện có 47 repository và 97.988 hoạt động, với kiểm tra khóa định danh và status được lưu trong audit. Đây là cơ sở để trình bày pipeline API, thiết kế Repository-cha/bảng-con và phân tích mô tả Việt Nam–quốc tế trong phạm vi mẫu đã chọn.
