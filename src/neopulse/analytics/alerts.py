"""Bộ quy tắc cảnh báo có mức ưu tiên, thời gian nguội (cooldown) và khóa chống lặp.

Quy tắc          Điều kiện                                              Cơ sở ngưỡng
volume_spike     RVOL thanh >= 5 (có KL nền) hoặc z_vol >= 3,5           RVOL: ngân sách cảnh báo; z: Iglewicz & Hoaglin
spread_blowout   spread (số bước giá HOSE) >= 3 và > phân vị 95% của    spread rời rạc theo bước giá nên đo bằng bước;
                 chính mã trên các thanh trước trong phiên)              MAD ~ 0 làm z vô nghĩa
price_jump       |z_ret| >= 3,5                                         thống kê
foreign_flow     cửa sổ 3 thanh: NN ròng khác 0, chiếm >= 30% GT khớp,   phân phối dồn về 0, room NN về theo cục
                 |ròng| >= phân vị 99% các cửa sổ có NN trước của mã     ~1 lần/phút; không dùng z
book_pressure    |OBI_3| >= 0,6 cùng dấu >= 5 thanh liền nhau            OBI=0,6 <=> một bên dày gấp 4 lần bên kia
near_limit       |band_pos| >= 0,9                                      quy tắc biên độ trần/sàn của sàn
Mức ưu tiên: CAO nếu >= 2 quy tắc cùng nổ trên một mã trong một thanh hoặc giá trị của volume_spike/price_jump
>= CAO_VALUE; còn lại TRUNG BÌNH, riêng near_limit/book_pressure là THẤP khi đứng một mình. spread_blowout và
foreign_flow đo bằng đơn vị riêng (bước giá, tỷ trọng) nên chỉ CAO khi đi cùng quy tắc khác.
Ngưỡng RVOL 5, 3 bước giá + phân vị 95%, khối ngoại phân vị 99% trên cửa sổ 3 thanh, 5 thanh OBI và CAO_VALUE 10 chọn ngày 28/11/2026 CHỈ trên 4 phiên
trong mẫu 19, 20, 23, 25/11 theo ngân sách cảnh báo (CAO <= 1, mỗi quy tắc <= 2 trên một mã một phiên; lấy cấu hình ít chặt nhất
đạt ngân sách và giữ độ thu hồi mô phỏng >= 0,8); 26-27/11 chỉ để báo cáo ngoài mẫu. Mọi lần thử, kể cả phương án bị loại: docs/calibration_log.md.
volume_spike bỏ thanh 09:15 (khớp ATO) và 14:45 (khớp ATC): khối lượng đấu giá lớn theo cấu trúc phiên, không phải
bất thường.
Cảnh báo là tín hiệu "đáng xem", không phải khuyến nghị mua/bán.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..finance.microstructure import grid_ticks
from ..finance.rvol import RVOL_SPIKE
from .anomaly import Z_CAP, Z_THRESHOLD, score_bars

OBI_EXTREME = 0.6
OBI_PERSIST = 5
NEAR_LIMIT = 0.9
FOREIGN_MIN_SHARE = 0.30
FOREIGN_Q = 0.99
FOREIGN_WINDOW = 3  # thanh; room NN về theo cục nên tỷ trọng 1 thanh hay > 100% (12% số thanh trong mẫu, 3 thanh: 5%)
SPREAD_MIN_TICKS = 3.0
SPREAD_Q = 0.95
HIST_MIN = 20  # số giá trị trước (cùng mã, cùng phiên) tối thiểu để tính phân vị riêng của mã
CAO_VALUE = 10.0
AUCTION_BARS = ("09:15", "14:45")  # thanh chứa lần khớp ATO / ATC (thanh = floor của thời điểm nhận)
NO_VALUE_ESCALATION = ("spread_blowout", "foreign_flow")  # đơn vị riêng, chỉ CAO khi >= 2 quy tắc
RULE_NAMES = {"volume_spike": "Khối lượng tăng bất thường", "spread_blowout": "Độ chênh giá mua-bán giãn rộng",
              "price_jump": "Giá biến động đột ngột", "foreign_flow": "Khối ngoại giao dịch bất thường",
              "book_pressure": "Mất cân bằng sổ lệnh kéo dài", "near_limit": "Sát trần/sàn"}


@dataclass(frozen=True)
class AlertConfig:
    z: float = Z_THRESHOLD
    cooldown_bars: int = 10
    window: int = 60
    min_periods: int = 20


def detect(bars: pd.DataFrame, cfg: AlertConfig | None = None, source: str = "") -> pd.DataFrame:
    """Chạy toàn bộ quy tắc trên bảng thanh thời gian; trả về bảng cảnh báo đã áp cooldown."""
    cfg = cfg or AlertConfig()
    cols = ["ts", "trading_date", "symbol", "rule", "severity", "value", "threshold", "message", "source", "dedupe_key"]
    if bars.empty:
        return pd.DataFrame(columns=cols)
    b = score_bars(bars, cfg.window, cfg.min_periods)
    bar_len = bars["bar"].sort_values().diff().dropna()
    unit = bar_len[bar_len > pd.Timedelta(0)].min() if len(bar_len) else pd.Timedelta("1min")
    run = _signed_run_length(b, unit)
    rules = {
        # có KL TB 20 phiên: so với CÙNG GIỜ các phiên trước (RVOL); không có: z bền vững của KL trong phiên
        "volume_spike": _volume_rule(b, cfg, ~b["bar"].dt.strftime("%H:%M").isin(AUCTION_BARS)),
        "spread_blowout": _spread_rule(b),
        "price_jump": (b["z_ret"].abs() >= cfg.z, b["z_ret"], cfg.z),
        "foreign_flow": _foreign_rule(b),
        "book_pressure": (run == OBI_PERSIST, b["obi3"], OBI_EXTREME),
        "near_limit": (b["band_pos"].abs() >= NEAR_LIMIT, b["band_pos"], NEAR_LIMIT),
    }
    frames = []
    for rule, (mask, value, thr) in rules.items():
        hit = b.loc[mask.fillna(False), ["bar", "trading_date", "symbol", "last", "pct_change"]].copy()
        if hit.empty:
            continue
        hit["rule"], hit["value"] = rule, value[mask.fillna(False)]
        hit["threshold"] = thr[mask.fillna(False)] if isinstance(thr, pd.Series) else thr
        frames.append(hit)
    if not frames:
        return pd.DataFrame(columns=cols)
    a = pd.concat(frames).sort_values(["trading_date", "symbol", "rule", "bar"])
    # cooldown: cùng mã + cùng quy tắc chỉ báo lại sau `cooldown_bars` thanh
    step = a.groupby(["trading_date", "symbol", "rule"])["bar"].diff()
    a = a[step.isna() | (step > unit * cfg.cooldown_bars)].copy()
    n_rules = a.groupby(["trading_date", "symbol", "bar"])["rule"].transform("nunique")
    low = a["rule"].isin(["near_limit", "book_pressure"])
    by_value = (a["value"].abs() >= CAO_VALUE) & ~low & ~a["rule"].isin(NO_VALUE_ESCALATION)
    a["severity"] = np.where((n_rules >= 2) | by_value, "CAO",
                             np.where(low, "THẤP", "TRUNG BÌNH"))
    a["message"] = [_message(r) for r in a.itertuples()]
    a["ts"] = a["bar"]
    a["source"] = source
    a["dedupe_key"] = (source + "|" + a["trading_date"] + "|" + a["symbol"] + "|" + a["rule"] + "|"
                       + a["bar"].dt.strftime("%H:%M"))
    return a[cols].sort_values("ts", ascending=False).reset_index(drop=True)


def _signed_run_length(b: pd.DataFrame, unit: pd.Timedelta) -> pd.Series:
    """Độ dài chuỗi thanh LIỀN NHAU (cách đúng một thanh) mà OBI_3 vượt ngưỡng cực đoan VÀ giữ nguyên dấu
    (theo mã, theo phiên). Mất thanh giữa chừng hoặc qua nghỉ trưa thì đếm lại (CX-019)."""
    sign = np.sign(b["obi3"]).where(b["obi3"].abs() >= OBI_EXTREME, 0.0).fillna(0.0)
    keys = [b["trading_date"], b["symbol"]]
    gap = b["bar"].groupby(keys).diff() != unit
    changed = sign.ne(sign.groupby(keys).shift(1)) | gap
    run_id = changed.groupby(keys).cumsum()
    length = sign.groupby(keys + [run_id]).cumcount() + 1
    return length.where(sign != 0, 0)


def _prior_quantile(x: pd.Series, keys: list, q: float) -> pd.Series:
    """Phân vị q của các giá trị TRƯỚC thanh hiện tại (cùng mã, cùng phiên), bỏ NaN; < HIST_MIN giá trị -> NaN."""
    return x.groupby(keys).transform(lambda s: s.shift(1).expanding(min_periods=HIST_MIN).quantile(q))


def _spread_rule(b: pd.DataFrame):
    """Spread tính bằng số bước giá HOSE. Báo khi >= SPREAD_MIN_TICKS và > phân vị SPREAD_Q của chính mã.
    Chưa đủ HIST_MIN thanh trước: chỉ dùng sàn SPREAD_MIN_TICKS (fallback rõ ràng, không cần MAD)."""
    if "bid1" not in b or "ask1" not in b:
        return pd.Series(False, index=b.index), pd.Series(np.nan, index=b.index), SPREAD_MIN_TICKS
    ticks = pd.Series(grid_ticks(b["bid1"], b["ask1"]), index=b.index)  # đếm trên lưới giá, kể cả khi vắt qua mốc
    own = _prior_quantile(ticks, [b["trading_date"], b["symbol"]], SPREAD_Q)
    thr = np.maximum(own.fillna(SPREAD_MIN_TICKS), SPREAD_MIN_TICKS)
    # spread rời rạc: phải VƯỢT phân vị riêng (mã thường trực 5 bước thì 5 bước không bất thường)
    return (ticks >= SPREAD_MIN_TICKS) & ~(ticks <= own), ticks, thr


def _foreign_rule(b: pd.DataFrame):
    """Cộng FOREIGN_WINDOW thanh gần nhất (cùng mã, cùng phiên). Báo khi NN ròng khác 0, chiếm >= FOREIGN_MIN_SHARE
    giá trị khớp của cửa sổ và |ròng| >= phân vị FOREIGN_Q của các cửa sổ có NN trước đó của chính mã. Chưa đủ HIST_MIN cửa sổ trước -> không báo (fallback rõ ràng). Giá trị = tỷ trọng có dấu."""
    keys = [b["trading_date"], b["symbol"]]
    roll = lambda c: b[c].groupby(keys).transform(  # noqa: E731
        lambda x: x.rolling(FOREIGN_WINDOW, min_periods=FOREIGN_WINDOW).sum())
    net, val = roll("f_net_val"), roll("val")
    traded = net.notna() & (net != 0)
    share = (net.abs() / val).where(val > 0)
    own = _prior_quantile(net.abs().where(traded), keys, FOREIGN_Q)
    mask = traded & (share >= FOREIGN_MIN_SHARE) & (net.abs() >= own)
    return mask, np.sign(net) * share, FOREIGN_MIN_SHARE


def _volume_rule(b: pd.DataFrame, cfg: AlertConfig, eligible: pd.Series):
    if "rvol_bar" not in b:
        return (b["z_vol"] >= cfg.z) & eligible, b["z_vol"], cfg.z
    has = b["rvol_bar"].notna()
    mask = ((has & (b["rvol_bar"] >= RVOL_SPIKE)) | (~has & (b["z_vol"] >= cfg.z))) & eligible
    value = b["rvol_bar"].where(has, b["z_vol"])
    thr = pd.Series(np.where(has, RVOL_SPIKE, cfg.z), index=b.index)
    return mask, value, thr


def _message(r) -> str:
    name = RULE_NAMES[r.rule]
    if r.rule == "volume_spike" and r.threshold == RVOL_SPIKE:
        return f"Khối lượng cao gấp {r.value:.1f} lần mức thường thấy cùng khung giờ (ngưỡng {RVOL_SPIKE:.1f})"
    if r.rule == "book_pressure":
        side = "bên mua dày hơn" if r.value > 0 else "bên bán dày hơn"
        return f"Mất cân bằng sổ lệnh (OBI₃) ở mức {r.value:+.2f}, {side}, trong {OBI_PERSIST} thanh 1 phút liên tiếp"
    if r.rule == "near_limit":
        return f"Giá đã đi {abs(r.value) * 100:.0f}% khoảng cách từ giá tham chiếu đến giá {'trần' if r.value > 0 else 'sàn'}"
    if r.rule == "foreign_flow":
        return (f"Khối ngoại {'mua' if r.value > 0 else 'bán'} ròng bằng {abs(r.value) * 100:.0f}% giá trị khớp "
                f"{FOREIGN_WINDOW} phút gần nhất, lớn hơn {FOREIGN_Q:.0%} các cửa sổ có khối ngoại trước đó của mã")
    if r.rule == "spread_blowout":
        return (f"Độ chênh giá mua-bán {r.value:.0f} bước giá (ngưỡng {r.threshold:.0f} bước: tối thiểu "
                f"{SPREAD_MIN_TICKS:.0f} bước hoặc phân vị {SPREAD_Q:.0%} của chính mã trong phiên)")
    z = f"|z| ≥ {Z_CAP:.0f}" if abs(r.value) >= Z_CAP else f"z = {r.value:+.1f}"
    return f"{name}: điểm z bền vững {z} (ngưỡng {r.threshold:g})"


def to_rows(alerts: pd.DataFrame) -> list[dict]:
    if alerts.empty:
        return []
    a = alerts.copy()
    a["ts"] = a["ts"].map(lambda t: t.isoformat(timespec="milliseconds"))
    return a.to_dict("records")


def evaluate_against_truth(alerts: pd.DataFrame, truth: pd.DataFrame, window_min: int = 6) -> dict:
    """Đối chiếu cảnh báo với sự kiện đã cài trong dữ liệu MÔ PHỎNG (bảng sim_truth).

    recall    = tỷ lệ sự kiện cài được ít nhất một cảnh báo đúng loại trong `window_min` phút sau đó
    precision = tỷ lệ cảnh báo (3 loại có đáp án) rơi vào cửa sổ của một sự kiện cài cùng mã
    """
    kind_rule = {"volume_spike": "volume_spike", "spread_blowout": "spread_blowout", "foreign_dump": "foreign_flow"}
    if truth.empty:
        return {"n_events": 0, "recall": float("nan"), "precision": float("nan"), "by_kind": {}}
    a = alerts[alerts["rule"].isin(kind_rule.values())] if not alerts.empty else alerts
    win = pd.Timedelta(minutes=window_min)
    hits, by_kind, matched_alerts = 0, {}, set()
    for kind, grp in truth.groupby("kind"):
        k_hit = 0
        for ev in grp.itertuples():
            if a.empty:
                continue
            m = a[(a["symbol"] == ev.symbol) & (a["rule"] == kind_rule[kind])
                  & (a["ts"] >= ev.ts.floor("1min")) & (a["ts"] <= ev.ts + win)]
            if len(m):
                k_hit += 1
                matched_alerts.update(m.index)
        by_kind[kind] = {"n": int(len(grp)), "detected": k_hit, "recall": k_hit / len(grp)}
        hits += k_hit
    return {"n_events": int(len(truth)), "n_alerts": int(len(a)), "recall": hits / len(truth),
            "precision": (len(matched_alerts) / len(a)) if len(a) else float("nan"), "by_kind": by_kind}
