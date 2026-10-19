
from pathlib import Path

import pandas as pd

# File raw duoc giu nguyen
input_file = Path("data/raw/commits_stage2.csv")

# Luu ban da lam sach vao thu muc processed
output_file = Path("data/processed/commits_stage2_clean.csv")

if not input_file.exists():
    raise SystemExit("Khong tim thay file commits_stage2.csv")

df = pd.read_csv(
    input_file,
    encoding="utf-8-sig",
    dtype={"repository": "string", "sha": "string"}
)

print("So dong truoc khi lam sach:", len(df))

# Loai bo ky tu BOM khoi cac cot dang text
text_columns = df.select_dtypes(
    include=["object", "string"]
).columns

for column in text_columns:
    df[column] = df[column].map(
        lambda value: (
            value.replace("\ufeff", "")
            if isinstance(value, str)
            else value
        )
    )

# Loai bo commit trung theo repository va SHA
df = df.drop_duplicates(
    subset=["repository", "sha"]
)

output_file.parent.mkdir(
    parents=True,
    exist_ok=True
)

df.to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig"
)

# Kiem tra lai ket qua
bom_count = 0

for column in text_columns:
    bom_count += (
        df[column]
        .astype("string")
        .str.contains("\ufeff", regex=False, na=False)
        .sum()
    )

print("\n=== KET QUA LAM SACH ===")
print("So dong sau khi lam sach:", len(df))
print("So repository:", df["repository"].nunique())
print("So SHA duy nhat:", df["sha"].nunique())
print("So dong trung lap:", df.duplicated(
    subset=["repository", "sha"]
).sum())
print("So gia tri con BOM:", bom_count)
print("File da luu:", output_file)
s