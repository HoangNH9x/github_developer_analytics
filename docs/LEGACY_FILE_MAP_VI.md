# Bản đồ file hiện có và quy tắc kế thừa dữ liệu

## Mục đích

Thư mục hiện tại đã có nhiều vòng thử nghiệm. Tài liệu này không kết luận rằng tất cả file cũ đều sai; nó phân biệt nguồn gốc, mục đích, và cách cho phép dùng lại để tránh ghép các dataset khác phạm vi hoặc khác định nghĩa.

## 1. Nhóm Giai đoạn 1

**Thư mục:** Ass_GD1/

Có script và CSV như main.py, commit.py, issues.py, cleaning.py, eda.py, repositories.csv, commits.csv, issues.csv và các file *_clean.csv.

**Xử lý:** giữ nguyên làm bằng chứng cho Assignment/Giai đoạn 1. Không tự nối với Stage 2 chỉ vì các cột có tên tương tự. Chỉ tái dùng sau khi xác nhận khoảng thời gian, tiêu chí chọn 10 repository, schema và khóa dữ liệu phù hợp.

## 2. Nhóm collector Stage 2

Các script đang nằm ở thư mục gốc gồm:
- collect_stage2.py
- collect_commits_stage2.py
- collect_commits_batch.py
- collect_commits_paged.py
- collect_issues_pr_stage2.py
- collect_developers_stage2.py
- collect_active_author_profiles.py
- collect_vietnam_profiles.py
- find_vietnam_developers.py

**Vấn đề quản lý:** tồn tại nhiều lối thu thập khác nhau, một số dùng batch/pagination/checkpoint khác nhau. Không chạy tất cả như một pipeline duy nhất và không nối output của các script nếu chưa cùng schema/phạm vi.

**Quy tắc mới:** sau khi xây collector chuẩn ở src/github_analytics/collect/, chỉ một entry point chính thức mới được dùng để thu thập dữ liệu Final. Các script cũ được xem là legacy/reference cho đến khi được kiểm thử tương thích.

## 3. Nhóm audit/validation

Hiện có các file như audit_stage2.py, audit_country_activity.py, audit_developers.py, audit_repository_coverage.py, final_audit_stage2.py, validate_repositories.py và validate_commits_stage2.py cùng check_commit_spike.py.

**Xử lý:** không xóa. Giữ lại để đối chiếu và lấy logic kiểm tra có ích; sau đó hợp nhất quy tắc thành một bộ quality report thống nhất. Mỗi kiểm tra mới phải nêu bảng đầu vào, khóa dùng để kiểm tra và ngưỡng/pass condition.

## 4. Nhóm dữ liệu raw hiện có

Thư mục data/raw/ gồm:
- Repository: repositories_stage2.csv, repositories_test.csv
- Commit: commits_stage2.csv, commits_test.csv, commits_repositories_done.csv, commits_pagination_checkpoint.csv
- Issue/PR: issues_stage2.csv, pull_requests_stage2.csv, issues_pr_checkpoint.csv, issues_pr_checkpoint_backup.csv
- Developer/profile: developers_stage2.csv, developers_activity_profiles.csv, developers_activity_profiles_checkpoint.csv, developers_not_found.csv, vietnam_developer_candidates.csv, vietnam_developer_profiles.csv

**Xử lý:** giữ các raw CSV gốc để kiểm tra khả năng tái dùng. Không tự nối *_test.csv vào dataset chính. Không coi checkpoint như bảng sự kiện hoạt động. Record từ checkpoint cần được phân biệt với event raw records.

## 5. Nhóm dữ liệu processed hiện có

Thư mục data/processed/ bao gồm:
- Repository summary: repository_activity_counts.csv, activity_by_repository.csv
- Country/activity: activity_by_country.csv, country_activity_coverage.csv, country_activity_detailed.csv, country_activity_distribution.csv, developer_country_distribution.csv, vietnam_vs_international_summary.csv, monthly_vietnam_international.csv
- Developer master: developers_stage2_master.csv, developers_stage2_country.csv
- Audit/clean: analysis_data_quality.csv, comparison_data_quality.csv, final_audit_report.csv, repository_coverage_audit.csv
- Clean commits: commits_stage2_clean.csv

**Xử lý:** không coi toàn bộ file này là một bộ dữ liệu đồng nhất. Tên một số bảng phản ánh quốc gia tác giả/developer, số khác tổng hợp theo repo. Chỉ file được pipeline mới xuất ra trong data/processed/ mới là đầu vào chuẩn cho báo cáo Final.

## 6. Báo cáo và app hiện tại

- Ass_final.pbix: giữ làm bản so sánh tham khảo. Sau khi có canonical processed tables, cần kiểm tra lại relationship, Power Query paths, measures và coverage trước khi dùng làm bản nộp cuối.
- streamlit_app.py: giữ làm bản tham khảo. Final app sẽ phải đọc cùng processed CSV với Power BI và hiển thị trạng thái chất lượng dữ liệu.
- Charts/: có thể dùng lại hình ảnh/biểu đồ sau khi xác nhận nguồn và định nghĩa; không dùng chart cũ làm bằng chứng cho số liệu mới.
- insight.md: phải viết lại từ kết quả đã audit của bộ dữ liệu cuối, không chỉ sao chép insight cũ.
- requirements.txt: hiện chứa cả các package đã pin và các dependency có dòng trùng/đè yêu cầu như pandas, streamlit. Cần chuẩn hóa thành dependency trực tiếp tối thiểu và kiểm thử trong môi trường mới.

## 7. Các lỗi phương pháp cần tránh trong pipeline mới

1. Cộng số dòng hiện có của một file mà không kiểm tra pagination/completeness.
2. Xem giới hạn số lượng trả về theo repository/search query như số lượng thật.
3. Biến count null hoặc metric chưa chạy thành số 0.
4. Gọi open_issues_count của repository là Issues được tạo trong khoảng thời gian; metadata này có thể bao gồm PR và có ngữ nghĩa khác.
5. Ghép bảng commit, issue và PR dạng detail trực tiếp bằng repo rồi tính tổng; join many-to-many có thể nhân bản số lượng.
6. Dùng country của tác giả commit làm country của repository owner.
7. Suy rộng kết quả của mẫu repository được chọn theo truy vấn/thứ hạng thành kết luận về toàn bộ GitHub hoặc toàn bộ quốc gia.
8. Để Word, PowerPoint, Power BI và Streamlit mỗi nơi tự tính một phiên bản KPI riêng.

## 8. Luật kế thừa dữ liệu

Một file cũ chỉ được đưa vào nguồn chuẩn khi đủ cả các điều kiện:
- Schema và khóa được kiểm tra.
- Khoảng thời gian được xác nhận.
- Phương pháp crawl và coverage có thể giải thích.
- Trùng lặp đã được kiểm tra bằng ID ổn định.
- Tình trạng COMPLETE/PARTIAL/ERROR được xác định hoặc có thể tái lập từ checkpoint.
- Các định nghĩa metric khớp với Data Dictionary.
- Kết quả audit được ghi lại.

Nếu không đáp ứng điều kiện, file vẫn có thể dùng trong phần nhật ký tiến trình hoặc đối chiếu, nhưng không dùng làm nguồn chính để kết luận.
