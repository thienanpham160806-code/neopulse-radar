"""Bộ MÔ PHỎNG thị trường - sinh thông điệp đúng lược đồ thô của NEO API (stockInfo, marketInfo).

MỤC ĐÍCH: cho phép chạy, kiểm thử và trình diễn toàn bộ đường ống khi chưa có tài khoản NEO API
hoặc ngoài giờ giao dịch. Dữ liệu sinh ra KHÔNG phải dữ liệu thị trường; mọi bản ghi mang
source='sim' và giao diện luôn gắn nhãn "MÔ PHỎNG". Kết quả kiểm chứng trên dữ liệu này chỉ
chứng minh mã nguồn chạy đúng, không phải bằng chứng về thị trường thật.

Cơ chế sinh (để biết mô hình "biết trước" điều gì):
  * Mỗi mã có một biến dòng lệnh ẩn f_t ~ AR(1). Mất cân bằng sổ lệnh là hàm tăng của f_t và lợi suất
    kỳ sau = beta * f_t + nhiễu => OBI có sức dự báo yếu DO THIẾT KẾ.
  * Sự kiện bất thường (bùng nổ khối lượng, giãn spread, nước ngoài bán mạnh) được cài ngẫu nhiên và
    ghi vào bảng `sim_truth` làm "đáp án" để đo độ thu hồi của bộ phát hiện.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

import numpy as np

from ..timeutil import VN_TZ

VN30_SIM = ["ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG", "LPB", "MBB", "MSN",
            "MWG", "PLX", "SAB", "SHB", "SSB", "SSI", "STB", "TCB", "TPB", "VCB", "VHM", "VIB", "VIC",
            "VJC", "VNM", "VPB", "VRE"]


def hose_tick(price: float) -> float:
    """Bước giá HOSE cho cổ phiếu: <10.000: 10đ; 10.000-49.950: 50đ; >=50.000: 100đ."""
    return 10.0 if price < 10_000 else (50.0 if price < 50_000 else 100.0)


def round_tick(price: float, mode: str = "nearest") -> float:
    t = hose_tick(price)
    q = price / t
    q = math.floor(q) if mode == "down" else (math.ceil(q) if mode == "up" else round(q))
    return q * t


@dataclass
class _Stock:
    symbol: str
    ref: float
    mid: float
    base_depth: float       # khối lượng chờ điển hình mỗi mức giá
    base_rate: float        # khối lượng khớp điển hình mỗi bước
    foreign_bias: float     # thiên hướng mua(+)/bán(-) của khối ngoại
    room: float
    remain: float
    flow: float = 0.0
    cum_vol: float = 0.0
    cum_val: float = 0.0
    fbv: float = 0.0
    fsv: float = 0.0
    fbval: float = 0.0
    fsval: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    last: float = 0.0
    last_vol: float = 0.0
    spread_ticks: int = 1
    shock_left: int = 0
    shock_kind: str = ""


class SimMarket:
    """Thị trường mô phỏng của một phiên. Gọi `step()` để tiến một bước thời gian."""

    def __init__(self, session_date: date, symbols: list[str] | None = None, *, seed: int = 7,
                 step_seconds: int = 30, prev_close: dict[str, float] | None = None,
                 anomaly_rate: float = 0.0015, beta: float = 0.00016):
        self.rng = np.random.default_rng(seed + session_date.toordinal())
        self.date, self.step_seconds = session_date, step_seconds
        self.anomaly_rate, self.beta = anomaly_rate, beta
        self.truth: list[dict] = []
        base_rng = np.random.default_rng(seed)  # đặc tính mã cố định qua các phiên
        self.stocks: dict[str, _Stock] = {}
        for sym in symbols or VN30_SIM:
            p0 = float(base_rng.choice([12_000, 18_500, 24_000, 31_000, 45_000, 62_000, 88_000, 120_000]))
            ref = round_tick((prev_close or {}).get(sym, p0 * (1 + base_rng.normal(0, 0.05))))
            depth = float(base_rng.lognormal(11.0, 0.8))
            room = float(base_rng.uniform(5e8, 3e9))
            st = _Stock(sym, ref, ref, depth, depth * float(base_rng.uniform(0.15, 0.5)),
                        float(base_rng.normal(0, 0.15)), room, room * float(base_rng.uniform(0.02, 0.6)))
            st.open = st.high = st.low = st.last = ref
            self.stocks[sym] = st
        self.market_factor = 0.0
        self.session_drift = float(self.rng.normal(0, 0.0000006 * step_seconds))
        self.vn30_prev = 1900.0 if prev_close is None else prev_close.get("__VN30__", 1900.0)
        self.vnindex_prev = 1650.0 if prev_close is None else prev_close.get("__VNINDEX__", 1650.0)
        self.basis = float(self.rng.normal(2.0, 3.0))
        self.fut_cum_vol = 0.0
        self.now = datetime.combine(session_date, time(9, 15), tzinfo=VN_TZ)
        self.t = 0

    # ----------------------------------------------------------- điều khiển
    def session_times(self) -> list[datetime]:
        out, cur = [], datetime.combine(self.date, time(9, 15), tzinfo=VN_TZ)
        end_am = datetime.combine(self.date, time(11, 30), tzinfo=VN_TZ)
        start_pm = datetime.combine(self.date, time(13, 0), tzinfo=VN_TZ)
        end_pm = datetime.combine(self.date, time(14, 30), tzinfo=VN_TZ)
        while cur <= end_pm:
            if cur <= end_am or cur >= start_pm:
                out.append(cur)
            cur += timedelta(seconds=self.step_seconds)
        return out

    def step(self, now: datetime) -> None:
        self.now, self.t = now, self.t + 1
        r = self.rng
        dt = self.step_seconds / 30.0
        # dạng chữ U của thanh khoản trong ngày
        frac = ((now.hour * 60 + now.minute) - 555) / 315.0
        ushape = 0.6 + 1.6 * (2 * frac - 1) ** 2
        self.market_factor = 0.9 * self.market_factor + float(r.normal(0, 0.3))
        for st in self.stocks.values():
            st.flow = 0.85 * st.flow + float(r.normal(0, 0.4)) + 0.03 * self.market_factor
            if st.shock_left > 0:
                st.shock_left -= 1
                if st.shock_left == 0:
                    st.shock_kind, st.spread_ticks = "", 1
            elif r.random() < self.anomaly_rate:
                st.shock_kind = str(r.choice(["volume_spike", "spread_blowout", "foreign_dump"]))
                st.shock_left = int(r.integers(4, 9))
                self.truth.append({"ts": now.isoformat(timespec="milliseconds"),
                                   "trading_date": self.date.isoformat(), "symbol": st.symbol,
                                   "kind": st.shock_kind, "detail": f"kéo dài {st.shock_left} bước"})
            ret = (self.beta * st.flow + self.session_drift + 0.00005 * self.market_factor
                   + float(r.normal(0, 0.0007))) * math.sqrt(dt)
            lo, hi = round_tick(st.ref * 0.93, "up"), round_tick(st.ref * 1.07, "down")
            st.mid = min(max(st.mid * (1 + ret), lo), hi)
            vol_mult = 9.0 if st.shock_kind == "volume_spike" else 1.0
            if st.shock_kind == "spread_blowout":
                st.spread_ticks = 6
            traded = max(0.0, st.base_rate * ushape * vol_mult * float(r.lognormal(0, 0.5)) * dt)
            traded = round(traded / 100) * 100
            tick = hose_tick(st.mid)
            bid1 = min(round_tick(st.mid - tick * st.spread_ticks / 2, "down"), hi - tick)
            bid1 = max(bid1, lo)
            ask1 = min(bid1 + tick * st.spread_ticks, hi)
            st._bid1, st._ask1 = bid1, ask1  # type: ignore[attr-defined]
            if traded > 0:
                st.last = ask1 if st.flow > 0 else bid1
                st.last_vol = min(traded, float(r.choice([100, 200, 500, 1000, 5000])))
                st.cum_vol += traded
                st.cum_val += traded * st.last
                st.high, st.low = max(st.high, st.last), min(st.low, st.last)
                f_part = 0.12 * float(r.lognormal(0, 0.6))
                bias = st.foreign_bias - (2.5 if st.shock_kind == "foreign_dump" else 0.0)
                if st.shock_kind == "foreign_dump":
                    f_part = 0.8
                p_buy = 1 / (1 + math.exp(-bias))
                fb, fs = traded * f_part * p_buy, traded * f_part * (1 - p_buy)
                st.fbv, st.fsv = st.fbv + fb, st.fsv + fs
                st.fbval, st.fsval = st.fbval + fb * st.last, st.fsval + fs * st.last
                st.remain = min(st.room, max(0.0, st.remain - fb + fs))
        self.basis = 0.96 * self.basis + float(r.normal(0, 0.5)) + 0.05 * self.market_factor
        self.fut_cum_vol += max(0.0, float(r.lognormal(5.5, 0.5))) * ushape * dt

    # ------------------------------------------------------- thông điệp thô
    def stock_messages(self) -> list[dict]:
        r, out = self.rng, []
        for st in self.stocks.values():
            tick = hose_tick(st.mid)
            bid1, ask1 = st._bid1, st._ask1  # type: ignore[attr-defined]
            k = 0.4
            thin = 0.25 if st.shock_kind == "spread_blowout" else 1.0
            bv = [round(st.base_depth * thin * math.exp(k * st.flow) * float(r.lognormal(0, 0.5)) / 100) * 100 + 100
                  for _ in range(3)]
            av = [round(st.base_depth * thin * math.exp(-k * st.flow) * float(r.lognormal(0, 0.5)) / 100) * 100 + 100
                  for _ in range(3)]
            chg = st.last - st.ref
            out.append({
                "symbol": st.symbol, "marketCode": "HOSE", "stockType": "ST",
                "tradingDate": self.date.strftime("%d/%m/%Y"),
                "ceilingPrice": round_tick(st.ref * 1.07, "down"), "floorPrice": round_tick(st.ref * 0.93, "up"),
                "refPrice": st.ref,
                "bidPrice1": f"{bid1:.1f}", "bidVol1": bv[0], "bidPrice2": bid1 - tick, "bidVol2": bv[1],
                "bidPrice3": bid1 - 2 * tick, "bidVol3": bv[2],
                "askPrice1": f"{ask1:.1f}", "askVol1": av[0], "askPrice2": ask1 + tick, "askVol2": av[1],
                "askPrice3": ask1 + 2 * tick, "askVol3": av[2],
                "closePrice": st.last, "closeVol": st.last_vol, "priceChange": chg,
                "percentPriceChange": round(chg / st.ref * 100, 2),
                "openPrice": st.open, "highPrice": st.high, "lowPrice": st.low,
                "averagePrice": round(st.cum_val / st.cum_vol) if st.cum_vol else st.ref,
                "totalTradingVolume": st.cum_vol, "totalTradingValue": st.cum_val,
                "totalBidQTTY": None, "totalAskQTTY": None,
                "foreignBuyVolume": round(st.fbv), "foreignSellVolume": round(st.fsv),
                "foreignBuyValue": round(st.fbval), "foreignSellValue": round(st.fsval),
                "foreignNetValue": round(st.fbval - st.fsval),
                "foreignRemain": round(st.remain), "foreignRoom": round(st.room), "breakEvenPoint": 0,
            })
        return out

    def _vn30_value(self) -> float:
        rets = [st.last / st.ref - 1 for st in self.stocks.values()]
        return self.vn30_prev * (1 + float(np.mean(rets)))

    def index_messages(self) -> list[dict]:
        sts = list(self.stocks.values())
        adv = sum(s.last > s.ref for s in sts)
        dec = sum(s.last < s.ref for s in sts)
        ce = sum(s.last >= round_tick(s.ref * 1.07, "down") for s in sts)
        fl = sum(s.last <= round_tick(s.ref * 0.93, "up") for s in sts)
        vol, val = sum(s.cum_vol for s in sts), sum(s.cum_val for s in sts)
        vn30 = self._vn30_value()
        mean_ret = vn30 / self.vn30_prev - 1
        out = []
        for code, prev, scale in (("VN30", self.vn30_prev, 1.0), ("VNINDEX", self.vnindex_prev, 13.0)):
            value = prev * (1 + mean_ret * (1.0 if code == "VN30" else 0.85))
            k = 1 if code == "VN30" else 13  # VNINDEX: nhân rổ mô phỏng để có quy mô ~390 mã
            out.append({
                "dateString": self.date.isoformat(), "indexCode": code, "indexValue": f"{value:.2f}",
                "indexTime": self.now.strftime("%H:%M:%S"), "indexChange": round(value - prev, 2),
                "indexPercentChange": round((value / prev - 1) * 100, 2),
                "totalVolume": round(vol * scale), "totalValue": round(val * scale),
                "marketStatus": "LO", "marketCode": "HOSE",
                "advances": adv * k, "declines": dec * k, "noChange": (len(sts) - adv - dec) * k,
                "numberOfCe": ce * k, "numberOfFl": fl * k, "oddLotTotalVolume": 0, "oddLotTotalValue": 0,
            })
        return out

    def future_messages(self) -> list[dict]:
        """HĐTL VN30 tháng gần nhất: giá = VN30 + basis; basis co dần về 0 khi gần đáo hạn."""
        d = self.date.replace(day=15)
        third_thu = d + timedelta(days=(3 - d.weekday()) % 7)
        if third_thu < self.date:
            nm = (self.date.replace(day=28) + timedelta(days=7)).replace(day=15)
            third_thu = nm + timedelta(days=(3 - nm.weekday()) % 7)
        dtm = max(0, (third_thu - self.date).days)
        spot = self._vn30_value()
        price = round((spot + self.basis * min(1.0, dtm / 10 + 0.15)) * 10) / 10
        ref = round(self.vn30_prev * 10) / 10
        sym = f"VN30F{third_thu:%y%m}"
        return [{
            "symbol": sym, "stockName": f"HDTL VN30 {third_thu:%m/%Y}", "marketCode": "FU",
            "stockType": "FUVN30", "tradingDate": self.date.strftime("%d/%m/%Y"),
            "ceilingPrice": math.floor(ref * 1.07 * 10) / 10, "floorPrice": math.ceil(ref * 0.93 * 10) / 10,
            "refPrice": ref,
            "bidPrice1": f"{price - 0.1:.1f}", "bidVol1": int(self.rng.integers(5, 120)),
            "bidPrice2": round(price - 0.2, 1), "bidVol2": int(self.rng.integers(5, 120)),
            "bidPrice3": round(price - 0.3, 1), "bidVol3": int(self.rng.integers(5, 120)),
            "askPrice1": f"{price + 0.1:.1f}", "askVol1": int(self.rng.integers(5, 120)),
            "askPrice2": round(price + 0.2, 1), "askVol2": int(self.rng.integers(5, 120)),
            "askPrice3": round(price + 0.3, 1), "askVol3": int(self.rng.integers(5, 120)),
            "closePrice": price, "closeVol": 1, "priceChange": round(price - ref, 1),
            "percentPriceChange": round((price / ref - 1) * 100, 2),
            "openPrice": ref, "highPrice": max(price, ref), "lowPrice": min(price, ref),
            "totalTradingVolume": round(self.fut_cum_vol), "totalTradingValue": round(self.fut_cum_vol * price * 100_000),
            "underlyingSymbol": "VN30", "maturityDate": third_thu.strftime("%d/%m/%Y"),
            "openInterest": 30_000 + int(self.rng.integers(-500, 500)),
        }]

    def closes(self) -> dict[str, float]:
        out = {s.symbol: s.last for s in self.stocks.values()}
        out["__VN30__"] = self._vn30_value()
        out["__VNINDEX__"] = self.vnindex_prev * (1 + (out["__VN30__"] / self.vn30_prev - 1) * 0.85)
        return out


def simulate_sessions(storage, n_sessions: int = 6, *, end: date | None = None, seed: int = 7,
                      step_seconds: int = 30, symbols: list[str] | None = None) -> dict:
    """Sinh `n_sessions` phiên mô phỏng (bỏ cuối tuần) và ghi qua đúng đường ống nhập liệu thật."""
    from ..data.ingest import Ingestor
    from ..timeutil import iso_vn, now_vn, previous_weekday

    end = end or now_vn().date()
    if end.weekday() >= 5:
        end = previous_weekday(end)
    days = [end]
    while len(days) < n_sessions:
        days.append(previous_weekday(days[-1]))
    days.reverse()
    ing = Ingestor(storage, "sim", batch_size=5000)
    run = storage.start_run(iso_vn(now_vn()), "sim", f"{n_sessions} phiên mô phỏng, seed={seed}, bước={step_seconds}s")
    prev = None
    for d in days:
        mkt = SimMarket(d, symbols, seed=seed, step_seconds=step_seconds, prev_close=prev)
        for ts in mkt.session_times():
            mkt.step(ts)
            for m in mkt.stock_messages():
                ing.add_quote(m, ts)
            for m in mkt.index_messages():
                ing.add_index(m, ts)
            for m in mkt.future_messages():
                ing.add_quote(m, ts)
        storage.insert_sim_truth(mkt.truth)
        prev = mkt.closes()
        ing.flush()
    ing.flush()
    storage.finish_run(run, iso_vn(now_vn()), **ing.counts())
    return {"sessions": [d.isoformat() for d in days], **ing.counts()}
