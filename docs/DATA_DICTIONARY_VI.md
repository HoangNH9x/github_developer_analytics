# Data Dictionary — GitHub Developer Analytics

Tài liệu này là hợp đồng dữ liệu chuẩn cho nhánh tái xây dựng. Tên cột cuối cùng có thể bổ sung theo phản hồi API, nhưng định nghĩa và grain bên dưới không được thay đổi âm thầm.

## 1. Raw entities

### `repositories_raw` — metadata repository
**Grain:** một dòng cho mỗi repository được chọn tại thời điểm crawl (có thể có các phiên bản snapshot nếu thu thập nhiều lần).

| Field | Definition |
|---|---|
| `repository_id` | GitHub numeric ID; khóa định danh repository chính |
| `full_name` | Tên đầy đủ `owner/repo` tại lúc thu thập |
| `repo_name` | Tên repository |
| `owner_login` | Login của tài khoản owner |
| `owner_type` | `User` hoặc `Organization`, nếu API cung cấp |
| `owner_profile_location` | Location công khai tự khai báo của owner |
| `owner_country` | Quốc gia suy luận từ public location; null nếu không đủ bằng chứng |
| `owner_country_status` | `RECOGNIZED`, `UNKNOWN`, hoặc `AMBIGUOUS` |
| `created_at` | Thời điểm repository được tạo |
| `updated_at` | Thời điểm repository được cập nhật gần nhất do API cung cấp |
| `language` | Ngôn ngữ chính mà API gắn với repository; không phải đầy đủ mọi ngôn ngữ |
| `stargazers_count` | Stars tại thời điểm crawl |
| `forks_count` | Forks tại thời điểm crawl |
| `open_issues_count_api_includes_pr` | Số open issues do metadata API trả về; có thể bao gồm PR, không dùng làm số issue-only |
| `html_url` | URL web của repository |
| `sample_source` | Nguồn đưa repository vào mẫu, ví dụ `global_seed` hoặc `vietnam_owner_discovery` |
| `collected_at` | Thời điểm crawl metadata |
| `collection_status` | Trạng thái lấy metadata |

### `commits_raw` — commit records
**Grain:** một dòng cho mỗi commit duy nhất trong phạm vi dữ liệu được crawl.

| Field | Definition |
|---|---|
| `commit_sha` | SHA của commit; khóa chống trùng ưu tiên |
| `repository_id` | Khóa repository |
| `full_name` | Tên repo lúc crawl để đối soát |
| `author_login` | Login tác giả nếu GitHub liên kết được tài khoản |
| `author_name` | Tên tác giả trong metadata commit; không đảm bảo là GitHub login |
| `author_date` | Ngày tác giả ghi trong commit |
| `committer_date` | Ngày committer ghi trong commit |
| `collected_at` | Thời điểm ghi record vào dataset |

### `issues_raw` — issue records, không bao gồm PR
**Grain:** một dòng cho mỗi GitHub issue duy nhất.

| Field | Definition |
|---|---|
| `issue_id` | GitHub issue ID; khóa chống trùng |
| `repository_id` | Khóa repository |
| `number` | Số issue trong repository |
| `created_at` | Thời điểm issue được tạo |
| `closed_at` | Thời điểm đóng, null nếu chưa đóng/không có |
| `state` | Trạng thái theo API tại lúc crawl |
| `comments_count` | Số comment hiện tại do API trả về, không phải comment tạo trong khoảng nghiên cứu |
| `creator_login` | Login người tạo issue theo API nếu được liên kết tài khoản |
| `creator_type` | Loại tài khoản creator khi có |
| `collected_at` | Thời điểm thu thập |

### `pull_requests_raw` — pull request records
**Grain:** một dòng cho mỗi PR duy nhất.

| Field | Definition |
|---|---|
| `pr_id` | GitHub PR/issue ID; khóa chống trùng |
| `repository_id` | Khóa repository |
| `number` | Số PR trong repository |
| `created_at` | Thời điểm PR được tạo |
| `closed_at` | Thời điểm đóng, có thể null |
| `merged_at` | Thời điểm merge, có thể null |
| `state` | Trạng thái theo API tại lúc crawl |
| `comments_count` | Số comment hiện tại theo API, không phải count lịch sử theo ngày |
| `creator_login` | Login người tạo PR theo API nếu được liên kết tài khoản |
| `creator_type` | Loại tài khoản creator khi có |
| `collected_at` | Thời điểm thu thập |

## 2. Canonical processed tables

### `dim_repository.csv`
**Grain:** đúng một dòng cho mỗi `repository_id`.

Tối thiểu gồm: `repository_id`, `full_name`, `repo_name`, `owner_login`, `owner_type`, `owner_profile_location`, `owner_country`, `owner_country_status`, `language`, `created_at`, `sample_source`.

### `repository_country_metrics.csv`
**Grain:** đúng một dòng cho mỗi repository trong mẫu. Khóa duy nhất là `repository_id`.

