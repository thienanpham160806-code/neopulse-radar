"""Làm mới sự kiện và tin tức (kèm link bài gốc) cho mọi hồ sơ doanh nghiệp đã xuất, không tải lại BCTC.

Cập nhật cả dữ liệu thô data/company/raw/<MÃ>.json nếu có, để lần dựng lại `neopulse company` giữ kết quả mới.
"""
import json
import re
import sys
import time
from pathlib import Path

import httpx

from neopulse.analytics.company import fetch_disclosures

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT / "web/public/data/company"
    raw_dir = ROOT / "data/company/raw"
    only = {a.upper() for a in sys.argv[1:]}  # trống = mọi mã
    paths = [p for p in sorted(out.glob("*.json")) if re.fullmatch(r"[A-Z][A-Z0-9]{1,9}", p.stem) and (not only or p.stem in only)]
    with httpx.Client(timeout=40) as client:
        for i, path in enumerate(paths, 1):
            report = json.loads(path.read_text(encoding="utf-8"))
            if report.get("symbol") != path.stem:
                continue
            got = fetch_disclosures(path.stem, client)
            for target in (path, raw_dir / path.name):
                if not target.exists():
                    continue
                data = report if target == path else json.loads(target.read_text(encoding="utf-8"))
                # Nguồn lỗi tạm thời: giữ danh sách cũ thay vì xóa.
                data.update({k: v for k, v in got.items() if v})
                if target == path:
                    data["notes"] = [n.replace("chưa có cổ đông, lãnh đạo hoặc tin/sự kiện", "chưa có cổ đông và lãnh đạo")
                                     for n in data.get("notes", [])]
                tmp = target.with_suffix(".tmp")
                tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
                tmp.replace(target)
            print(f"[{i}/{len(paths)}] {path.stem}: {len(got['events'])} sự kiện, {len(got['news'])} tin", flush=True)
            time.sleep(2)  # Vietcap trả 418 khi gọi dồn


if __name__ == "__main__":
    main()
