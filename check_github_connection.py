"""Safely verify that the local GitHub token is loaded and usable.

This script never prints the token value.
"""
from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    token = os.getenv("GITHUB_TOKEN", "").strip()

    if not token:
        print("[FAIL] Không tìm thấy GITHUB_TOKEN trong biến môi trường hoặc file .env.")
        print("Hãy kiểm tra file .env ở thư mục gốc, cùng cấp với pyproject.toml.")
        return 2
    if "PASTE_YOUR_GITHUB_TOKEN_HERE" in token or token.lower() in {"your_token", "token"}:
        print("[FAIL] GITHUB_TOKEN vẫn đang là placeholder, chưa phải token thật.")
        print("Mở file .env, thay giá trị mẫu bằng token vừa tạo ở GitHub rồi lưu file.")
        return 2

    print("[OK] Đã tìm thấy GITHUB_TOKEN (giá trị được giữ bí mật).")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "github-developer-analytics-student-project",
    }
    session = requests.Session()
    for label, url in [
        ("Xác thực token", "https://api.github.com/user"),
        ("Repository công khai thử nghiệm", "https://api.github.com/repos/cft0808/edict"),
    ]:
        try:
            response = session.get(url, headers=headers, timeout=20)
        except requests.RequestException as exc:
            print(f"[FAIL] {label}: lỗi kết nối mạng/TLS: {exc}")
            return 3

        print(f"[INFO] {label}: HTTP {response.status_code}")
        if response.ok:
            print(f"[OK] {label} thành công.")
            continue

        message = ""
        try:
            message = str(response.json().get("message", ""))
        except ValueError:
            message = response.text[:200]
        print(f"[FAIL] API message: {message or 'không có thông báo'}")
        if response.status_code == 401:
            print("Gợi ý: token sai, hết hạn, bị thu hồi hoặc chưa được lưu đúng trong .env.")
        elif response.status_code == 403:
            print("Gợi ý: có thể chạm giới hạn API hoặc token bị hạn chế; kiểm tra rate-limit headers / thời gian reset.")
        elif response.status_code == 404:
            print("Gợi ý: xác nhận lại owner/repository; API thường trả 404 nếu repo không tồn tại hoặc không truy cập được.")
        return 4

    print("[SUCCESS] Token có thể gọi GitHub API. Có thể chạy lại smoke test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
