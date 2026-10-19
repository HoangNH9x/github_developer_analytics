
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

FILES = [
    RAW / "developers_stage2.csv",
    RAW / "vietnam_developer_profiles.csv",
    RAW / "developers_activity_profiles.csv",
]
OUTPUT_FILE = PROCESSED / "developers_stage2_master.csv"


def normalize_country(location):
    if pd.isna(location) or not str(location).strip():
        return "Unknown"

    text = str(location).strip().casefold()

    # Vietnam: dua tren dia diem tu khai bao
    vietnam_terms = [
        "vietnam", "viet nam", "việt nam",
        "hanoi", "ha noi", "hà nội",
        "ho chi minh", "hồ chí minh",
        "saigon", "sài gòn",
        "da nang", "đà nẵng",
        "can tho", "cần thơ",
        "hai phong", "hải phòng",
        "quang ninh", "quảng ninh",
    ]

    if any(term in text for term in vietnam_terms):
        return "Vietnam"

    mappings = {
        "United States": [
            "united states", "u.s.a", "usa",
            "new york", "san francisco", "seattle",
            "austin, tx", "los angeles", "california",
        ],
        "Canada": ["canada", "toronto", "vancouver"],
        "Germany": ["germany", "berlin"],
        "Australia": ["australia", "sydney", "melbourne"],
        "India": ["india", "bengaluru", "bangalore"],
        "China": ["china", "中国", "上海", "shanghai", "北京", "beijing"],
        "France": ["france", "paris"],
        "Brazil": ["brazil", "brasil"],
        "Singapore": ["singapore"],
        "United Kingdom": [
            "united kingdom", "london, uk",
            "england", "britain",
        ],
        "Poland": ["poland", "warsaw"],
        "Hong Kong": ["hong kong"],
    }

    for country, terms in mappings.items():
        if any(term in text for term in terms):
            return country

    return "Other/Unknown"


# 1. Doc cac file hien co
frames = []

for file_path in FILES:
    if file_path.exists():
        df = pd.read_csv(
            file_path,
            encoding="utf-8-sig",
            dtype={"login": "string"},
        )

        if "login" not in df.columns:
            print("Bo qua file thieu cot login:", file_path.name)
            continue

        df["source_file"] = file_path.name
        frames.append(df)
        print(f"Da doc {file_path.name}: {len(df)} ho so")
    else:
        print("Khong tim thay file:", file_path.name)

if not frames:
    raise SystemExit("Khong co file Developer hop le!")

# 2. Gop va loai trung theo login
combined = pd.concat(frames, ignore_index=True, sort=False)

combined["login"] = combined["login"].astype("string").str.strip()
combined = combined.dropna(subset=["login"])
combined = combined[
    combined["login"].str.len() > 0
].copy()

combined["login_key"] = combined["login"].str.lower()

# Neu mot tai khoan xuat hien trong hai file, uu tien ho so sau cung
combined = combined.drop_duplicates(
    subset=["login_key"],
    keep="last",
)

# 3. Chuan hoa location
combined["country_or_region"] = combined["location"].apply(
    normalize_country
)

# 4. Luu file master
PROCESSED.mkdir(parents=True, exist_ok=True)

combined.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig",
)

# 5. Bao cao
print("\n=== KET QUA DEVELOPER MASTER ===")
print("Tong login duy nhat:", combined["login_key"].nunique())
print("So dong:", len(combined))
print("Location bi thieu:", combined["location"].isna().sum())

if "type" in combined.columns:
    print("\n=== LOAI TAI KHOAN ===")
    print(combined["type"].fillna("Unknown").value_counts())

print("\n=== PHAN BO QUOC GIA/VUNG ===")
print(combined["country_or_region"].value_counts().to_string())

users = combined[
    combined["type"].astype("string").str.casefold() == "user"
] if "type" in combined.columns else combined.iloc[0:0]

print("\nSo ho so co type User:", len(users))
print(
    "So User gan Vietnam theo location:",
    (users["country_or_region"] == "Vietnam").sum()
)

print("\nFile da luu:", OUTPUT_FILE)
