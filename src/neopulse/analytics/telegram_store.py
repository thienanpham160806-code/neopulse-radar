"""Đăng ký Redis: mã hóa Fernet, khóa HMAC, CAS chống ghi đè giữa webhook và worker."""
from __future__ import annotations

import hashlib
import hmac
import json
import os

import httpx
from cryptography.fernet import Fernet

INDEX = "neopulse:telegram:users"
CAS = """
local old=redis.call('GET', KEYS[1])
if (old or '') ~= ARGV[1] then return 0 end
redis.call('SET',KEYS[1],ARGV[2])
if ARGV[3]=='1' then redis.call('SADD',KEYS[2],KEYS[1])
else redis.call('SREM',KEYS[2],KEYS[1]);redis.call('EXPIRE',KEYS[1],604800) end
return 1
"""


class RedisUsers:
    def __init__(self, url: str, token: str, key: str, client: httpx.Client):
        self.url, self.token, self.key, self.client = url.rstrip("/"), token, key, client
        self.cipher = Fernet(key.encode())

    @classmethod
    def from_env(cls, client):
        return cls(os.environ["KV_REST_API_URL"], os.environ["KV_REST_API_TOKEN"], os.environ["TELEGRAM_STATE_KEY"], client)

    def call(self, *args):
        r = self.client.post(self.url, headers={"Authorization": f"Bearer {self.token}"}, json=list(args))
        if r.status_code != 200:
            raise RuntimeError("Redis unavailable")
        d = r.json()
        if d.get("error"):
            raise RuntimeError("Redis command failed")
        return d.get("result")

    def address(self, cid: str):
        digest = hmac.new(self.key.encode(), cid.encode(), hashlib.sha256).hexdigest()
        return f"neopulse:telegram:user:{digest}"

    def decode(self, raw):
        return json.loads(self.cipher.decrypt(raw.encode())) if raw else {"version": -1, "user": None}

    def read(self, cid):
        return self.decode(self.call("GET", self.address(cid)))

    def update(self, cid, mutate):
        address = self.address(cid)
        for _ in range(8):
            old = self.call("GET", address)
            record = self.decode(old)
            new = mutate(record)
            if new is None:
                return record
            if new.get("user"):
                new["cid"] = cid
            else:
                new.pop("cid", None)
            encrypted = self.cipher.encrypt(json.dumps(new, separators=(",", ":")).encode()).decode()
            if self.call("EVAL", CAS, 2, address, INDEX, old or "", encrypted, "1" if new.get("user") else "0"):
                return new
        raise RuntimeError("Redis update conflict")

    def users(self):
        keys = self.call("SMEMBERS", INDEX) or []
        out = {}
        for start in range(0, len(keys), 100):
            for raw in self.call("MGET", *keys[start:start + 100]):
                if raw:
                    r = self.decode(raw)
                    if r.get("user"):
                        out[r["cid"]] = r["user"]
        return out


def handle_update(store, update: dict, valid: set[str], now: float):
    from .telegram_cloud import command
    message = update.get("message", {})
    chat = message.get("chat", {})
    if chat.get("type") != "private" or not isinstance(chat.get("id"), int) or not isinstance(update.get("update_id"), int):
        return None
    cid, reply = str(chat["id"]), []

    def mutate(record):
        reply.clear()
        if update["update_id"] <= record["version"]:
            return None
        state = {"users": {cid: record["user"]} if record.get("user") else {}}
        answer = command(state, update, valid, now)
        if answer:
            reply.append(answer)
        return {"version": update["update_id"], "user": state["users"].get(cid)}

    store.update(cid, mutate)
    return reply[0] if reply else None
