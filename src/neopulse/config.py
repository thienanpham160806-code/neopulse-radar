"""Cấu hình tập trung, đọc từ biến môi trường / tệp .env.

Mọi bí mật (mật khẩu, token) CHỈ đi qua đây và không bao giờ được in ra log:
dùng `Settings.redacted()` khi cần hiển thị cấu hình.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path

from dotenv import load_dotenv

SECRET_FIELDS = {
    "neo_password", "neo_access_token", "ssi_consumer_secret",
    "telegram_bot_token", "llm_api_key",
}


def _csv(value: str | None) -> list[str]:
    return [x.strip().upper() for x in (value or "").split(",") if x.strip()]


@dataclass(frozen=True)
class Settings:
    mode: str = "sim"  # sim | live
    neo_username: str = ""
    neo_password: str = ""
    neo_access_token: str = ""
    neo_auth_url: str = "https://external.vpbanks.com.vn/auth/token"
    neo_base_url: str = "https://neoapi.vpbanks.com.vn/neo-api"
    neo_ws_market_url: str = "ws://neoapi.vpbanks.com.vn/stock-stream/broker"
    neo_device_id: str = "neopulse-radar"
    neo_device_type: str = "Chrome"
    neo_max_rps: float = 4.0
    universe_index: str = "VN30"
    extra_symbols: list[str] = field(default_factory=list)
    indexes: list[str] = field(default_factory=lambda: ["VNINDEX", "VN30", "HNXINDEX", "UPCOMINDEX"])
    db_path: str = "data/neopulse.sqlite"
    ssi_consumer_id: str = ""
    ssi_consumer_secret: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    @property
    def is_live(self) -> bool:
        return self.mode == "live"

    @property
    def has_neo_credentials(self) -> bool:
        return bool(self.neo_access_token or (self.neo_username and self.neo_password))

    def redacted(self) -> dict:
        """Bản cấu hình an toàn để in/log: bí mật chỉ còn trạng thái đã/chưa điền."""
        out = {}
        for f in fields(self):
            v = getattr(self, f.name)
            if f.name in SECRET_FIELDS:
                out[f.name] = "<đã điền>" if v else "<trống>"
            elif f.name == "neo_username":
                out[f.name] = (v[:3] + "***") if v else "<trống>"
            else:
                out[f.name] = v
        return out


def load_settings(env_file: str | os.PathLike | None = None) -> Settings:
    """Nạp cấu hình. Biến môi trường thật luôn thắng giá trị trong .env."""
    if env_file is None:
        env_file = Path.cwd() / ".env"
    if Path(env_file).exists():
        load_dotenv(env_file, override=False)
    g = os.environ.get
    mode = (g("NEOPULSE_MODE", "sim") or "sim").strip().lower()
    if mode not in {"sim", "live"}:
        raise ValueError(f"NEOPULSE_MODE phải là 'sim' hoặc 'live', nhận được: {mode!r}")
    rps = float(g("NEO_MAX_RPS", "4") or 4)
    if not 0 < rps <= 5:
        raise ValueError("NEO_MAX_RPS phải trong (0, 5] - NEO API giới hạn 5 request/giây.")
    return Settings(
        mode=mode,
        neo_username=g("NEO_USERNAME", "").strip(),
        neo_password=g("NEO_PASSWORD", ""),
        neo_access_token=g("NEO_ACCESS_TOKEN", "").strip(),
        neo_auth_url=g("NEO_AUTH_URL", Settings.neo_auth_url).strip(),
        neo_base_url=g("NEO_BASE_URL", Settings.neo_base_url).strip().rstrip("/"),
        neo_ws_market_url=g("NEO_WS_MARKET_URL", Settings.neo_ws_market_url).strip(),
        neo_device_id=g("NEO_DEVICE_ID", Settings.neo_device_id).strip(),
        neo_device_type=g("NEO_DEVICE_TYPE", Settings.neo_device_type).strip(),
        neo_max_rps=rps,
        universe_index=(g("NEOPULSE_UNIVERSE_INDEX", "VN30") or "VN30").strip().upper(),
        extra_symbols=_csv(g("NEOPULSE_EXTRA_SYMBOLS")),
        indexes=_csv(g("NEOPULSE_INDEXES")) or ["VNINDEX", "VN30", "HNXINDEX", "UPCOMINDEX"],
        db_path=g("NEOPULSE_DB_PATH", "data/neopulse.sqlite").strip(),
        ssi_consumer_id=g("SSI_CONSUMER_ID", "").strip(),
        ssi_consumer_secret=g("SSI_CONSUMER_SECRET", "").strip(),
        telegram_bot_token=g("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_chat_id=g("TELEGRAM_CHAT_ID", "").strip(),
        llm_api_key=g("LLM_API_KEY", "").strip(),
        llm_model=g("LLM_MODEL", "").strip(),
    )
