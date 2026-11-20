"""Đóng gói đúng các mô-đun Python dùng chung cho serverless API (không sao chép dữ liệu/Secret)."""
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / "web" / "serverpkg" / "neopulse"
for relative in ["__init__.py", "timeutil.py", "analytics/__init__.py", "analytics/company.py",
                 "analytics/formatting.py", "analytics/charting.py", "analytics/telegram_cloud.py", "analytics/telegram_store.py", "analytics/company_remote.py"]:
    source = root / "src" / "neopulse" / relative
    output = target / relative
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, output)
# Next.js moves public assets to its static output before Python packaging.
for name, relative in {"catalog.json": "company/catalog.json", "field-aliases.json": "company/field-aliases.json", "VNINDEX.json": "charts/VNINDEX.json"}.items():
    output = target.parent / "data" / name
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / "web/public/data" / relative, output)
print("Serverless bundle prepared (source and public reference data; no Secrets)")
