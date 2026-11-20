"""Shared latest-session bootstrap for the web; only derived public indicators leave SQLite."""
from __future__ import annotations

import os
import time

import httpx

from . import webexport as wx

TTL = 7 * 86400


class MarketSnapshots:
    def __init__(self, url: str, token: str, *, client=None, mono=time.monotonic):
        self.url, self.token = url.rstrip("/"), token
        self.client = client or httpx.Client(timeout=12)
        self.mono, self.next_write = mono, 0.0

    @classmethod
    def from_env(cls):
        url, token = os.environ.get("KV_REST_API_URL"), os.environ.get("KV_REST_API_TOKEN")
        return cls(url, token) if url and token else None

    def __call__(self, view, db):
        if view.source == "sim" or view.status != "ok" or self.mono() < self.next_write:
            return
        # Limit full payload writes; Ably still carries ticks and pulse between these refreshes.
        self.next_write = self.mono() + 60
        payloads = [wx.payload_from_view(view, db)]
        if view.index_code != "VNINDEX":
            other = wx.build_payload(db, view.source, view.trading_date, "VNINDEX")
            if other.get("pulse") and other["meta"]["trading_date"] == view.trading_date:
                payloads.append(other)
        commands = []
        for payload in payloads:
            meta = payload["meta"]
            code, day = meta["index_code"], meta["trading_date"]
            encoded = wx.dumps(payload)
            commands += [["SETEX", f"neopulse:market:latest:{code}", TTL, encoded],
                         ["SETEX", f"neopulse:market:session:{day}:{code}", TTL, encoded]]
        response = self.client.post(self.url + "/pipeline", json=commands, headers={"Authorization": "Bearer " + self.token})
        response.raise_for_status()
        if any(r.get("error") for r in response.json()):
            raise RuntimeError("Market snapshot store rejected update")

    def close(self):
        self.client.close()
