import httpx

from neopulse.analytics import company_remote


def test_latest_annual_rows_and_missing_values():
    data = {"years": [{"yearReport": y, "f": y * 10} for y in range(2010, 2026)]}
    result = company_remote.statement(data, [{"titleEn": "Revenue", "field": "f"}], {"Revenue": "revenue"})
    assert result["years"] == ["2021", "2022", "2023", "2024", "2025"]
    assert result["items"]["revenue"]["2025"] == 20250
    assert not company_remote.statement(data, [], {})["items"]


def test_provider_price_units_and_date_are_preserved(monkeypatch):
    def respond(request):
        if request.method == "POST":
            return httpx.Response(200, json=[{"t": ["1795132800"], "c": [14250]}])
        if "details" in str(request.url):
            value = {"viOrganName": "Test"}
        elif "metrics" in str(request.url):
            value = {}
        else:
            value = {"years": [{"yearReport": 2025}]}
        return httpx.Response(200, json={"data": value})

    inputs = []

    def build(raw, *_args):
        inputs.append(dict(raw))
        return {"profile": {"about": "Test"}, "notes": []}

    monkeypatch.setattr(company_remote, "build_report", build)
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        report = company_remote.fetch_report("VND", {"name": "Test"}, {}, client)
    assert inputs[-1]["prices"] == [["2026-11-20", 14.25]]
    assert report["technical"]["data"] == [{"time": "2026-11-20", "value": 14250}]
