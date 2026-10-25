# Khung báo cáo Final — GitHub Developer Analytics

> Đây là khung nội dung. Chỉ điền các số liệu, biểu đồ và insights sau khi pipeline hoàn tất và data quality audit được duyệt. Không tự điền số liệu ước lượng hoặc suy đoán.

## Trang bìa
- Tên đề tài: GitHub Developer Analytics
- Học phần / lớp / giảng viên / thành viên nhóm: [điền thông tin của nhóm]
- Ngày nộp: [điền ngày]

## Tóm tắt điều hành
Tóm tắt mục tiêu, nguồn GitHub REST API, khoảng nghiên cứu 2020-01-01 đến 2026-10-20, quy mô dữ liệu thực tế sau crawl, 3 kết quả nổi bật đã kiểm chứng, giới hạn chính và sản phẩm Power BI / Streamlit.

## 1. Giới thiệu
### 1.1 Bối cảnh
GitHub là nền tảng cộng tác phát triển phần mềm; dữ liệu công khai của repository có thể hỗ trợ phân tích mức độ phổ biến và hoạt động phát triển.
### 1.2 Mục tiêu
- Phân tích Stars/Forks snapshot, ngôn ngữ và metadata của mẫu repository.
- Phân tích Commit, Issue tạo mới, Pull Request tạo mới theo thời gian.
- So sánh mẫu repository có owner public location được suy ra là Việt Nam với các nhóm owner-country khác.
- Xây dựng dashboard Power BI và website Streamlit từ cùng bộ dữ liệu đã kiểm định.
### 1.3 Câu hỏi nghiên cứu
Chèn các câu hỏi đã chốt trong REBUILD_PLAN_VI.md, không mở rộng câu hỏi sau khi xem kết quả nếu không nêu rõ đó là phân tích bổ sung.

## 2. Phạm vi và phương pháp
### 2.1 Khoảng nghiên cứu
2020-01-01 đến hết 2026-10-20. Nêu rõ Stars/Forks là snapshot tại thời điểm crawl, không phải mức tăng trong giai đoạn.
### 2.2 Nguồn và endpoint API
Mô tả repository search/metadata, owner profile, commits, issues và pull requests. Trình bày các tham số since/until, created date, per_page, page và Link header.
### 2.3 Chọn mẫu
Ghi lại tiêu chí tạo global seed và tiêu chí bổ sung mẫu owner-location Vietnam. Công bố sample_source và giải thích đây không phải mẫu ngẫu nhiên đại diện toàn bộ GitHub.
### 2.4 Giới hạn API và phương án dự phòng
Nêu pagination, Search API result cap, giới hạn request, retry/backoff, checkpoint, split date windows và status PARTIAL/ERROR.
### 2.5 Quy tắc gán quốc gia
Owner country được suy ra từ public profile location tự khai báo. Tách biệt owner-country với country của commit author.

## 3. Thu thập và xử lý dữ liệu
### 3.1 Pipeline
GitHub API → Raw → checkpoint → chuẩn hóa/khử trùng → audit chất lượng → canonical processed CSV → Power BI / Streamlit.
### 3.2 Các bảng dữ liệu
Mô tả repositories, owner profiles, commits, issues, pull requests và các bảng processed trong DATA_DICTIONARY_VI.md.
### 3.3 Chất lượng dữ liệu
Điền từ data_quality_report.csv và deduplication_audit.csv:
- Số repository trong mẫu / ID duy nhất.
- Số record raw từng loại, ID duy nhất và trùng lặp đã xử lý.
- Khoảng ngày thực tế theo bảng sự kiện.
- Số metric COMPLETE / ZERO_CONFIRMED / PARTIAL / ERROR / NOT_RUN.
- Tỷ lệ nhận diện owner-country và coverage từng metric.
### 3.4 Làm sạch và quy tắc không biến missing thành zero
Giải thích khóa ID, null, chuẩn hóa ngày, loại trừ PR khỏi Issues, và xử lý metric chưa hoàn chỉnh.

## 4. Mô hình và chỉ số phân tích
### 4.1 Grain của các bảng
Một dòng trong repository_country_metrics.csv = một repository duy nhất. Monthly activity = country + month. Developer activity summary = login contributor.
### 4.2 Định nghĩa KPI
Stars/Forks snapshot; commits theo endpoint/date window; issues và PR theo ngày tạo; averages chỉ từ repository có metric hoàn chỉnh; coverage công bố cạnh kết quả.
### 4.3 Công cụ
Python/Pandas cho collection/transforms/audit; Power BI cho dashboard; Streamlit cho website demo.

## 5. Kết quả phân tích
> Chỉ điền sau khi dữ liệu Final đã vượt audit.

### 5.1 Tổng quan mẫu
[Chèn KPI và top repositories từ canonical CSV.]
### 5.2 Xu hướng theo tháng
[Chèn chart monthly_activity; giải thích chỉ số và coverage từng metric.]
### 5.3 Việt Nam và quốc tế
[Chèn bảng/biểu đồ vietnam_vs_other_countries_comparison; nêu quy mô mẫu và coverage.]
### 5.4 Contributor activity
[Chèn top contributor từ developer_activity_summary; nhắc đây là login nhận diện được từ dữ liệu sự kiện, không nhất thiết đại diện mọi hoạt động của contributor.]
### 5.5 Ba insights chính
- Insight 1: [mô tả quan sát] — bằng chứng: [metric, sample, coverage, so sánh].
- Insight 2: [mô tả xu hướng] — bằng chứng: [tháng/khoảng thời gian, metric, coverage].
- Insight 3: [so sánh nhóm] — bằng chứng: [số repository, status completeness, giới hạn diễn giải].

Mỗi insight phải ghi rõ số liệu, giai đoạn và một giới hạn có liên quan; không suy ra quan hệ nhân quả từ tương quan mô tả.

## 6. Sản phẩm dashboard
### 6.1 Power BI
Mô tả các trang Overview, Monthly Trends, Vietnam vs International, measures, model và cách refresh data.
### 6.2 Streamlit
Mô tả bộ lọc, repository explorer, contributors, chất lượng dữ liệu và URL demo sau khi deploy.

## 7. Hạn chế
- Mẫu repository không phải mẫu ngẫu nhiên đại diện toàn GitHub.
- Profile location tự khai báo, có thể thiếu hoặc không chính xác.
- Stars/Forks là snapshot hiện tại tại thời điểm crawl.
- Một số metric có thể thiếu/partial do giới hạn API, repository bị xóa/đổi tên hoặc dữ liệu không công khai.
- Tập contributor phản ánh các login gắn với sự kiện thu thập được; không bao quát toàn bộ hoạt động ngoài mẫu.
- Nêu riêng tỷ lệ coverage thực tế và hệ quả của các metric bị loại khỏi phân tích.

## 8. Kết luận và hướng phát triển
Tóm tắt mức độ đạt mục tiêu dựa trên kết quả thực tế, không đưa insight mới chưa phân tích. Đề xuất mở rộng mẫu, cải thiện country resolution, thu thập profile có kiểm soát hoặc tự động cập nhật dữ liệu.

## Tài liệu tham khảo
- GitHub REST API documentation: https://docs.github.com/en/rest
- GitHub pagination: https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api
- GitHub rate limits: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- Streamlit Community Cloud documentation nếu sử dụng deploy: https://docs.streamlit.io/deploy/streamlit-community-cloud

## Phụ lục
- Data dictionary.
- Endpoint / query / parameters.
- Data quality report.
- DAX measures.
- Hướng dẫn chạy pipeline và triển khai website.
