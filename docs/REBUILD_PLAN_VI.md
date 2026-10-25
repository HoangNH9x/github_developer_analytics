# Kế hoạch làm lại GitHub Developer Analytics — từ Giai đoạn 1 đến Final

## 1. Nguyên tắc làm lại

- Giữ nguyên lịch sử và file cũ trên `main`; mọi thay đổi tái xây dựng nằm trên nhánh `rebuild-stage1-final`.
- Chỉ có **một pipeline chính thức** để thu thập → kiểm tra → làm sạch → tạo bảng phân tích.
- Tách `raw` (dữ liệu API nguyên bản), `interim` (bước trung gian), `processed` (bộ dữ liệu phân tích) và `reports` (báo cáo/biểu đồ).
- Không ghi đè dữ liệu raw bằng dữ liệu đã clean; không coi dữ liệu thiếu hoặc thu thập dở dang là số 0.
- Mỗi lần chạy phải ghi thời điểm thu thập, khoảng thời gian nghiên cứu, trạng thái phân trang và trạng thái chất lượng dữ liệu.
- Không đưa GitHub token, file `.env`, thông tin cá nhân nhạy cảm hoặc file checkpoint cục bộ lên GitHub.

## 2. Câu hỏi nghiên cứu và phạm vi

**Tên đề tài:** GitHub Developer Analytics: phân tích hoạt động repository và so sánh mẫu repository có chủ sở hữu đặt tại Việt Nam với mẫu quốc tế.

**Khoảng thời gian hoạt động:** từ 2020-01-01 đến hết 2026-10-20 (inclusive). Metadata phổ biến như Stars/Forks là snapshot tại thời điểm thu thập, không phải số tăng thêm trong khoảng thời gian này.

**Câu hỏi chính:**
1. Các repository trong mẫu có quy mô và mức độ phổ biến như thế nào (Stars, Forks, ngôn ngữ)?
2. Mức độ hoạt động theo thời gian thể hiện qua Commits, Issues được tạo và Pull Requests được tạo ra sao?
3. Trong mẫu nghiên cứu, các repository có chủ sở hữu ghi địa điểm ở Việt Nam khác gì so với repository của chủ sở hữu ở quốc gia khác?
4. Xu hướng theo tháng/năm có thay đổi không, và dữ liệu nào đủ đầy để kết luận?
5. Phần dữ liệu thiếu, không phân giải được quốc gia hoặc bị giới hạn API có thể làm sai lệch kết quả đến mức nào?

**Lưu ý diễn giải:** quốc gia được suy ra từ trường location công khai do chủ tài khoản GitHub tự khai báo. Đây không phải bằng chứng xác minh nơi cư trú hay quốc gia pháp lý của repository. Phân tích theo quốc gia chủ repository phải tách biệt với phân tích quốc gia của tác giả commit; không được gộp hai khái niệm.

## 3. Các giai đoạn thực hiện

### Giai đoạn 1 — Xác định bài toán và thiết kế thu thập
- Chốt câu hỏi nghiên cứu, chỉ số, khoảng thời gian, quy tắc chọn mẫu.
- Lập danh sách endpoint GitHub API, tham số, cách phân trang, giới hạn và phương án retry.
- Viết thuyết minh quy trình crawl và sơ đồ pipeline để báo cáo giảng viên.
- Định nghĩa data dictionary và quy tắc phân loại Vietnam / Other recognized / Unknown.

**Đầu ra:** đề cương, sơ đồ pipeline, bảng endpoint/tham số, data dictionary, tiêu chí nghiệm thu.

### Giai đoạn 2 — Thu thập dữ liệu API
- Thu thập metadata repository và thông tin public profile của owner.
- Thu thập counts/records Commits, Issues (không gồm PR), Pull Requests theo khoảng ngày.
- Lưu nguyên trạng phản hồi/record vào raw CSV hoặc JSONL; checkpoint để tiếp tục sau lỗi.
- Ghi `sample_source`, `collected_at`, `study_start`, `study_end`, `collection_status` và `collection_method`.
- Đặt mục tiêu tối thiểu 100.000 record tổng trên các nhóm dữ liệu nếu API và giới hạn truy cập cho phép; công bố số liệu thực tế sau crawl, không cam kết trước khi chạy.

**Đầu ra:** raw repositories, commits, issues, pull requests, owner profiles và checkpoint/audit.

### Giai đoạn 3 — Kiểm tra chất lượng và làm sạch
- Kiểm tra schema, kiểu dữ liệu, null, bản ghi trùng, khóa ID, định dạng ngày, các giá trị ngoại lệ.
- Chuẩn hóa tên cột, múi giờ/ngày, owner login/repo full name, quốc gia và loại tài khoản.
- Loại trùng theo ID thật của GitHub; không xóa trùng chỉ bằng tiêu đề.
- Giữ nguyên cột trạng thái thu thập; metric `PARTIAL`, `ERROR` hoặc `UNKNOWN` không được sử dụng như metric chính xác.
- Tạo báo cáo data quality và đối soát số dòng raw → clean.

**Đầu ra:** clean CSVs, data quality report, quy tắc xử lý lỗi có thể chạy lại.

