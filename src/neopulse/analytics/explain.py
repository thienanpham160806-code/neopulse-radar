"""Diễn giải bản tin: mặc định bằng MẪU CÂU xác định; tùy chọn dùng mô hình ngôn ngữ có rào chắn.

Nguyên tắc (mục 13 của đề): mô hình ngôn ngữ không được là nguồn sự thật.
  1. `build_facts` rút MỌI con số từ `SessionView` - đây là nguồn duy nhất.
  2. `template_summary` dựng câu từ facts: luôn chạy được, không cần mạng, không thể bịa số.
  3. `llm_summary` (nếu có LLM_API_KEY): chỉ đưa facts cho mô hình, rồi `numbers_grounded` kiểm tra mọi con
     số trong câu trả lời đều có trong facts; sai một số => BỎ câu trả lời, quay về mẫu câu.
Không sinh khuyến nghị mua/bán: prompt cấm, và `contains_advice` chặn lần nữa ở đầu ra.
"""
from __future__ import annotations

import logging
import math
import re

import httpx

from ..config import Settings
from ..finance.pulse import COMPONENT_NAMES
from .view import SessionView, fmt_money

log = logging.getLogger(__name__)
ADVICE_PATTERNS = re.compile(r"\b(nên mua|nên bán|khuyến nghị mua|khuyến nghị bán|hãy mua|hãy bán|chốt lời|"
                             r"cắt lỗ|giải ngân|mua vào|bán ra ngay)\b", re.I)
_NUM = re.compile(r"(?<![\w.])[-+−]?\d+(?:[.,]\d+)*")


def _r(x, nd=2):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), nd)


def build_facts(v: SessionView) -> dict:
    f: dict = {"phiên": v.trading_date, "nguồn": "MÔ PHỎNG" if v.is_simulated else "NEO API",
               "chỉ_số": v.index_code}
    if v.index_row:
        r = v.index_row
        f.update(giá_trị_chỉ_số=_r(r.get("value")), thay_đổi_pct=_r(r.get("pct_change")),
                 số_mã_tăng=_r(r.get("advances"), 0), số_mã_giảm=_r(r.get("declines"), 0),
                 số_mã_trần=_r(r.get("n_ceiling"), 0), số_mã_sàn=_r(r.get("n_floor"), 0),
                 gtgd_tỷ=_r((r.get("total_value") or float("nan")) / 1e9, 0))
    if v.pulse and not math.isnan(v.pulse.score):
        f.update(điểm_nhịp=v.pulse.score, trạng_thái=v.pulse.label,
                 thành_phần={COMPONENT_NAMES[k]: _r(x) for k, x in v.pulse.components.items()})
    if v.foreign_summary:
        f.update(nn_ròng_tỷ=_r(v.foreign_summary.get("net_val", float("nan")) / 1e9, 1),
                 nn_số_mã_mua_ròng=v.foreign_summary.get("n_net_buy"),
                 nn_số_mã_bán_ròng=v.foreign_summary.get("n_net_sell"))
    if len(v.foreign):
        f["nn_mua_ròng_mạnh_nhất"] = v.foreign.index[0]
        f["nn_bán_ròng_mạnh_nhất"] = v.foreign.index[-1]
    if v.basis_state and not math.isnan(v.basis_state.get("basis", float("nan"))):
        f.update(basis_điểm=_r(v.basis_state["basis"]), basis_trạng_thái=v.basis_state["label"],
                 ngày_tới_đáo_hạn=_r(v.basis_state.get("dtm"), 0))
    if len(v.alerts):
        f["số_cảnh_báo"] = int(len(v.alerts))
        f["số_cảnh_báo_cao"] = int((v.alerts["severity"] == "CAO").sum())
        f["mã_nhiều_cảnh_báo"] = v.alerts["symbol"].value_counts().head(3).index.tolist()
    if v.divergence:
        f["phân_kỳ"] = v.divergence
    return {k: x for k, x in f.items() if x is not None}


_SEP_IN_NUMBER = re.compile(r"(?<=\d)[.,](?=\d)")


def vn_digits(text: str) -> str:
    """Đổi định dạng số kiểu Anh (1,933.61) sang kiểu Việt (1.933,61): chỉ đổi dấu nằm GIỮA hai chữ số,
    nên dấu phẩy câu (luôn có khoảng trắng sau) không bị đụng."""
    return _SEP_IN_NUMBER.sub(lambda m: "," if m.group(0) == "." else ".", text)


