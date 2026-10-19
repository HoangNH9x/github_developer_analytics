
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent

input_file = ROOT / "data" / "raw" / "developers_stage2.csv"
output_file = ROOT / "data" / "processed" / "developers_stage2_country.csv"

if not input_file.exists():
    raise SystemExit("Khong tim thay developers_stage2.csv")

df = pd.read_csv(input_file, encoding="utf-8-sig")

if "location" not in df.columns:
    raise SystemExit("File khong co cot location")

def normalize_country(location):
    if pd.isna(location) or not str(location).strip():
        return "Unknown"

    text = str(location).strip().casefold()

    # Viet Nam: dua tren location tu khai bao
    vietnam_terms = [
        "vietnam", "viet nam", "việt nam",
        "hanoi", "ha noi", "hà nội",
        "ho chi minh", "hồ chí minh",
        "saigon", "sài gòn", "da nang", "đà nẵng",
        "can tho", "cần thơ", "hai phong", "hải phòng",
        "quang ninh", "quảng ninh",
    ]

    if any(term in text for term in vietnam_terms):
        return "Vietnam"

    # Cac quoc gia/vung co the nhan dien tu location
    mappings = {
        "United States": [
            "united states", "u.s.a.", "usa",
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
            "united kingdom", "uk", "london",
            "england", "britain", "united kingdom",
        ],
        "Poland": ["poland", "warsaw"],
        "Hong Kong": ["hong kong"],
    }

    for country, terms in mappings.items():
        if any(term in text for term in terms):
            return country

    return "Other/Unknown"


df["country_or_region"] = df["location"].apply(normalize_country)

output_file.parent.mkdir(parents=True, exist_ok=True)

df.to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig",
)

print("=== KET QUA CHUAN HOA DEVELOPER ===")
print("Tong ho so:", len(df))
print("Login duy nhat:", df["login"].nunique())

print("\n=== SO LUONG THEO QUOC GIA/VUNG ===")
print(
    df["country_or_region"]
    .value_counts()
    .to_string()
)

print("\n=== TY LE VIET NAM ===")
vn_count = (df["country_or_region"] == "Vietnam").sum()
print("Tai khoan co location duoc gan Vietnam:", vn_count)

print("\nFile da luu:", output_file)
