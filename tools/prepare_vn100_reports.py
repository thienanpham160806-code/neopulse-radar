"""Prepare actual VN100 reports using the existing on-demand report calculator."""
import json
import time
from pathlib import Path

import httpx

from neopulse.analytics.company_remote import fetch_report
from neopulse.timeutil import iso_vn, now_vn

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT / "web/public/data/company"
    members = json.loads((ROOT / "web/reference/vn100.json").read_text(encoding="utf-8"))["symbols"]
    assert len(members) == len(set(members)) == 100
    catalog = {r["symbol"]: r for r in json.loads((ROOT / "web/reference/catalog.json").read_text(encoding="utf-8"))["symbols"]}
    aliases = json.loads((ROOT / "web/reference/field-aliases.json").read_text(encoding="utf-8"))
    index = json.loads((ROOT / "web/public/data/charts/VNINDEX.json").read_text(encoding="utf-8"))
    prices = [[r["time"], r["value"]] for r in index["data"]]
    failed = []
    with httpx.Client(timeout=25) as client:
        for i, symbol in enumerate(members, 1):
            target = out / f"{symbol}.json"
            if target.exists():
                existing = json.loads(target.read_text(encoding="utf-8"))
                if existing.get("symbol") == symbol and existing.get("years") and existing.get("tables", {}).get("income"):
                    print(f"[{i}/100] {symbol}: cached", flush=True)
                    continue
            for attempt in range(3):
                try:
                    report = fetch_report(symbol, catalog[symbol], aliases, client, prices)
                    assert report["years"] and report["tables"]["income"] and report["tables"]["balance"]
                    temp = target.with_suffix(".tmp")
                    temp.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
                    temp.replace(target)
                    print(f"[{i}/100] {symbol}: prepared ({len(report['years'])} annual periods)", flush=True)
                    break
                except (httpx.HTTPError, ValueError, KeyError, AssertionError, TypeError) as error:
                    if attempt == 2:
                        failed.append(symbol)
                        print(f"[{i}/100] {symbol}: unavailable ({type(error).__name__})", flush=True)
                    else:
                        time.sleep(5 * (attempt + 1))
            time.sleep(1.5)
    # Preserve all earlier reports, including any outside the current basket.
    entries = []
    for path in sorted(out.glob("*.json")):
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("schema") == 1 and report.get("symbol") == path.stem and report.get("profile"):
            entries.append({"symbol": report["symbol"], "name": report["profile"].get("name"), "industry": report["profile"].get("industry")})
    (out / "index.json").write_text(json.dumps({"schema": 1, "generated_at": iso_vn(now_vn()), "symbols": entries}, ensure_ascii=False), encoding="utf-8")
    print(f"VN100 ready: {100 - len(failed)}/100; all prepared reports: {len(entries)}", flush=True)
    if failed:
        raise SystemExit("Unavailable: " + ",".join(failed))


if __name__ == "__main__":
    main()
