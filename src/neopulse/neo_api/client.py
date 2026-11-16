"""NEO API REST client: đăng nhập JWT, tự làm mới token, giới hạn tần suất, thử lại có kiểm soát.

Chỉ bao gồm các nhóm API ĐỌC dữ liệu thị trường. Các endpoint đặt/sửa/hủy lệnh bị chặn cứng
(`NeoSafetyError`) vì đề đồ án cấm phát sinh giao dịch thật và NEO API không có môi trường thử.

Nguồn đặc tả: https://neoinvest.vpbanks.com.vn/neo-openapi/docs (v1.0.0, truy cập 14/11/2026).
"""
from __future__ import annotations

import logging
import time
from collections.abc import Iterable, Iterator
from typing import Any

import httpx

from ..config import Settings
from .errors import (
    RETRYABLE_CODES,
    RETRYABLE_HTTP,
    SUCCESS_CODES,
    NeoApiError,
    NeoAuthError,
    NeoSafetyError,
)
from .ratelimit import RateLimiter

log = logging.getLogger(__name__)

# Đường dẫn bị cấm tuyệt đối trong đồ án (đặt/sửa/hủy lệnh = lệnh thật trên thị trường).
FORBIDDEN_PATH_PREFIXES = ("/trading/orders",)
TOKEN_REFRESH_MARGIN_S = 300  # làm mới token trước khi hết hạn 5 phút
MAX_SYMBOLS_PER_CALL = 10     # mã lỗi NEOINP000021: tối đa mười mã mỗi lần gọi


