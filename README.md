# GitHub Developer Analytics

## 1. Giới thiệu

GitHub Developer Analytics là project phân tích dữ liệu hoạt động của các repository trên GitHub.

Project sử dụng GitHub API để thu thập dữ liệu về:

- Repository
- Issues
- Commits
- Developers / Authors

Sau đó dữ liệu được lưu dưới dạng CSV, kiểm tra chất lượng, làm sạch, phân tích bằng Pandas và trực quan hóa bằng Matplotlib.

---

## 2. Mục tiêu của Project

Project nhằm phân tích:

- Mức độ phổ biến của các repository thông qua Stars và Forks.
- Tình trạng Issues của các repository.
- Mức độ thảo luận thông qua số lượng Comments.
- Hoạt động Commit của các Developers/Authors.
- Một số xu hướng và đặc điểm nổi bật trong dataset.

---

## 3. Nguồn dữ liệu

Dữ liệu được thu thập trực tiếp từ GitHub REST API.

Các repository được sử dụng trong project gồm:

- facebook/react
- vuejs/vue
- angular/angular
- vercel/next.js
- django/django
- pallets/flask
- pytorch/pytorch
- tensorflow/tensorflow
- microsoft/vscode
- kubernetes/kubernetes

Dữ liệu được thu thập bằng Python và thư viện `requests`.

---

## 4. Quy trình xử lý dữ liệu

Project được thực hiện theo quy trình:

```text
GitHub API
    ↓
Raw Data
    ↓
CSV
    ↓
Data Quality Check
    ↓
Data Cleaning
    ↓
Clean CSV
    ↓
EDA
    ↓
Data Visualization
    ↓
Insights
    ↓
Report