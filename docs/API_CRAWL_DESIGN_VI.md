# Thiết kế crawl GitHub API — Giai đoạn 1

## 1. Mục tiêu

Thiết kế một lần crawl có thể tái chạy, có checkpoint, và có thể giải thích trong báo cáo. Khoảng nghiên cứu hoạt động là 2020-01-01 đến hết 2026-10-20. Mỗi lần chạy phải ghi timestamp thực tế; dữ liệu snapshot của repository không được nhầm với hoạt động lịch sử.

## 2. API endpoints

| Entity | Endpoint / query | Dùng để lấy | Ghi chú |
|---|---|---|---|
| Repository discovery | `GET /search/repositories?q=...` | Khám phá, chọn danh sách repo | Search trả tối đa 1.000 kết quả cho một query; chia query theo tiêu chí rõ ràng, không lấy trang ngoài giới hạn |
| Repository metadata | `GET /repos/{owner}/{repo}` | `repository_id`, stars, forks, language, created_at, owner, URL | Stars/Forks là snapshot lúc lấy |
| Owner profile | `GET /users/{username}` hoặc `GET /orgs/{org}` | Public location, type, profile metadata | Location tự khai báo, có thể null/không rõ |
| Commit list | `GET /repos/{owner}/{repo}/commits?since=...&until=...&per_page=100&page=...` | Commit records trong cửa sổ thời gian | Dùng `Link` header để đi hết trang; lưu SHA để chống trùng |
| Issue search | `GET /search/issues?q=repo:OWNER/REPO is:issue created:START..END` | Issue tạo trong khoảng ngày | Điều kiện `is:issue` loại PR; search giới hạn 1.000 kết quả/query |
| PR search | `GET /search/issues?q=repo:OWNER/REPO is:pr created:START..END` | Pull request tạo trong khoảng ngày | PR được lưu riêng; không gộp vào issue-only count |

Tài liệu chính thức:
- Search API: https://docs.github.com/en/rest/search/search
- Commits API: https://docs.github.com/en/rest/commits/commits
- Issues API: https://docs.github.com/en/rest/issues/issues
- Pagination: https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api
- Rate limits và xử lý lỗi: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api và https://docs.github.com/en/rest/using-the-rest-api/troubleshooting-the-rest-api

## 3. Request headers

Mẫu header đề xuất:

```http
Accept: application/vnd.github+json
Authorization: Bearer <GITHUB_TOKEN>
X-GitHub-Api-Version: 2026-03-10
User-Agent: github-developer-analytics-student-project
```

Token chỉ lưu ở file local `.env` không được commit hoặc chia sẻ trong chat. Không cần cấp quyền ghi repository; chỉ xin quyền đọc cần thiết cho dữ liệu public mà bài tập sử dụng.

## 4. Phân trang, retry và checkpoint

1. Ưu tiên đọc `Link` response header để tìm trang tiếp theo/cuối. Không tự giả định luôn có số trang cuối.
2. Với commits và endpoints hỗ trợ pagination, dùng `per_page=100` và tiếp tục cho đến khi không còn trang hoặc không có record mới.
3. Với Search API, chia cửa sổ `created:` thành khoảng con khi query chạm giới hạn kết quả, có `incomplete_results=true`, hoặc API báo lỗi. Nếu cửa sổ nhỏ nhất vẫn bị giới hạn, đánh dấu `PARTIAL`; không khẳng định count chính xác.
4. Khi nhận 403/429 do rate limit, tuân thủ `Retry-After`, `X-RateLimit-Reset` và exponential backoff theo response. Không retry liên tục gây thêm hạn chế.
5. Sau mỗi repository, ghi checkpoint gồm `repository_id`, metric đã hoàn tất, trạng thái, lần thử gần nhất, khoảng ngày và lỗi gần nhất.
6. Resume chỉ tái sử dụng kết quả hoàn tất nếu cùng sample, cùng khoảng ngày, cùng phương pháp và cùng phiên bản pipeline; nếu không thì phải làm mới metric bị ảnh hưởng.
7. Khi có timeout hoặc lỗi mạng, giữ trạng thái chưa hoàn tất; không đổi số liệu rỗng thành zero.

## 5. Chọn mẫu và giới hạn suy luận

- Mẫu global phải có quy tắc chọn lặp lại được (ví dụ query theo ngôn ngữ/nhóm thời gian và giới hạn kết quả được ghi lại); không gọi nó là mẫu đại diện ngẫu nhiên toàn GitHub.
- Mẫu repository owner-location Vietnam có thể được tìm qua query tìm kiếm user/org và xác minh lại public location bằng endpoint profile. Các query theo thành phố có thể bỏ sót người dùng và có thể trùng lặp, nên phải khử trùng theo login/ID.
- Nếu bổ sung repository Việt Nam có chủ đích để đủ dữ liệu so sánh, ghi `sample_source=vietnam_owner_discovery`; không trộn lẫn về mặt phương pháp với mẫu global gốc.
- Nếu không đủ số lượng repository có owner-country Vietnam hoặc không có coverage đủ tốt, báo cáo rõ và không kết luận quốc gia này có hoạt động thấp hơn chỉ từ số đếm thô.
- Public profile location không được xác minh độc lập; nhãn quốc gia mang tính suy luận.

## 6. Quy tắc định nghĩa chỉ số

| Metric | Định nghĩa | Trạng thái không hoàn tất |
|---|---|---|
| Stars snapshot | `stargazers_count` khi crawl metadata | Lỗi metadata thì unknown |
| Forks snapshot | `forks_count` khi crawl metadata | Lỗi metadata thì unknown |
| Commits window | Commit record có ngày trong cửa sổ nghiên cứu, theo phương pháp đã pin | `PARTIAL/ERROR` không dùng làm count chính thức |
| Issues created window | Issue có `created_at` trong cửa sổ, được lấy từ điều kiện `is:issue` | Không coi page thiếu là 0 |
| PRs created window | PR có `created_at` trong cửa sổ, lấy riêng bằng `is:pr` | Không coi page thiếu là 0 |
| Open issues metadata | `open_issues_count` từ repository metadata | Không dùng thay Issues created window vì có ngữ nghĩa khác |

## 7. Cách chứng minh dữ liệu thu thập đạt yêu cầu

Cần xuất audit tối thiểu các trường: total repos in sample, distinct repository IDs, raw rows theo entity, distinct IDs, duplicate rows, min/max timestamps, số metric COMPLETE/ZERO_CONFIRMED/PARTIAL/ERROR, owner-country recognized/unknown, số ngày/phạm vi crawl và thời điểm crawl.

Không tuyên bố “đã crawl đủ 100.000 dòng” trước khi audit hoàn tất. Mục tiêu 100.000+ record tính tổng trên các entity, không phải 100.000 record cho từng entity; kết quả thực tế phải lấy từ audit sau crawl.
