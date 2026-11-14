"""Bộ quy tắc cảnh báo có mức ưu tiên, thời gian nguội (cooldown) và khóa chống lặp.

Quy tắc          Điều kiện                                         Cơ sở ngưỡng
volume_spike     z_vol >= 3,5                                      Iglewicz & Hoaglin (1993)
spread_blowout   z_spread >= 3,5 và spread >= 2 bước giá tối thiểu  thống kê + loại nhiễu 1 bước giá
price_jump       |z_ret| >= 3,5                                    thống kê
foreign_flow     |z_fnet| >= 3,5 và NN chiếm >= 30% GT thanh        thống kê + điều kiện trọng yếu
book_pressure    |OBI_3| >= 0,6 liên tục >= 3 thanh                 OBI=0,6 <=> một bên dày gấp 4 lần bên kia
near_limit       |band_pos| >= 0,9                                 quy tắc biên độ trần/sàn của sàn
Mức ưu tiên: CAO nếu >= 2 quy tắc cùng nổ trên một mã trong một thanh hoặc |z| >= 6; còn lại TRUNG BÌNH,
riêng near_limit/book_pressure là THẤP khi đứng một mình.
Cảnh báo là tín hiệu "đáng xem", không phải khuyến nghị mua/bán.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .anomaly import Z_CAP, Z_THRESHOLD, score_bars

OBI_EXTREME = 0.6
OBI_PERSIST = 3
NEAR_LIMIT = 0.9
FOREIGN_MIN_SHARE = 0.30
RULE_NAMES = {"volume_spike": "Bùng nổ khối lượng", "spread_blowout": "Giãn chênh lệch mua-bán",
              "price_jump": "Giá biến động đột ngột", "foreign_flow": "Dòng tiền NN bất thường",
              "book_pressure": "Sổ lệnh lệch kéo dài", "near_limit": "Sát trần/sàn"}


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
    g = b.groupby(["trading_date", "symbol"], sort=False)
    # spread tối thiểu trong phiên của mã ~ 1 bước giá => dùng làm thước đo "2 bước giá"
    min_spread = g["spread_bps"].transform(lambda s: s.expanding(min_periods=5).min().shift(1))
    run = _signed_run_length(b)
    fshare = (b["f_net_val"].abs() / b["val"]).where(b["val"] > 0)
    rules = {
        "volume_spike": (b["z_vol"] >= cfg.z, b["z_vol"], cfg.z),
        "spread_blowout": ((b["z_spread"] >= cfg.z) & (b["spread_bps"] >= 2 * min_spread), b["z_spread"], cfg.z),
        "price_jump": (b["z_ret"].abs() >= cfg.z, b["z_ret"], cfg.z),
        "foreign_flow": ((b["z_fnet"].abs() >= cfg.z) & (fshare >= FOREIGN_MIN_SHARE), b["z_fnet"], cfg.z),
        "book_pressure": (run == OBI_PERSIST, b["obi3"], OBI_EXTREME),
        "near_limit": (b["band_pos"].abs() >= NEAR_LIMIT, b["band_pos"], NEAR_LIMIT),
    }
    frames = []
    for rule, (mask, value, thr) in rules.items():
        hit = b.loc[mask.fillna(False), ["bar", "trading_date", "symbol", "last", "pct_change"]].copy()
        if hit.empty:
            continue
        hit["rule"], hit["value"], hit["threshold"] = rule, value[mask.fillna(False)], thr
        frames.append(hit)
    if not frames:
        return pd.DataFrame(columns=cols)
    a = pd.concat(frames).sort_values(["trading_date", "symbol", "rule", "bar"])
    # cooldown: cùng mã + cùng quy tắc chỉ báo lại sau `cooldown_bars` thanh
    step = a.groupby(["trading_date", "symbol", "rule"])["bar"].diff()
    bar_len = bars["bar"].sort_values().diff().dropna()
    unit = bar_len[bar_len > pd.Timedelta(0)].min() if len(bar_len) else pd.Timedelta("1min")
    a = a[step.isna() | (step > unit * cfg.cooldown_bars)].copy()
    n_rules = a.groupby(["trading_date", "symbol", "bar"])["rule"].transform("nunique")
    low = a["rule"].isin(["near_limit", "book_pressure"])
    a["severity"] = np.where((n_rules >= 2) | ((a["value"].abs() >= 6) & ~low), "CAO",
                             np.where(low, "THẤP", "TRUNG BÌNH"))
    a["message"] = [_message(r) for r in a.itertuples()]
    a["ts"] = a["bar"]
    a["source"] = source
    a["dedupe_key"] = (source + "|" + a["trading_date"] + "|" + a["symbol"] + "|" + a["rule"] + "|"
                       + a["bar"].dt.strftime("%H:%M"))
    return a[cols].sort_values("ts", ascending=False).reset_index(drop=True)


def _signed_run_length(b: pd.DataFrame) -> pd.Series:
    """Độ dài chuỗi thanh liên tiếp mà OBI_3 vượt ngưỡng cực đoan VÀ giữ nguyên dấu (theo mã, theo phiên)."""
    sign = np.sign(b["obi3"]).where(b["obi3"].abs() >= OBI_EXTREME, 0.0).fillna(0.0)
    keys = [b["trading_date"], b["symbol"]]
    changed = sign.ne(sign.groupby(keys).shift(1))
    run_id = changed.groupby(keys).cumsum()
    length = sign.groupby(keys + [run_id]).cumcount() + 1
    return length.where(sign != 0, 0)


def _message(r) -> str:
    name = RULE_NAMES[r.rule]
    if r.rule == "book_pressure":
        side = "bên MUA dày hơn" if r.value > 0 else "bên BÁN dày hơn"
        return f"{name}: OBI₃ = {r.value:+.2f} ({side}) trong {OBI_PERSIST} thanh liên tiếp"
    if r.rule == "near_limit":
        return f"{name}: giá ở {abs(r.value) * 100:.0f}% biên độ {'trần' if r.value > 0 else 'sàn'}"
    if r.rule == "foreign_flow":
        z = f"|z| ≥ {Z_CAP:.0f}" if abs(r.value) >= Z_CAP else f"z = {r.value:+.1f}"
        return f"{name}: NN {'mua' if r.value > 0 else 'bán'} ròng đột biến ({z})"
    z = f"|z| ≥ {Z_CAP:.0f}" if abs(r.value) >= Z_CAP else f"z = {r.value:+.1f}"
    return f"{name}: {z} (ngưỡng {r.threshold})"


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
