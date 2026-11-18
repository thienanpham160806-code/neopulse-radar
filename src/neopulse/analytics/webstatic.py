"""Snapshot tĩnh cho web: xuất JSON chỉ báo của một phiên vào web/public/data/ rồi (tùy chọn) triển khai lên Vercel.

Đây là đường triển khai MẶC ĐỊNH cho dữ liệu thật: không có kết nối thời gian thực, không tốn hạn mức Vercel Blob,
và dữ liệu SSI chỉ rời máy tác giả khi tác giả chủ động chạy `--deploy`.

  * Chỉ ĐỌC SQLite (ReadOnlyStorage) nên chạy song song với `neopulse record` an toàn.
  * Mọi chỉ báo do Python tính (build_view); web chỉ hiển thị.
  * `web/public/data/` bị .gitignore: dữ liệu thật không bao giờ vào git. Chỉ `web/public/sample/` (mô phỏng) được commit.
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import webexport as wx

log = logging.getLogger(__name__)

DEFAULT_OUT = "web/public/data"
DEFAULT_WEB_DIR = "web"
_URL = re.compile(r"https://[A-Za-z0-9.-]+\.vercel\.app\S*")


class StaticPublishError(Exception):
    """Lỗi xuất snapshot hoặc triển khai; thông báo không chứa bí mật."""


@dataclass
class StaticResult:
    entries: list[dict]
    out_dir: Path
    url: str | None = None


def deploy_web(web_dir: str | Path, runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
               which: Callable[[str], str | None] = shutil.which, timeout: float = 600) -> str | None:
    """Chạy `vercel --prod --yes` trong web/ và trả URL production (None nếu không đọc được từ đầu ra)."""
    exe = which("vercel")
    if not exe:
        raise StaticPublishError("Không tìm thấy lệnh `vercel`. Cài bằng `npm i -g vercel` và chạy `vercel login`.")
    d = Path(web_dir)
    if not (d / "package.json").exists():
        raise StaticPublishError(f"Thư mục web không hợp lệ: {d}")
    try:
        r = runner([exe, "--prod", "--yes"], cwd=str(d), capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise StaticPublishError(f"Không chạy được vercel ({type(e).__name__}).") from e
    text = f"{r.stdout or ''}\n{r.stderr or ''}"
    if r.returncode != 0:
        tail = " | ".join(ln.strip() for ln in text.strip().splitlines()[-3:])
        raise StaticPublishError(f"`vercel --prod` thất bại (mã {r.returncode}): {tail[:300]}")
    aliased = [ln for ln in text.splitlines() if "Aliased" in ln]
    urls = _URL.findall("\n".join(aliased)) or _URL.findall(text)
    return urls[-1].rstrip(".,)") if urls else None


def publish_static(db_path: str | Path, source: str, *, trading_date: str | None = None,
                   index_codes: list[str] | None = None, out_dir: str | Path = DEFAULT_OUT, all_dates: bool = False,
                   with_validation: bool = True, order_value: float = 500e6, deploy: bool = False,
                   web_dir: str | Path = DEFAULT_WEB_DIR,
                   deployer: Callable[[str | Path], str | None] = deploy_web) -> StaticResult:
    """Xuất snapshot vào `out_dir` (latest.json, latest_<chỉ số>.json, sessions/, index.json) rồi tùy chọn triển khai."""
    try:
        db = wx.ReadOnlyStorage(db_path)
    except FileNotFoundError as e:
        raise StaticPublishError(str(e)) from e
    try:
        dates = db.trading_dates(source)
        if not dates:
            raise StaticPublishError(f"Chưa có dữ liệu cho nguồn '{source}' trong {db_path}.")
        if trading_date and trading_date not in dates:
            raise StaticPublishError(f"Không có phiên {trading_date} (nguồn '{source}'). Các phiên có: {', '.join(dates[-8:])}")
        entries = wx.export_to_dir(db, source, out_dir, trading_date=trading_date, index_codes=index_codes,
                                   all_dates=all_dates, with_validation=with_validation, order_value=order_value,
                                   snapshot=True)
    finally:
        db.close()
    if not entries:
        raise StaticPublishError("Không xuất được tệp nào.")
    url = deployer(web_dir) if deploy else None
    return StaticResult(entries, Path(out_dir), url)
