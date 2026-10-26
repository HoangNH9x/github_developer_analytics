# GitHub Developer Analytics

Phân tích hoạt động repository GitHub, xu hướng Commits / Issues / Pull Requests, và so sánh repository có chủ sở hữu công khai đặt location tại Việt Nam với mẫu quốc tế.

> Nhánh `rebuild-stage1-final` đang xây pipeline chuẩn mới. Các script và CSV cũ được giữ lại để đối chiếu; chúng không mặc nhiên là nguồn chính thức cho kết quả Final.

## Trạng thái hiện tại

- [Kế hoạch làm lại Giai đoạn 1 → Final](docs/REBUILD_PLAN_VI.md)
- [Data Dictionary](docs/DATA_DICTIONARY_VI.md)
- [Thiết kế GitHub API crawl](docs/API_CRAWL_DESIGN_VI.md)
- [Bản đồ file cũ](docs/LEGACY_FILE_MAP_VI.md)
- [Hướng dẫn chạy pipeline chuẩn](docs/RUN_PIPELINE_VI.md)
- [Thiết kế Power BI và DAX](docs/POWERBI_MODEL_VI.md)
- [Phân tích dữ liệu Final và 3 insights](docs/FINAL_DATA_ANALYSIS_VI.md)
- [Hướng dẫn deploy Streamlit](docs/STREAMLIT_DEPLOY_VI.md)

Pipeline mới nằm trong `src/github_analytics/` và có entry point `run_pipeline.py`. Dùng `python check_github_connection.py` để xác minh token local trước khi crawl. Streamlit Final nằm ở `app/streamlit_app.py`. Trước tiên cần chạy thử với 3 repository, kiểm tra checkpoint / data-quality report, rồi mở rộng sang mẫu quốc tế/Việt Nam có kiểm soát; sau đó mới dùng canonical processed CSV cho Power BI và deploy app.

## Nghiên cứu và chỉ số

- **Khoảng thời gian hoạt động:** 2020-01-01 đến hết 2026-10-20.
- **Grain bảng phân tích chính:** một dòng cho mỗi repository duy nhất theo `repository_id`.
- **Stars / Forks:** snapshot tại thời điểm crawl, không phải mức tăng trong khoảng nghiên cứu.
- **Commits:** dữ liệu commit trả về từ API trong cửa sổ `since` / `until`.
- **Issues:** issue được tạo trong khoảng thời gian; pipeline lấy Issues + PRs qua một luồng phân trang REST API rồi tách issue thường khỏi PR bằng trường `pull_request`.
- **Pull Requests:** PR được tạo trong khoảng thời gian, lấy riêng bằng `is:pr`.
- **Country:** suy luận từ public profile location tự khai báo của owner; location mơ hồ được giữ là Unknown.
- **Author country:** khái niệm khác với owner country và chỉ dùng trong phân tích developer riêng.

Không trình bày metric `PARTIAL`, `ERROR` hoặc `NOT_RUN` như số liệu chính xác và không biến dữ liệu thiếu thành zero. Mẫu repository là mẫu chọn theo các tiêu chí tìm kiếm đã ghi lại, không phải mẫu ngẫu nhiên đại diện toàn GitHub.

## Chạy pipeline trên Windows

Yêu cầu Python 3.10 trở lên.

```powershell
git switch rebuild-stage1-final
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Điền GitHub token vào file `.env` local trên máy của bạn. Không commit file này và không chia sẻ token.

Chạy thử:

```powershell
python run_pipeline.py --limit-repos 10
```

Sau khi kiểm tra quality report và checkpoint, chạy mẫu đầy đủ với bổ sung owner Việt Nam:

```powershell
python run_pipeline.py --seed .\smoke_test_3_seed.csv --limit-repos 3 --discover-global --global-repo-limit 12 --global-per-country 3 --global-min-stars 50 --global-max-stars 5000 --discover-vietnam --vn-owner-limit 10 --vn-repos-per-owner 1
```

Chi tiết đầu ra, giới hạn API và cách resume được ghi trong [RUN_PIPELINE_VI.md](docs/RUN_PIPELINE_VI.md).

## Cấu trúc dữ liệu canonical

```text
data/
  raw/
    canonical/
      repositories.csv
      owner_profiles.csv
      commits.csv
      issues.csv
      pull_requests.csv
      repository_checkpoint.csv
  processed/
    canonical/
      repository_country_metrics.csv
      country_repository_comparison.csv
      vietnam_vs_other_countries_comparison.csv
      monthly_activity.csv
      developer_activity_summary.csv
      deduplication_audit.csv
      collection_errors.csv
      data_quality_report.csv
src/github_analytics/
  config.py
  country.py
  github_api.py
  pipeline.py
tests/
```

Raw data là bản thu thập có thể kiểm tra; processed data là nguồn chuẩn dùng cho Power BI và Streamlit sau khi audit đạt.

## Kiểm thử

```powershell
pytest -q
python -m compileall -q src run_pipeline.py
```

CI chạy unit test và compile check khi push lên nhánh làm lại. CI không chạy crawl API vì token không được lưu trong repository.
