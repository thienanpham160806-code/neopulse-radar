"""Ngành trong phiên: độ rộng, % thay đổi bình quân theo vốn hóa và đóng góp (ước lượng) vào chỉ số theo ngành.

Phân ngành: mã ICB 4 chữ số (chuẩn ICB cũ) do SSI trả trong `securitiesByBoard` (`icbCode`, `icbName`), gom về nhóm
ngành cấp 1 dễ đọc; tách riêng Ngân hàng / Bảo hiểm / Bất động sản / Dịch vụ tài chính vì các nhóm này chiếm phần lớn
VN30. Khi không có mã ICB, dùng danh sách mã tham chiếu tái sử dụng từ invest-system-phase2/config/sector_map.yaml
(`static_types`) - chỉ để PHÂN LOẠI, không làm dữ liệu số.

Công thức (mọi giá trị là % so với giá tham chiếu):
  vốn hóa_i     = số CP niêm yết_i x giá tham chiếu_i      (không điều chỉnh free-float -> ƯỚC LƯỢNG)
  % ngành       = Σ vốn hóa_i x %_i / Σ vốn hóa_i           (bình quân theo vốn hóa trong ngành)
  đóng góp_i    = vốn hóa_i / Σ vốn hóa rổ x %_i / 100 x chỉ số phiên trước   (điểm)
  đóng góp ngành = Σ đóng góp_i ; tổng các ngành ≈ thay đổi chỉ số (lệch do free-float/giới hạn tỷ trọng của VN30)
"""
from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources

import numpy as np
import pandas as pd

# ICB cũ: chữ số đầu = ngành cấp 1; tài chính (8xxx) tách theo 2 chữ số đầu
_FIN = {"83": "Ngân hàng", "85": "Bảo hiểm", "86": "Bất động sản", "87": "Dịch vụ tài chính"}
_L1 = {"0": "Dầu khí", "1": "Nguyên vật liệu", "2": "Công nghiệp", "3": "Hàng tiêu dùng", "4": "Y tế",
       "5": "Dịch vụ tiêu dùng", "6": "Viễn thông", "7": "Tiện ích", "9": "Công nghệ"}
# Tái sử dụng: invest-system-phase2/config/sector_map.yaml (static_types), cùng tác giả; chỉ giữ 4 nhóm tài chính
_STATIC = {
    "Ngân hàng": "VCB BID CTG TCB MBB ACB VPB HDB STB SHB TPB VIB LPB MSB OCB EIB SSB NAB BAB ABB VAB BVB KLB SGB PGB NVB VBB",
    "Dịch vụ tài chính": "SSI VND HCM VCI SHS MBS FTS BSI CTS VIX ORS AGR TVS BVS VDS APS EVS DSC VCK TCX",
    "Bảo hiểm": "BVH BMI PVI MIG BIC PTI PGI VNR ABI",
    "Bất động sản": "VHM VIC VRE NVL KDH DXG NLG PDR DIG KBC HDG CEO IDC SZC NTL HDC TCH DXS AGG SCR IJC KHG QCG BCM",
}
_STATIC_OF = {s: g for g, syms in _STATIC.items() for s in syms.split()}
UNKNOWN = "Chưa phân ngành"


def sector_of(symbol: str, icb_code: str | None = None) -> str:
    code = str(icb_code or "").strip()
    if len(code) == 4 and code.isdigit():
        return _FIN.get(code[:2], "Tài chính khác") if code[0] == "8" else _L1.get(code[0], UNKNOWN)
    return _STATIC_OF.get(symbol.upper(), UNKNOWN)


@lru_cache(maxsize=1)
def bundled_reference() -> dict[str, dict]:
    """Ảnh chụp tham chiếu đi kèm mã nguồn (ICB + số CP niêm yết của rổ VN30, lấy từ SSI REST 19/11/2026)."""
    text = resources.files("neopulse.data").joinpath("vn30_reference.json").read_text(encoding="utf-8")
    return json.loads(text)["symbols"]


def sector_table(latest: pd.DataFrame, reference: dict[str, dict], index_prev: float | None = None) -> pd.DataFrame:
    """Bảng theo ngành từ ảnh chụp mới nhất từng mã (cột symbol, last, ref, pct_change).

    `reference`: {mã: {icb_code, listed_share}}. Mã thiếu số CP niêm yết vẫn được đếm vào độ rộng nhưng không có trọng số."""
    cols = ["sector", "n", "n_up", "n_down", "n_flat", "pct_cap", "contrib_pts", "weight", "symbols"]
    if latest.empty:
        return pd.DataFrame(columns=cols)
    d = latest[["symbol", "last", "ref", "pct_change"]].copy()
    d = d[d["ref"].notna() & (d["ref"] > 0) & d["last"].notna()]
    if d.empty:
        return pd.DataFrame(columns=cols)
    ref_of = {k.upper(): v for k, v in reference.items()}
    d["sector"] = [sector_of(s, (ref_of.get(s) or {}).get("icb_code")) for s in d["symbol"]]
    d["shares"] = [float((ref_of.get(s) or {}).get("listed_share") or np.nan) for s in d["symbol"]]
    d["pct"] = (d["last"] - d["ref"]) / d["ref"] * 100
    d["cap"] = d["shares"] * d["ref"]
    total_cap = d["cap"].sum(min_count=1)
    rows = []
    for sec, g in d.groupby("sector"):
        w = g["cap"].where(g["cap"] > 0)
        has_w = w.notna().any()
        pct_cap = float((w * g["pct"]).sum() / w.sum()) if has_w else np.nan
        weight = float(w.sum() / total_cap) if has_w and total_cap and total_cap > 0 else np.nan
        contrib = (float((w / total_cap * g["pct"] / 100).sum() * index_prev)
                   if has_w and index_prev and total_cap and total_cap > 0 else np.nan)
        rows.append({"sector": sec, "n": int(len(g)), "n_up": int((g["pct"] > 0).sum()), "n_down": int((g["pct"] < 0).sum()),
                     "n_flat": int((g["pct"] == 0).sum()), "pct_cap": pct_cap, "contrib_pts": contrib, "weight": weight,
                     "symbols": sorted(g["symbol"].tolist())})
    return pd.DataFrame(rows, columns=cols).sort_values("contrib_pts", ascending=False, na_position="last").reset_index(drop=True)