class NeoClient:
    def __init__(self, settings: Settings, *, transport: httpx.BaseTransport | None = None,
                 limiter: RateLimiter | None = None, max_retries: int = 3,
                 sleep=time.sleep, clock=time.time):
        self.s = settings
        self._http = httpx.Client(timeout=httpx.Timeout(15.0, connect=8.0), transport=transport)
        self._limiter = limiter or RateLimiter(settings.neo_max_rps, burst=1)
        self._max_retries = max_retries
        self._sleep, self._clock = sleep, clock
        self._token: str | None = settings.neo_access_token or None
        # Token dán tay không biết hạn: giả định còn hiệu lực, hết hạn sẽ nhận 401 rồi đăng nhập lại.
        self._token_expiry: float = float("inf") if self._token else 0.0
        self.request_count = 0
        self.last_ok_at: float | None = None
        self.last_error: str | None = None

    # ------------------------------------------------------------------ auth
    def login(self) -> str:
        """POST /auth/token bằng username/password; lưu access_token trong bộ nhớ (không ghi đĩa)."""
        if not (self.s.neo_username and self.s.neo_password):
            raise NeoAuthError("Thiếu NEO_USERNAME/NEO_PASSWORD trong .env (hoặc NEO_ACCESS_TOKEN).")
        self._limiter.acquire()
        try:
            r = self._http.post(self.s.neo_auth_url,
                                json={"username": self.s.neo_username, "password": self.s.neo_password},
                                headers={"Content-Type": "application/json"})
        except httpx.HTTPError as e:
            raise NeoApiError(f"Không kết nối được máy chủ xác thực: {type(e).__name__}") from e
        body = self._json(r)
        if body.get("status") != 1 or not isinstance(body.get("data"), dict):
            raise NeoAuthError(body.get("message") or "Đăng nhập thất bại",
                               code=body.get("code"), http_status=r.status_code)
        data = body["data"]
        self._token = data["access_token"]
        self._token_expiry = self._clock() + float(data.get("expires_in") or 10800)
        log.info("Đăng nhập NEO API thành công; token hết hạn sau %ss", data.get("expires_in"))
        return self._token

    def token(self) -> str:
        if not self._token or self._clock() >= self._token_expiry - TOKEN_REFRESH_MARGIN_S:
            self.login()
        return self._token  # type: ignore[return-value]

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token()}",
                "x-device": self.s.neo_device_id, "x-devicetype": self.s.neo_device_type}

    # --------------------------------------------------------------- request
    @staticmethod
    def _json(r: httpx.Response) -> dict:
        try:
            body = r.json()
        except ValueError:
            raise NeoApiError("Phản hồi không phải JSON", http_status=r.status_code) from None
        if not isinstance(body, dict):
            raise NeoApiError("Phản hồi JSON không đúng cấu trúc envelope", http_status=r.status_code)
        return body

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET có envelope {status, code, message, data}; trả về `data`."""
        if any(path.startswith(p) for p in FORBIDDEN_PATH_PREFIXES):
            raise NeoSafetyError(f"Endpoint {path} bị chặn: đồ án không được phát sinh/đụng tới lệnh thật.")
        params = {k: v for k, v in (params or {}).items() if v is not None}
        relogin_done = False
        last: Exception | None = None
        for attempt in range(self._max_retries + 1):
            self._limiter.acquire()
            self.request_count += 1
            try:
                r = self._http.get(f"{self.s.neo_base_url}{path}", params=params, headers=self._headers())
            except httpx.HTTPError as e:
                last = NeoApiError(f"Lỗi mạng khi gọi {path}: {type(e).__name__}")
            else:
                if r.status_code == 401 and not relogin_done and self.s.neo_username:
                    relogin_done = True
                    log.warning("Token bị từ chối (401) - đăng nhập lại một lần.")
                    self._token = None
                    continue
                if r.status_code in (401, 403):
                    body = self._safe_body(r)
                    err = NeoAuthError(body.get("message") or "Không được phép truy cập",
                                       code=body.get("code") or f"NEOINP000{r.status_code}",
                                       http_status=r.status_code)
                    self.last_error = str(err)
                    raise err
                if r.status_code in RETRYABLE_HTTP:
                    last = NeoApiError(f"Máy chủ trả lỗi tạm thời khi gọi {path}", http_status=r.status_code)
                else:
                    body = self._json(r)
                    code = body.get("code")
                    if body.get("status") == 1 or code in SUCCESS_CODES:
                        self.last_ok_at, self.last_error = self._clock(), None
                        return body.get("data")
                    if code == "NEOINP000004":  # không có bản ghi: hợp lệ, trả rỗng
                        self.last_ok_at = self._clock()
                        return None
                    err = NeoApiError(body.get("message") or f"NEO API báo lỗi khi gọi {path}",
                                      code=code, http_status=r.status_code)
                    if code not in RETRYABLE_CODES:
                        self.last_error = str(err)
                        raise err
                    last = err
            if attempt < self._max_retries:
                delay = min(8.0, 0.5 * 2 ** attempt)
                log.warning("%s - thử lại lần %d sau %.1fs", last, attempt + 1, delay)
                self._sleep(delay)
        self.last_error = str(last)
        raise last  # type: ignore[misc]

    @staticmethod
    def _safe_body(r: httpx.Response) -> dict:
        try:
            b = r.json()
            return b if isinstance(b, dict) else {}
        except ValueError:
            return {}

    def get_paged(self, path: str, params: dict[str, Any] | None = None,
                  page_size: int = 1000, max_pages: int = 50) -> Iterator[dict]:
        """Duyệt các trang của API phân trang kiểu Spring (data.content, data.last)."""
        page = 1
        while page <= max_pages:
            data = self.get(path, {**(params or {}), "pageNo": page, "pageSize": page_size})
            if not data:
                return
            content = data.get("content") if isinstance(data, dict) else data
            yield from (content or [])
            if not isinstance(data, dict) or data.get("last", True) or not content:
                return
            page += 1

    # ------------------------------------------------------ nhóm THỊ TRƯỜNG
    def index_list(self, exchange_code: str = "ALL") -> list[dict]:
        return list(self.get_paged("/market/indexList", {"exchangeCode": exchange_code}))

    def market_index_detail(self, index_code: str = "ALL") -> list[dict]:
        data = self.get("/market/marketIndexDetail", {"indexCode": index_code})
        return data if isinstance(data, list) else ([data] if data else [])

    def intraday_market_index(self, index_code: str) -> dict:
        return self.get("/market/intradayMarketIndex", {"indexCode": index_code}) or {}

    def market_status(self, market_code: str = "ALL") -> list[dict]:
        return self.get("/market/marketStatus", {"marketCode": market_code}) or []

    # -------------------------------------------------------- nhóm CỔ PHIẾU
    def stock_list(self, market_code: str = "ALL") -> list[dict]:
        return list(self.get_paged("/stock/stockList", {"marketCode": market_code}))

    def stock_detail(self, symbols: Iterable[str], stock_type: str | None = "ST") -> list[dict]:
        """Chi tiết cổ phiếu; tự chia lô 10 mã/lần để không vượt giới hạn của API."""
        syms = [s.strip().upper() for s in symbols if s and s.strip()]
        out: list[dict] = []
        for i in range(0, len(syms), MAX_SYMBOLS_PER_CALL):
            chunk = syms[i:i + MAX_SYMBOLS_PER_CALL]
            out.extend(self.get_paged("/stock/stockDetail",
                                      {"symbols": ",".join(chunk), "stockType": stock_type}))
        return out

    def stock_detail_by_index(self, index_code: str) -> list[dict]:
        return list(self.get_paged("/stock/stockDetailByIndex", {"indexCode": index_code}))

    def fu_stock_detail(self, stock_type: str = "FUVN30", symbols: Iterable[str] | None = None) -> list[dict]:
        return list(self.get_paged("/stock/fuStockDetail",
                                   {"stockType": stock_type,
                                    "symbols": ",".join(symbols) if symbols else None}))

    def close(self) -> None:
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
