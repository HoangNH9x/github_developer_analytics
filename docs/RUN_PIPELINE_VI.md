# Chạy pipeline chuẩn — GitHub Developer Analytics

Pipeline mới nằm ở nhánh `rebuild-stage1-final`. Pipeline này tách dữ liệu canonical khỏi các file Stage 1/Stage 2 cũ để tránh trộn dữ liệu thử nghiệm với dữ liệu chuẩn.

## 1. Cài đặt lần đầu (Windows PowerShell)

Clone nhánh làm lại hoặc checkout nhánh đó trước:

```powershell
git switch rebuild-stage1-final
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Mở file `.env` bằng VS Code/Notepad và thay giá trị `GITHUB_TOKEN` bằng token của riêng bạn. Chỉ cần quyền đọc đối với dữ liệu public mà bài tập sử dụng. Không gửi token lên chat, không chụp màn hình lộ token và tuyệt đối không commit file `.env`.

Nếu PowerShell chặn kích hoạt môi trường, có thể dùng:
```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe run_pipeline.py --limit-repos 2
```

## 2. Kiểm tra token trước khi crawl

Nếu token chưa được kiểm tra, chạy trước:

```powershell
python check_github_connection.py
```

Script chỉ in trạng thái HTTP và thông báo lỗi; không bao giờ in giá trị token. Nếu trả về HTTP 401, tạo/lưu lại token; nếu HTTP 403, xem thông báo rate limit/permission. Chỉ tiếp tục khi cả xác thực và truy cập repository công khai thành công.

## 3. Chạy thử nhỏ trước

```powershell
python run_pipeline.py --seed .\\smoke_test_seed.csv --limit-repos 1
```

Nếu script báo lỗi metadata, ghi lại nguyên nhân API đầy đủ trong Terminal. Pipeline hiện sẽ dừng an toàn nếu không nhận được metadata nào, thay vì gây traceback khi tạo processed CSV. Không cần xóa checkpoint để thử lại.

Khi smoke test đã thành công, mới thử 10 repositories:

```powershell
python run_pipeline.py --limit-repos 10
```

Lần đầu chỉ chạy 10 repository đầu trong seed file mặc định `data/raw/repositories_stage2.csv`. Đây là bước thử để kiểm tra token, phân trang, schema, checkpoint và audit; chưa phải kết quả Final đầy đủ.

Sau khi chạy xong, kiểm tra:
- `data/raw/canonical/repositories.csv`
- `data/raw/canonical/commits.csv`
- `data/raw/canonical/issues.csv`
- `data/raw/canonical/pull_requests.csv`
- `data/raw/canonical/owner_profiles.csv`
- `data/raw/canonical/repository_checkpoint.csv`
- `data/processed/canonical/repository_country_metrics.csv`
- `data/processed/canonical/country_repository_comparison.csv`
- `data/processed/canonical/vietnam_vs_other_countries_comparison.csv`
- `data/processed/canonical/monthly_activity.csv`
- `data/processed/canonical/developer_activity_summary.csv`
- `data/processed/canonical/deduplication_audit.csv`
- `data/processed/canonical/collection_errors.csv`
- `data/processed/canonical/data_quality_report.csv`

**Không xóa checkpoint trong lúc crawl.** Khi một repository có trạng thái COMPLETE/ZERO_CONFIRMED cho cả ba metric và cùng khoảng ngày, lần chạy sau sẽ bỏ qua repo đó. Các metric PARTIAL/ERROR sẽ được thử lại.

## 4. Tạo mẫu Final cân bằng (khuyến nghị trước khi crawl lớn)

Không chạy cả 952 repository ngay. Trước hết tạo mẫu nhỏ có cả:
- Global seed hiện có (giới hạn số repo bằng `--limit-repos`);
- Owner-country quốc tế đã nhận diện (không trùng owner trong seed, tối đa N repo và tối đa vài repo mỗi quốc gia);
- Owner location Việt Nam đã nhận diện từ public profile.

Ví dụ tạo mẫu bổ sung, giữ nguyên 3 repo seed thử nghiệm và thêm tối đa 12 repo quốc tế cùng tối đa 10 owner Việt Nam (mỗi owner tối đa 1 repo):

```powershell
python run_pipeline.py --seed .\smoke_test_3_seed.csv --limit-repos 3 --discover-global --global-repo-limit 12 --global-per-country 3 --global-min-stars 50 --global-max-stars 5000 --discover-vietnam --vn-owner-limit 10 --vn-repos-per-owner 1
```

Lưu ý:
- Global discovery tìm repository công khai có Stars trong khoảng được đặt, rồi xác minh public profile location của owner. Unknown và Việt Nam bị loại khỏi nhóm quốc tế.
- Mẫu này là mẫu có chủ đích, không phải mẫu ngẫu nhiên đại diện cho toàn GitHub.
- Không chọn nhiều repository từ cùng owner trong phần global discovery; giới hạn số repo mỗi quốc gia giúp giảm tình trạng một owner hoặc một quốc gia chi phối mẫu.
- Không đặt `--limit-repos` quá cao cho seed gốc khi chưa kiểm tra thời gian và độ phủ.

Sau khi mẫu nhỏ hoàn tất, kiểm tra số repo, số record, trạng thái và coverage quốc gia. Chỉ tăng số lượng khi cần đạt mục tiêu tối thiểu 100.000 record tổng mà vẫn giữ được so sánh Việt Nam / quốc tế có ý nghĩa.

## 5. Làm mới dữ liệu

Muốn cập nhật snapshot Stars/Forks và thu thập lại mọi metric:
```powershell
python run_pipeline.py --discover-global --discover-vietnam --force-recrawl --global-repo-limit 12 --global-per-country 3 --vn-owner-limit 10 --vn-repos-per-owner 1
```
Không chạy `--force-recrawl` trừ khi thật sự muốn làm mới toàn bộ lượt crawl.

## 4. Định nghĩa số liệu

- Commits: danh sách commit được API trả về trong `since=2020-01-01T00:00:00Z` đến `until=2026-10-20T23:59:59Z`. Bản ghi có SHA dùng để khử trùng.
- Issues: issue tạo trong khoảng nghiên cứu; truy vấn dùng `is:issue` để tách khỏi PR.
- Pull Requests: PR tạo trong khoảng nghiên cứu; thu thập riêng bằng `is:pr`.
- Stars/Forks: snapshot tại thời điểm crawl, không phải tổng tăng trong giai đoạn.
- Country: suy luận thận trọng từ public profile location của owner; location mơ hồ để Unknown.
- `open_issues_count_api_includes_pr`: trường metadata GitHub có thể bao gồm PR; không dùng nó như số issue-only trong giai đoạn.

Để giảm số lần gọi Search API, pipeline dùng endpoint `/repos/{owner}/{repo}/issues?state=all&since=...` cho cả Issues và Pull Requests trong một luồng phân trang REST API thông thường; sau đó tách PR bằng trường `pull_request` và lọc `created_at` trong cửa sổ nghiên cứu. Theo GitHub, `since` của endpoint này lọc theo thời điểm cập nhật, vì vậy pipeline bắt đầu trước ngày nghiên cứu và lọc lại ngày tạo tại máy. Search API chỉ dành cho discovery/fallback có kiểm soát. Số request vẫn phải tuân thủ rate limits của GitHub; không có cách hợp lệ để vượt qua giới hạn. Metric `PARTIAL/ERROR/NOT_RUN` để trống trong bảng phân tích; số record quan sát được vẫn được giữ trong raw để kiểm tra.

## 5. Quy tắc chọn mẫu và diễn giải

- Mẫu seed hiện tại là mẫu chọn theo nguồn/tiêu chí sẵn có, không phải mẫu ngẫu nhiên đại diện cho mọi repository trên GitHub.
- Các repository bổ sung theo owner Việt Nam có `sample_source=vietnam_owner_discovery`; nên công bố sự khác biệt về cách chọn mẫu trong báo cáo.
- Nếu không có repository Vietnam hoặc metric chưa hoàn tất, không được kết luận rằng Việt Nam có hoạt động bằng 0.
- Country owner khác với country tác giả commit; hai chỉ số đó không được gộp.
- Nếu API bị giới hạn hoặc gặp lỗi, để trạng thái lỗi rõ ràng và tiếp tục chạy để resume. Không đổi dữ liệu thiếu thành số 0.

## 6. Kiểm thử

```powershell
pytest -q
python -m compileall -q src run_pipeline.py
```

Nhánh này có GitHub Actions workflow để chạy unit test và compile check khi có push. Các kiểm tra đó chỉ xác minh helper/schema code; **chúng không thay thế một lần crawl thật bằng token của bạn**.

## 7. Thứ tự làm việc

1. Chạy `--limit-repos 10`.
2. Gửi lại (không kèm token) nội dung `data/processed/canonical/data_quality_report.csv`, `repository_checkpoint.csv` và 5–10 dòng đầu của `repository_country_metrics.csv` nếu cần mình kiểm tra.
3. Sửa lỗi/định nghĩa nếu audit cho thấy vấn đề.
4. Chạy mẫu đầy đủ và chờ các repository PARTIAL/ERROR được xử lý.
5. Chỉ sau khi audit đã đạt mới dùng các canonical processed CSV trong Power BI và Streamlit.
