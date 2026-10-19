
from pathlib import Path
import re

file_path = Path("data/raw/issues_stage2.csv")

if not file_path.exists():
    raise SystemExit(f"Khong tim thay file: {file_path}")

content = file_path.read_bytes()

pattern = rb"sk-or-v1-[A-Za-z0-9_-]{20,}"

cleaned, count = re.subn(
    pattern,
    b"[REDACTED_OPENROUTER_KEY]",
    content,
)

file_path.write_bytes(cleaned)

remaining = len(re.findall(pattern, cleaned))

print("So chuoi key da che:", count)
print("So chuoi key con lai:", remaining)
print("Da cap nhat file Issues.")