def template_summary(v: SessionView) -> list[str]:
    """Danh sách câu nhận định, mỗi câu gắn với số liệu cụ thể."""
    out: list[str] = []
    if v.status == "no_data" or v.pulse is None:
        return ["Chưa có dữ liệu để nhận định."]
    r, p = v.index_row or {}, v.pulse
    if not math.isnan(p.score):
        drivers = sorted(p.components.items(), key=lambda kv: -abs(kv[1]))
        top = ", ".join(f"{COMPONENT_NAMES[k]} ({x:+.2f})" for k, x in drivers[:2])
        out.append(f"Điểm nhịp thị trường {p.score:.1f}/100 - {p.label}. Thành phần chi phối: {top}.")
        if p.missing:
            out.append("Thiếu dữ liệu cho: " + ", ".join(COMPONENT_NAMES[m] for m in p.missing)
                       + " - điểm được tính trên các thành phần còn lại.")
    if r.get("value") is not None:
        out.append(f"{v.index_code} ở {r['value']:,.2f} ({r.get('pct_change', float('nan')):+.2f}%), "
                   f"{r.get('advances', 0):.0f} mã tăng / {r.get('declines', 0):.0f} mã giảm, "
                   f"{r.get('n_ceiling', 0):.0f} trần / {r.get('n_floor', 0):.0f} sàn; "
                   f"giá trị giao dịch {fmt_money(r.get('total_value'))}.")
    if v.divergence:
        out.append("Phân kỳ: " + v.divergence)
    fs = v.foreign_summary
    if fs and not math.isnan(fs.get("net_val", float("nan"))):
        side = "mua ròng" if fs["net_val"] > 0 else "bán ròng"
        out.append(f"Khối ngoại {side} {fmt_money(abs(fs['net_val']))} trong rổ theo dõi "
                   f"({fs['n_net_buy']} mã mua ròng, {fs['n_net_sell']} mã bán ròng); "
                   f"mua ròng mạnh nhất {v.foreign.index[0]}, bán ròng mạnh nhất {v.foreign.index[-1]}.")
    bs = v.basis_state
    if bs and not math.isnan(bs.get("basis", float("nan"))):
        z = f", z = {bs['z']:+.1f} so với trong phiên" if not math.isnan(bs.get("z", float("nan"))) else ""
        out.append(f"{bs['symbol']}: basis {bs['basis']:+.2f} điểm ({bs['basis_pct']:+.2f}%) - {bs['label']}, "
                   f"còn {bs['dtm']:.0f} ngày tới đáo hạn{z}.")
    if len(v.alerts):
        hi = v.alerts[v.alerts["severity"] == "CAO"]
        names = ", ".join(hi["symbol"].value_counts().head(5).index) if len(hi) else "không có"
        out.append(f"{len(v.alerts)} cảnh báo trong phiên, {len(hi)} mức CAO (mã: {names}).")
    return [vn_digits(x) for x in out]


def numbers_grounded(text: str, facts: dict, tol: float = 0.011) -> tuple[bool, list[str]]:
    """Mọi con số trong `text` phải khớp (sai số làm tròn) với một con số trong `facts`."""
    def candidates(token: str) -> set[float]:
        """Mọi cách đọc hợp lý của một chuỗi số: 22.510 có thể là 22,51 (kiểu Anh) hoặc 22 510 (kiểu Việt)."""
        t = token.replace("−", "-")
        forms = {t.replace(",", ""), t.replace(".", "").replace(",", "."), t.replace(",", "."), t.replace(".", "")}
        out = set()
        for f in forms:
            try:
                out.add(abs(float(f)))
            except ValueError:
                pass
        return out

    allowed = {100.0, 0.0}
    for m in _NUM.findall(repr(facts)):  # facts là số Python: chỉ có dấu chấm thập phân
        try:
            allowed.add(abs(float(m)))
        except ValueError:
            pass
    bad = [m for m in _NUM.findall(text)
           if not any(abs(c - a) <= tol * max(1.0, a) for c in candidates(m) for a in allowed)]
    return (not bad), bad


def contains_advice(text: str) -> bool:
    return bool(ADVICE_PATTERNS.search(text))


SYSTEM_PROMPT = (
    "Bạn viết bản tóm tắt thị trường chứng khoán Việt Nam bằng tiếng Việt, 4-6 câu, giọng trung tính. "
    "CHỈ dùng số liệu trong khối FACTS; không thêm số, không suy đoán nguyên nhân ngoài dữ liệu, "
    "không dự báo, không khuyến nghị mua/bán. Nếu FACTS ghi nguồn MÔ PHỎNG, câu đầu tiên phải nói rõ "
    "đây là dữ liệu mô phỏng.")


def llm_summary(v: SessionView, settings: Settings, *, transport: httpx.BaseTransport | None = None) -> dict:
    """Trả về {'text', 'engine', 'rejected_reason'}; luôn có văn bản (rơi về mẫu câu khi cần)."""
    fallback = " ".join(template_summary(v))
    if not (settings.llm_api_key and settings.llm_model):
        return {"text": fallback, "engine": "template", "rejected_reason": None}
    facts = build_facts(v)
    try:
        with httpx.Client(timeout=30, transport=transport) as c:
            r = c.post("https://api.anthropic.com/v1/messages",
                       headers={"x-api-key": settings.llm_api_key, "anthropic-version": "2023-06-01",
                                "content-type": "application/json"},
                       json={"model": settings.llm_model, "max_tokens": 500, "system": SYSTEM_PROMPT,
                             "messages": [{"role": "user", "content": f"FACTS = {facts!r}"}]})
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text").strip()
    except (httpx.HTTPError, ValueError, KeyError) as e:
        log.warning("Gọi mô hình ngôn ngữ thất bại (%s) - dùng mẫu câu.", type(e).__name__)
        return {"text": fallback, "engine": "template", "rejected_reason": f"lỗi gọi API: {type(e).__name__}"}
    ok, bad = numbers_grounded(text, facts)
    if not text or not ok:
        return {"text": fallback, "engine": "template", "rejected_reason": f"số không có trong dữ liệu: {bad[:5]}"}
    if contains_advice(text):
        return {"text": fallback, "engine": "template", "rejected_reason": "đầu ra chứa ngôn ngữ khuyến nghị"}
    return {"text": text, "engine": f"llm:{settings.llm_model}", "rejected_reason": None}
