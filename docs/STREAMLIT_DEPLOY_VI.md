# Hướng dẫn triển khai Streamlit Final

## Điều kiện trước khi deploy

1. Pipeline đã chạy trên máy bạn với seed/mẫu cuối cùng.
2. Audit đã được xem lại; các metric PARTIAL/ERROR/NOT_RUN không được biến thành 0.
3. Đã có các CSV processed canonical cần cho app:
   - `repository_country_metrics.csv`
   - `country_repository_comparison.csv`
   - `vietnam_vs_other_countries_comparison.csv`
   - `monthly_activity.csv`
   - `developer_activity_summary.csv`
   - `deduplication_audit.csv`
   - `collection_errors.csv`
   - `data_quality_report.csv`
4. Sau khi kiểm tra dữ liệu, commit các CSV processed này lên nhánh triển khai. Thư mục raw canonical và checkpoint được .gitignore vì chúng có thể lớn; **không** commit token hoặc file `.env`.

## Chạy local

Từ thư mục gốc của repository:

```powershell
python -m pip install -r requirements.txt
python run_pipeline.py --limit-repos 10
streamlit run app/streamlit_app.py
```

Lượt crawl 10 repository chỉ dùng để thử app và kiểm tra luồng dữ liệu, không phải số liệu Final. Nếu app đang báo thiếu CSV, kiểm tra đầu ra trong `data/processed/canonical/`.

## Deploy trên Streamlit Community Cloud

1. Mở https://share.streamlit.io và đăng nhập bằng GitHub.
2. Chọn **Create app**.
3. Chọn repository `HoangNH9x/github_developer_analytics`.
4. Chọn branch `rebuild-stage1-final` để test (hoặc branch Final đã được duyệt sau này).
5. Đặt App file path là `app/streamlit_app.py`.
6. Giữ dependency file tại root là `requirements.txt`; app phụ thuộc vào Streamlit, Pandas và Plotly.
7. Chọn URL/subdomain nếu muốn rồi deploy. Khi deploy thành công, Community Cloud hiển thị đường link `.streamlit.app` để chia sẻ.

Hướng dẫn chính thức của Streamlit: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app

## Nếu app chưa hiện biểu đồ

- Vào tab Chất lượng dữ liệu để xem trạng thái metric khi CSV đã có.
- Nếu app báo thiếu CSV, kiểm tra bạn đã commit đúng các file processed canonical lên đúng branch đang deploy chưa.
- Nếu báo lỗi dependency, kiểm tra log của app và đối chiếu với `requirements.txt`.
- Không đặt GitHub token vào app vì app chỉ đọc CSV đã xử lý; token chỉ cần khi chạy pipeline crawl trên máy thu thập.
- Khi cập nhật processed data, commit/push CSV mới để Cloud đọc lại.

## Bảo mật và giới hạn diễn giải

Đường link Streamlit có thể được chia sẻ cho giảng viên hoặc người khác; chỉ đưa lên những bảng processed đã được rà soát. Không commit raw event data nếu không cần thiết, không công bố token, và không diễn giải owner profile location như quốc gia đã được xác minh độc lập.
