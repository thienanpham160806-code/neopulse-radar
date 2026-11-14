"""Cấu hình logging có lọc bí mật: JWT/Bearer token bị che trước khi ghi ra."""
from __future__ import annotations

import logging
import re

_JWT = re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}")
_BEARER = re.compile(r"(Bearer\s+)[A-Za-z0-9._-]{12,}", re.I)
_PWD = re.compile(r'("?password"?\s*[:=]\s*)"?[^",}\s]+"?', re.I)


def redact(text: str) -> str:
    text = _JWT.sub("<jwt:đã che>", text)
    text = _BEARER.sub(r"\1<đã che>", text)
    return _PWD.sub(r"\1<đã che>", text)


class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = ()
        return True


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s | %(message)s"))
    handler.addFilter(RedactFilter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
