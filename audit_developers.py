
from pathlib import Path

import pandas as pd

file_path = Path("data/raw/developers_stage2.csv")

if not file_path.exists():
    raise SystemExit("Khong tim thay developers_stage2.csv")

df = pd.read_csv(file_path, encoding="utf-8-sig")

print("=== KIEM TRA DEVELOPER ===")
print("Tong so ho so:", len(df))

if "login" in df.columns:
    print("Login duy nhat:", df["login"].nunique())
    print("Login bi thieu:", df["login"].isna().sum())

if "type" in df.columns:
    print("\n=== LOAI TAI KHOAN ===")
    print(df["type"].fillna("Unknown").value_counts())

if "location" in df.columns:
    location = df["location"].fillna("").astype(str).str.strip()
    has_location = location.ne("")

    print("\n=== DO PHU DIA DIEM ===")
    print("Co khai bao location:", int(has_location.sum()))
    print("Khong khai bao location:", int((~has_location).sum()))
    print("Ty le co location: {:.2f}%".format(
        has_location.mean() * 100
    ))

    print("\n=== 30 LOCATION PHO BIEN ===")
    print(
        location[has_location]
        .value_counts()
        .head(30)
        .to_string()
    )

    # Chi tim tai khoan co dau hieu lien quan den Viet Nam.
    # Day la danh sach ung vien can kiem tra, chua phai ket luan quoc gia.
    vn_pattern = (
        r"vietnam|viet nam|việt nam|hanoi|ha noi|hà nội|"
        r"ho chi minh|hồ chí minh|saigon|sài gòn|"
        r"da nang|đà nẵng|can tho|cần thơ|"
        r"hai phong|hải phòng|quang ninh|quảng ninh"
    )

    candidates = df[
        location.str.contains(vn_pattern, case=False, regex=True)
    ].copy()

    print("\n=== UNG VIEN LOCATION LIEN QUAN VIET NAM ===")
    print("So ho so can xem lai:", len(candidates))

    columns = [
        column for column in ["login", "name", "location", "type"]
        if column in candidates.columns
    ]

    if not candidates.empty:
        print(candidates[columns].head(30).to_string(index=False))
    else:
        print("Chua tim thay location khop tu khoa.")

print("\nDa kiem tra xong. Khong thay doi file goc.")
