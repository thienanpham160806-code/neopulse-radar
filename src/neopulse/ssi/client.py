"""SSI FastConnect REST client (API v3): lấy token bằng API key/secret, giới hạn tần suất, thử lại.

Chỉ đọc dữ liệu thị trường. Token lấy KHÔNG kèm OTP nên về nguyên tắc chỉ đọc được dữ liệu
(theo tài liệu SSI: token không có OTP chỉ dùng cho dữ liệu thị trường).

Nguồn đặc tả: https://developers.ssi.com.vn/docs/getting-started/first-api-call (truy cập 18/11/2026).
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from ..config import Settings
from ..neo_api.errors import NeoSafetyError
from ..neo_api.ratelimit import RateLimiter

log = logging.getLogger(__name__)

# Mọi đường dẫn có thể đụng tới lệnh/tài khoản đều bị cấm trong đồ án này.
FORBIDDEN_PATH_PREFIXES = ("/api/v3/trading", "/api/v3/account")
EP_TOKEN = "/api/v3/auth/token"
EP_SECURITIES_BY_BOARD = "/api/v3/data/securitiesByBoard"
EP_INDEX_LIST = "/api/v3/data/indexList"
EP_INDEX_SUMMARY = "/api/v3/data/indexSummary"
EP_OHLC = "/api/v3/data/ohlc"
EP_SECURITIES_SUMMARY = "/api/v3/data/securitiesSummary"
EP_MASTERDATA = "/api/v3/data/masterdata"
TOKEN_REFRESH_MARGIN_S = 120
RETRYABLE_HTTP = {429, 500, 502, 503, 504}


class SsiApiError(Exception):
    def __init__(self, message: str, *, http_status: int | None = None):
        super().__init__(message)
        self.http_status = http_status

    def __str__(self) -> str:
        base = super().__str__()
        return f"{base} (HTTP {self.http_status})" if self.http_status else base


class SsiAuthError(SsiApiError):
    """Sai API key/secret, key bị thu hồi hoặc chưa được cấp quyền dữ liệu."""


def rows_of(body: Any) -> list[dict]:
    """Phản hồi có thể là mảng trần hoặc {data: [...]} có phân trang - lấy danh sách bản ghi."""
    if isinstance(body, list):
        return [x for x in body if isinstance(x, dict)]
    if isinstance(body, dict):
        data = body.get("data")
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
    return []


class SsiClient:
    def __init__(self, settings: Settings, *, transport: httpx.BaseTransport | None = None,
                 limiter: RateLimiter | None = None, max_retries: int = 3,
                 sleep=time.sleep, clock=time.time):
        self.s = settings
        self._http = httpx.Client(timeout=httpx.Timeout(20.0, connect=8.0), transport=transport)
        self._limiter = limiter or RateLimiter(settings.ssi_max_rps, burst=1)
        self._max_retries = max_retries
        self._sleep, self._clock = sleep, clock
        self._token: str | None = None
        self._token_expiry = 0.0
        self.request_count = 0
        self.last_error: str | None = None

    # ------------------------------------------------------------------ auth
    def login(self) -> str:
        if not self.s.has_ssi_credentials:
            raise SsiAuthError("Thiếu SSI_API_KEY / SSI_API_SECRET trong .env.")
        self._limiter.acquire()
        try:
            r = self._http.post(f"{self.s.ssi_api_url}{EP_TOKEN}",
                                json={"apiKey": self.s.ssi_api_key, "apiSecret": self.s.ssi_api_secret},
                                headers={"Content-Type": "application/json"})
        except httpx.HTTPError as e:
            raise SsiApiError(f"Không kết nối được máy chủ SSI: {type(e).__name__}") from e
        body = self._json(r)
        data = body.get("data") if isinstance(body.get("data"), dict) else body
        token = data.get("accessToken")
        if r.status_code >= 400 or not token:
            raise SsiAuthError(str(body.get("message") or body.get("error") or "Lấy token thất bại"),
                               http_status=r.status_code)
        self._token = token
        exp = data.get("expiresAt")
        # expiresAt là epoch giây theo tài liệu; nếu thiếu/không hợp lệ thì giả định 55 phút.
        self._token_expiry = float(exp) if isinstance(exp, (int, float)) and exp > self._clock() else self._clock() + 3300
        log.info("Lấy token SSI thành công; còn hiệu lực ~%d giây", max(0, int(self._token_expiry - self._clock())))
        return token

    def token(self) -> str:
        if not self._token or self._clock() >= self._token_expiry - TOKEN_REFRESH_MARGIN_S:
            self.login()
        return self._token  # type: ignore[return-value]

    @property
    def token_expiry(self) -> float:
        """Epoch giây token hết hạn (0 nếu chưa đăng nhập) - bộ phát WebSocket dùng để nối lại trước hạn."""
        return self._token_expiry

    # --------------------------------------------------------------- request
    @staticmethod
    def _json(r: httpx.Response) -> Any:
        try:
            return r.json()
        except ValueError:
            raise SsiApiError("Phản hồi không phải JSON", http_status=r.status_code) from None

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if any(path.startswith(p) for p in FORBIDDEN_PATH_PREFIXES):
            raise NeoSafetyError(f"Endpoint {path} bị chặn: đồ án không được đụng tới lệnh/tài khoản thật.")
        params = {k: v for k, v in (params or {}).items() if v is not None}
        relogin_done = False
        last: Exception | None = None
        for attempt in range(self._max_retries + 1):
            self._limiter.acquire()
            self.request_count += 1
            try:
                r = self._http.get(f"{self.s.ssi_api_url}{path}", params=params,
                                   headers={"Authorization": f"Bearer {self.token()}",
                                            "Content-Type": "application/json"})
            except httpx.HTTPError as e:
                last = SsiApiError(f"Lỗi mạng khi gọi {path}: {type(e).__name__}")
            else:
                if r.status_code == 401 and not relogin_done:
                    relogin_done = True
                    log.warning("Token SSI bị từ chối (401) - lấy token mới một lần.")
                    self._token = None
                    continue
                if r.status_code in (401, 403):
                    err = SsiAuthError("Không được phép truy cập - kiểm tra API key và quyền dữ liệu",
                                       http_status=r.status_code)
                    self.last_error = str(err)
                    raise err
                if r.status_code in RETRYABLE_HTTP:
                    last = SsiApiError(f"Máy chủ SSI tạm thời lỗi khi gọi {path}", http_status=r.status_code)
                elif r.status_code >= 400:
                    err = SsiApiError(f"Yêu cầu {path} bị từ chối", http_status=r.status_code)
                    self.last_error = str(err)
                    raise err
                else:
                    return self._json(r)
            if attempt < self._max_retries:
                wait = min(8.0, 0.5 * 2 ** attempt)
                log.warning("Thử lại %s sau %.1fs (%s)", path, wait, last)
                self._sleep(wait)
        self.last_error = str(last)
        raise last if last else SsiApiError("Lỗi không xác định")

    # ------------------------------------------------------------- nghiệp vụ
    def securities_by_index(self, index: str) -> list[dict]:
        return rows_of(self.get(EP_SECURITIES_BY_BOARD, {"index": index.upper()}))

    def securities_by_board(self, board: str) -> list[dict]:
        return rows_of(self.get(EP_SECURITIES_BY_BOARD, {"board": board.upper()}))

    def index_list(self, board: str | None = None) -> list[dict]:
        return rows_of(self.get(EP_INDEX_LIST, {"board": board}))

    def index_summary(self, index: str, trading_date: str | None = None) -> list[dict]:
        return rows_of(self.get(EP_INDEX_SUMMARY, {"index": index.upper(), "tradingDate": trading_date}))

    def masterdata(self, page_size: int = 1000) -> list[dict]:
        """Trần/sàn/tham chiếu của PHIÊN HÔM NAY cho mọi mã (4 sàn, ~2.100 mã, 3 trang).

        Luồng `market.<mã>` không gửi các giá này trong phiên (kiểm chứng 19/11/2026) nên phải lấy qua REST."""
        out: list[dict] = []
        for page in range(1, 50):
            body = self.get(EP_MASTERDATA, {"pageIndex": page, "pageSize": page_size})
            out.extend(rows_of(body))
            pages = int(body.get("pagesCount") or 1) if isinstance(body, dict) else 1
            if page >= pages:
                break
        return out

    def daily_ohlc(self, symbol: str, from_date: str, to_date: str, page_size: int = 1000) -> list[dict]:
        """Nến ngày (from/to dạng 'YYYY/MM/DD HH:MM:SS' theo SDK chính thức); đi hết các trang."""
        out: list[dict] = []
        for page in range(1, 50):
            body = self.get(EP_OHLC, {"symbol": symbol.upper(), "from": from_date, "to": to_date,
                                      "timeFrame": "1d", "pageIndex": page, "pageSize": page_size})
            rows = rows_of(body)
            out.extend(rows)
            if len(rows) < page_size:
                break
        return out

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> SsiClient:
        return self

    def __exit__(self, *exc) -> None:
        self.close()