### Giai đoạn 4 — Mô hình dữ liệu và phân tích
- Dùng grain rõ ràng: **một dòng trong bảng repository summary = một repository duy nhất**.
- Khóa chính repository là GitHub `repository_id` (hoặc `repo_id` chuẩn hóa nếu dữ liệu nguồn không có ID).
- Tạo bảng summary theo repository và bảng activity theo tháng; không join nhiều fact-detail trực tiếp với nhau theo cách gây nhân bản số liệu.
- Tạo nhóm `Vietnam`, `Other recognized countries`, `Unknown / unresolved`.
- Stars/Forks hiện tại; Commits/Issues/PRs trong khoảng nghiên cứu; các chỉ số phải có nhãn và định nghĩa riêng.
- Tính trung bình theo repository chỉ từ các repository có metric đã hoàn tất. Hiển thị riêng coverage/unknowns.

**Đầu ra:** bảng phân tích chuẩn, EDA, biểu đồ và tối thiểu 3 insights được hỗ trợ bởi dữ liệu thực.

### Giai đoạn 5 — Power BI
- Nạp duy nhất các CSV trong thư mục processed đã được pipeline sinh ra.
- Trang 1: Overview / chất lượng mẫu và KPI chính.
- Trang 2: xu hướng hoạt động theo thời gian (Commits, Issues, PRs).
- Trang 3: Việt Nam so với quốc tế theo quốc gia owner, đồng thời thể hiện độ phủ dữ liệu.
- Dùng `repository_id` làm khóa; không liên kết các bảng chỉ bằng tên hiển thị nếu có khóa ID.
- Không dùng đường dẫn máy cá nhân dạng `E:\...`; ưu tiên đường dẫn tương đối hoặc hướng dẫn đổi nguồn rõ ràng.

**Đầu ra:** PBIX refresh được, nhãn/measure rõ ràng, nguồn và trạng thái chất lượng minh bạch.

### Giai đoạn 6 — Website Streamlit
- Dùng cùng processed CSV với Power BI; không tự crawl lại hoặc tự tính một phiên bản khác trong app.
- Có Overview, Vietnam vs International, Time Trend, Repository Explorer và Data Quality.
- Hiện rõ ngày cập nhật, khoảng thời gian, sample limitations và số liệu chưa hoàn chỉnh.
- Có hướng dẫn chạy local và triển khai; không commit token.

**Đầu ra:** ứng dụng có thể chạy từ repo, README deploy và đường dẫn public sau khi người dùng hoàn tất cấu hình triển khai.

### Giai đoạn 7 — Báo cáo và bảo vệ Final
- Báo cáo Word: mục tiêu, phương pháp crawl, data cleaning, mô hình dữ liệu, kết quả, 3+ insights, hạn chế và kết luận.
- PowerPoint: vấn đề, pipeline, chất lượng dữ liệu, kết quả, insights, demo Power BI/Streamlit.
- Chuẩn bị kịch bản demo, hướng dẫn tái chạy pipeline và các câu hỏi thường gặp.
- Đồng bộ số liệu giữa Word, PowerPoint, Power BI và Streamlit từ cùng phiên bản dữ liệu.

## 4. Bộ quy tắc thống nhất

| Thành phần | Quy tắc chuẩn |
|---|---|
| Khoảng nghiên cứu | 2020-01-01 đến 2026-10-20, bao gồm cả ngày kết thúc |
| Đơn vị repository | Một repository duy nhất theo `repository_id` |
| Quốc gia chính | Quốc gia suy ra từ public profile location của owner |
| Quốc gia tác giả commit | Chỉ dùng trong phân tích riêng; không thay thế quốc gia owner |
| Stars / Forks | Snapshot tại ngày thu thập |
| Commits | Commit trong khoảng thời gian nghiên cứu; ghi rõ phương pháp và giới hạn endpoint |
| Issues | Issue tạo trong khoảng thời gian, loại trừ pull request |
| Pull Requests | PR tạo trong khoảng thời gian |
| Missing / Partial | Unknown/Partial không được biến thành 0 |
| Zero hợp lệ | Chỉ dùng 0 khi việc thu thập hoàn tất và đã xác nhận không có record |
| So sánh quốc gia | Báo cáo quy mô mẫu và coverage; không suy rộng thành năng suất của cả quốc gia |
| Secret | Token chỉ lưu local trong `.env` hoặc secret manager |

## 5. Cấu trúc thư mục đích

```text
docs/
  REBUILD_PLAN_VI.md
  DATA_DICTIONARY_VI.md
src/github_analytics/
  config.py
  collect/
  transform/
  validate/
  analysis/
data/
  raw/
  interim/
  processed/
reports/
  figures/
  tables/
powerbi/
app/
tests/
```

Cấu trúc này là đích tái tổ chức. Trong quá trình chuyển đổi, dữ liệu cũ được giữ nguyên; chỉ đánh dấu file nào là legacy sau khi đã đối chiếu và xác nhận.

## 6. Tiêu chí nghiệm thu

- [ ] Có thể chạy lại pipeline từ lệnh hướng dẫn trong README.
- [ ] Không có secret/token trong git history của nhánh làm lại mới.
- [ ] Mỗi repository có khóa duy nhất; không nhân bản số liệu sau join.
- [ ] Khoảng thời gian, định nghĩa metric và phương pháp crawl được ghi rõ.
- [ ] Báo cáo quality có row count, duplicate count, null count, status coverage.
- [ ] Số liệu partial/error không bị trình bày như kết quả chính xác.
- [ ] Word, PowerPoint, Power BI và Streamlit sử dụng cùng một phiên bản processed data.
- [ ] Có ít nhất 3 insights được tính từ dữ liệu thực; không viết insight trước khi có kết quả hợp lệ.
- [ ] Hạn chế về mẫu, location tự khai báo và dữ liệu snapshot được nêu trong báo cáo.
