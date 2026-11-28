"""Đóng gói bài nộp: K244141653_PhamNgocThienAn_NEOAPI_FinTech.zip.

  python tools/package_submission.py [--tag v1.0.0] [--out out/submission]

Nội dung:
  * `git archive` của tag (mã nguồn, docs, report/data, data_sample MÔ PHỎNG đã commit);
  * data_sample/bars_ssi_<phiên>.csv: chỉ báo TỔNG HỢP theo thanh 1 phút của một phiên SSI thật, sinh từ SQLite
    (chỉ đọc). Không có giá hay sổ lệnh thô từng tick: bỏ mọi cột giá/khối lượng từng mức.
Tự kiểm: zip không chứa .env, *.sqlite, raw_dump/, out/, node_modules, .vercel; in danh sách tệp và dung lượng.
"""
from __future__ import annotations

import argparse
import io
import subprocess
import sys
import zipfile
from pathlib import Path

NAME = "K244141653_PhamNgocThienAn_NEOAPI_FinTech"
ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PARTS = {"raw_dump", "out", "node_modules", ".vercel", ".review", ".venv"}
# cột tổng hợp theo thanh; KHÔNG có bid/ask/last/mid hay khối lượng từng mức giá
BAR_COLS = ["trading_date", "symbol", "bar", "spread_bps", "obi1", "obi3", "obi_w", "micro_dev_bps", "pressure",
            "band_pos", "pct_change", "ret", "vol", "val", "f_net_val", "rvol_bar"]


def forbidden(name: str) -> bool:
    p = Path(name)
    base = p.name.lower()
    return (base == ".env" or (base.startswith(".env") and base != ".env.example") or base.endswith((".sqlite", ".sqlite-wal", ".sqlite-shm"))
            or any(part in FORBIDDEN_PARTS for part in p.parts))


def bars_csv(db_path: Path, day: str | None) -> tuple[str, bytes]:
    sys.path.insert(0, str(ROOT / "src"))
    from neopulse.analytics.reportdata import ReadOnlyStorage
    from neopulse.analytics.view import build_view
    db = ReadOnlyStorage(db_path)
    try:
        day = day or db.trading_dates("ssi")[-1]
        b = build_view(db, "ssi", day, "VN30").bars
    finally:
        db.close()
    out = b[[c for c in BAR_COLS if c in b.columns]].copy()
    out["bar"] = out["bar"].map(lambda t: t.isoformat())
    return f"data_sample/bars_ssi_{day}.csv", out.round(6).to_csv(index=False).encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="v1.0.0")
    ap.add_argument("--out", default="out/submission")
    ap.add_argument("--db", default="data/neopulse.sqlite")
    ap.add_argument("--day", help="phiên SSI cho bảng thanh tổng hợp (mặc định: phiên mới nhất)")
    a = ap.parse_args(argv)
    archive = subprocess.run(["git", "archive", "--format=zip", f"--prefix={NAME}/", a.tag], cwd=ROOT,
                             capture_output=True, check=True).stdout
    out_dir = ROOT / a.out
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{NAME}.zip"
    with zipfile.ZipFile(io.BytesIO(archive)) as src, zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            dst.writestr(info, src.read(info))
        if (ROOT / a.db).exists():
            rel, data = bars_csv(ROOT / a.db, a.day)
            dst.writestr(f"{NAME}/{rel}", data)
        else:
            print(f"Không thấy {a.db}: bỏ qua bảng thanh tổng hợp.")
    with zipfile.ZipFile(target) as z:
        infos = [i for i in z.infolist() if not i.is_dir()]
        bad = [i.filename for i in infos if forbidden(i.filename.split("/", 1)[-1])]
        for i in infos:
            print(f"{i.file_size:>12,}  {i.filename}")
        print(f"\n{len(infos)} tệp · nén {target.stat().st_size / 1e6:.2f} MB · {target}")
    if bad:
        target.unlink()
        print("LỖI: zip chứa tệp cấm, đã xóa zip:", *bad, sep="\n  ")
        return 1
    print("Kiểm tra: không có .env, *.sqlite, raw_dump/, out/, node_modules, .vercel.")
    return 0


if __name__ == "__main__":
    assert forbidden(".env") and forbidden("data/neopulse.sqlite") and forbidden("web/node_modules/x.js")
    assert forbidden("out/a.log") and not forbidden(".env.example") and not forbidden("src/neopulse/data/ingest.py")
    sys.exit(main())
