
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

# =====================================
# CAU HINH
# =====================================

PROJECT_DIR = Path(__file__).resolve().parent

COLLECTOR_FILE = PROJECT_DIR / "collect_commits_paged.py"
COMMITS_FILE = PROJECT_DIR / "data" / "raw" / "commits_stage2.csv"

TARGET_COMMITS = 20_000
MAX_ROUNDS = 15
WAIT_BETWEEN_ROUNDS = 15

# =====================================
# HAM DEM COMMIT DUY NHAT
# =====================================

def count_commits():
    if not COMMITS_FILE.exists():
        return 0

    df = pd.read_csv(
        COMMITS_FILE,
        usecols=["repository", "sha"],
        dtype=str
    )

    return len(
        df.dropna(subset=["repository", "sha"])
        .drop_duplicates(subset=["repository", "sha"])
    )


# =====================================
# KIEM TRA FILE THU THAP
# =====================================

if not COLLECTOR_FILE.exists():
    raise SystemExit(
        f"Khong tim thay file: {COLLECTOR_FILE.name}"
    )

print("=== GITHUB ANALYTICS STAGE 2 ===")
print("Muc tieu commits:", TARGET_COMMITS)
print("So vong toi da:", MAX_ROUNDS)

# =====================================
# TU DONG CHAY CAC DOT
# =====================================

for round_number in range(1, MAX_ROUNDS + 1):

    before = count_commits()

    if before >= TARGET_COMMITS:
        print("\nDa dat muc tieu commits trung gian!")
        break

    print(f"\n=== DOT {round_number}/{MAX_ROUNDS} ===")
    print("Commit hien co:", before)

    try:
        result = subprocess.run(
            [sys.executable, str(COLLECTOR_FILE)],
            cwd=PROJECT_DIR,
            check=False
        )
    except KeyboardInterrupt:
        print("\nDa yeu cau dung chuong trinh.")
        break

    after = count_commits()

    print("Commit sau dot:", after)
    print("Commit moi:", after - before)

    if after >= TARGET_COMMITS:
        print("\nDa dat muc tieu commits trung gian!")
        break

    if after <= before:
        print(
            "Khong co tien trien moi. "
            "Tam dung de tranh lap request vo ich."
        )
        break

    if result.returncode != 0:
        print("Bo thu thap ket thuc voi ma loi.")
        break

    if round_number < MAX_ROUNDS:
        print(
            f"Cho {WAIT_BETWEEN_ROUNDS} giay "
            "truoc dot tiep theo..."
        )
        time.sleep(WAIT_BETWEEN_ROUNDS)

print("\n=== TONG KET ===")
print("Tong commit duy nhat:", count_commits())
print("File du lieu:", COMMITS_FILE)
print("Checkpoint duoc quan ly boi collect_commits_paged.py")