Tối thiểu gồm:
- Repository metadata: `repository_id`, `full_name`, `owner_login`, `owner_country`, `owner_country_status`, `language`, `sample_source`.
- Snapshot metrics: `stars_snapshot`, `forks_snapshot`, `snapshot_at`.
- Window metrics: `commits_count_window`, `issues_created_count_window`, `prs_created_count_window`.
- Status riêng cho từng metric: `commits_status`, `issues_status`, `prs_status`; giá trị dự kiến gồm `COMPLETE`, `ZERO_CONFIRMED`, `PARTIAL`, `ERROR`, `NOT_RUN`.
- Phạm vi: `study_start`, `study_end`, `collected_at`.

Không tính trung bình hoặc ranking dựa trên metric có status khác `COMPLETE`/ `ZERO_CONFIRMED`.

### `monthly_activity.csv`
**Grain:** một dòng cho mỗi `owner_country` + `activity_month`.

Các cột hiện được pipeline xuất ra:
- `commits_count_complete`, `issues_count_complete`, `prs_count_complete`: số sự kiện theo tháng từ các repository có trạng thái thu thập COMPLETE/ZERO_CONFIRMED cho metric tương ứng.
- `commits_repositories_covered`, `issues_repositories_covered`, `prs_repositories_covered`: số repository trong quốc gia/nhóm có metric tương ứng thu thập hoàn chỉnh.

Các repository PARTIAL/ERROR/NOT_RUN bị loại khỏi metric tương ứng. Mỗi tháng không có hoạt động trong tập đã thu thập hoàn chỉnh được thể hiện bằng 0.

### `developer_activity_summary.csv`
**Grain:** một dòng cho mỗi GitHub login xuất hiện trong record hoạt động đã thu thập hoàn chỉnh.

Cột gồm `developer_login`, `commits_count_complete`, `issues_created_count_complete`, `prs_created_count_complete` và `total_contributions_observed_complete`. Các contribution counts chỉ gồm hoạt động từ repository có metric tương ứng đã thu thập hoàn chỉnh. Bảng này không gán quốc gia owner cho developer và hiện không xác minh location của tác giả.

### `country_repository_comparison.csv`
**Grain:** một dòng cho mỗi quốc gia / nhóm quốc gia.

Tối thiểu: `owner_country`, `repositories_total`, `repositories_with_complete_commits`, `repositories_with_complete_issues`, `repositories_with_complete_prs`, `stars_sum_snapshot`, `stars_avg_snapshot`, `forks_sum_snapshot`, `forks_avg_snapshot`, `commits_sum_complete`, `commits_avg_per_repo_complete`, `issues_sum_complete`, `issues_avg_per_repo_complete`, `prs_sum_complete`, `prs_avg_per_repo_complete`.

### `vietnam_vs_other_countries_comparison.csv`
**Grain:** một dòng cho mỗi nhóm cố định:
- `Vietnam`
- `Other recognized countries`
- `Unknown / unresolved`

Phải luôn giữ đủ ba nhóm kể cả khi một nhóm có 0 repository; ghi số lượng mẫu và coverage để tránh kết luận nhầm do dữ liệu thiếu.

### `data_quality_report.csv`
**Grain:** một dòng cho mỗi bảng / metric / quy tắc kiểm tra.

Các thông tin đề xuất: `table_name`, `check_name`, `expected_rule`, `observed_value`, `status`, `details`, `checked_at`.

### `collection_errors.csv`
**Grain:** một dòng cho mỗi repository có metric chưa hoàn tất hoặc owner profile không lấy/nhận diện được.

Bảng giữ trạng thái theo từng metric, lỗi API gần nhất, số record quan sát được và khoảng nghiên cứu. Dùng để audit và giải thích coverage; không dùng các số record quan sát được từ PARTIAL như số tổng chính xác.

## 3. Nguyên tắc đếm và join

1. Tách Issue khỏi PR: khi lấy Issues từ GitHub Issues API/Search API cần loại PR, ví dụ bằng điều kiện `is:issue`; lấy PR riêng bằng điều kiện `is:pr`.
2. Khoảng thời gian lọc theo ngày tạo issue/PR và ngày commit được định nghĩa rõ trong pipeline. Phải xử lý ngày kết thúc bao gồm hết 2026-10-20.
3. Stars/Forks là snapshot hiện tại; không mô tả chúng như số đã tăng trong 2020–2026.
4. Tổng activity theo quốc gia phải tính từ bảng grain repository sau khi metric đủ hoàn tất; không merge bảng detail commits × issues × PRs trực tiếp vì sẽ nhân bản record.
5. Profile location thiếu/khó hiểu không được đoán quốc gia. Dùng `Unknown / unresolved` và giữ raw location để có thể audit.
6. Quốc gia owner và quốc gia author là hai thuộc tính khác nhau; chỉ tạo phân tích author-country khi có bảng developer/profile riêng.
7. Nếu GitHub API trả về lỗi, giới hạn search, timeout, hoặc thiếu trang, giữ trạng thái `PARTIAL`/`ERROR`; không chuyển count rỗng thành 0.
8. Với repository đổi tên/chủ sở hữu, lưu `repository_id` và snapshot `full_name` để phát hiện; không coi `full_name` là khóa bất biến.
