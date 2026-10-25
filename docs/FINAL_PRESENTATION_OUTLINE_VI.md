# Khung PowerPoint Final — GitHub Developer Analytics

> Slide này là storyboard, không phải kết quả cuối. Thay placeholder bằng kết quả đã audit; không điền số liệu trước khi crawl hoàn tất.

## Slide 1 — Title
GitHub Developer Analytics
- Phân tích hoạt động repository và so sánh mẫu Việt Nam với quốc tế
- Thành viên nhóm / lớp / ngày báo cáo

## Slide 2 — Vấn đề và mục tiêu
- Vì sao phân tích metadata và hoạt động GitHub có ích?
- 3–4 mục tiêu đã chốt
- Nêu khoảng nghiên cứu: 2020-01-01 đến 2026-10-20

## Slide 3 — Câu hỏi nghiên cứu
- Repository nào phổ biến trong mẫu?
- Hoạt động Commit / Issue / PR biến đổi ra sao theo thời gian?
- Mẫu owner-location Vietnam khác gì so với các nhóm owner-country khác?
- Những giới hạn chất lượng nào cần lưu ý?

## Slide 4 — Data collection pipeline
Sơ đồ: GitHub REST API → Raw CSV/checkpoint → validation/cleaning → canonical processed CSV → Power BI / Streamlit.
- Endpoint chính và phương án phân trang
- Throttle / retry / checkpoint
- Tách Issues khỏi Pull Requests

## Slide 5 — Dataset và data quality
- [Số repo duy nhất]
- [Số commit / issue / PR thực tế]
- [Tỷ lệ trạng thái COMPLETE / PARTIAL / ERROR]
- [Tỷ lệ nhận diện owner-country]
- Nêu rõ chưa biến missing thành zero

## Slide 6 — Data model và KPI
- Grain repository-centric: một dòng trên một repo duy nhất
- Country owner khác với country author
- Stars/Forks snapshot; activity counts thuộc khoảng nghiên cứu
- Coverage đi cùng mọi tổng/average

## Slide 7 — Overview
- KPI cards từ Power BI
- Top 10 repository theo Stars snapshot
- Phân bố theo owner-country hoặc language
- [Một quan sát chính kèm số liệu và phạm vi mẫu]

## Slide 8 — Activity trends
- Biểu đồ tháng Commits / Issues / PRs
- Mô tả cao điểm / thấp điểm chỉ khi dữ liệu hỗ trợ
- Hiển thị số repository có metric hoàn chỉnh

## Slide 9 — Vietnam vs International
- So sánh Vietnam / Other recognized / Unknown
- Cân nhắc sử dụng average per complete repository cùng số lượng mẫu
- Tránh kết luận về năng suất của cả quốc gia từ mẫu đã chọn

## Slide 10 — Contributor activity
- Top contributor theo sự kiện đã thu thập đầy đủ
- Giải thích metric, phạm vi repository và giới hạn nhận diện login

## Slide 11 — Three key insights
- Insight 1 + bằng chứng số liệu
- Insight 2 + bằng chứng theo thời gian
- Insight 3 + bằng chứng so sánh nhóm
Mỗi insight có một câu “vì sao đáng chú ý” và một giới hạn diễn giải.

## Slide 12 — Product demo: Power BI and Streamlit
- Power BI: filter, trend, comparison, quality coverage
- Streamlit: repository explorer, contributors, data quality
- [Đường dẫn Streamlit public sau khi đã deploy]

## Slide 13 — Limitations and next steps
- Sampling bias, location self-reported, snapshot metrics, API caps
- Cải tiến tiếp theo và cách tái chạy pipeline

## Slide 14 — Q&A
- Cảm ơn giảng viên
- Link repository / app
