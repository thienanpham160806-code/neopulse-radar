import json

import httpx
from cryptography.fernet import Fernet

from neopulse.analytics.telegram_store import RedisUsers, handle_update


def test_encrypted_registration_replay_stop_and_compare_swap_retry():
    data, members = {}, set()
    fail_once = [True]

    def redis(request):
        command, *args = json.loads(request.content)
        if command == "GET":
            result = data.get(args[0])
        elif command == "EVAL":
            _, _, address, _, old, new, active = args
            if fail_once.pop() if fail_once else False:
                result = 0
            elif data.get(address, "") != old:
                result = 0
            else:
                data[address] = new
                (members.add if active == "1" else members.discard)(address)
                result = 1
        elif command == "SMEMBERS":
            result = list(members)
        elif command == "MGET":
            result = [data.get(k) for k in args]
        else:
            raise AssertionError(command)
        return httpx.Response(200, json={"result": result})

    def update(i, text):
        return {"update_id": i, "message": {"chat": {"type": "private", "id": 123456789}, "text": text}}

    with httpx.Client(transport=httpx.MockTransport(redis)) as client:
        store = RedisUsers("https://redis.test", "secret", Fernet.generate_key().decode(), client)
        answer = handle_update(store, update(1, "/start"), {"VND"}, 100)
        assert "https://neopulse-radar.vercel.app" in answer[1]
        assert "123456789" not in str(data)
        assert len(store.users()) == 1
        assert handle_update(store, update(1, "/start"), {"VND"}, 101) is None
        handle_update(store, update(2, "/watch VND"), {"VND"}, 102)
        assert store.read("123456789")["user"]["symbols"] == ["VND"]
        handle_update(store, update(3, "/stop"), {"VND"}, 103)
        assert store.users() == {}
        assert "cid" not in store.read("123456789")
        # A replay of /start cannot resurrect a deleted subscription.
        assert handle_update(store, update(1, "/start"), {"VND"}, 104) is None
        assert store.read("123456789")["user"] is None
