from datetime import datetime

import httpx

from neopulse.analytics import company_remote


def test_latest_annual_rows_and_missing_values():
    data = {"years": [{"yearReport": y, "f": y * 10} for y in range(2010, 2026)]}
    result = company_remote.statement(data, [{"titleEn": "Revenue", "field": "f"}], {"Revenue": "revenue"})
    assert result["years"] == ["2021", "2022", "2023", "2024", "2025"]
    assert result["items"]["revenue"]["2025"] == 20250
    assert not company_remote.statement(data, [], {})["items"]


def test_provider_price_units_and_date_are_preserved(monkeypatch):
    requested = []
    def respond(request):
        requested.append(str(request.url))
        if "section=INCOME_STATEMENT" in str(request.url) and "language=vi" not in str(request.url):
            raise httpx.ReadTimeout("temporary statement timeout", request=request)
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
    monkeypatch.setattr(company_remote, "now_vn", lambda: datetime(2026, 11, 21, tzinfo=company_remote.VN_TZ))
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        report = company_remote.fetch_report("VND", {"name": "Test"}, {}, client)
    assert inputs[-1]["prices"] == [["2026-11-20", 14.25]]
    assert report["technical"]["data"] == [{"time": "2026-11-20", "value": 14250}]
    assert any("section=INCOME_STATEMENT&language=vi" in url for url in requested)
    monkeypatch.setattr(company_remote, "now_vn", lambda: datetime(2026, 11, 20, 10, tzinfo=company_remote.VN_TZ))
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        forming = company_remote.fetch_report("VND", {"name": "Test"}, {}, client)
    assert forming["technical"]["data"] == []


def test_disclosures_keep_all_events_and_only_vietstock_links():
    def respond(request):
        if "events" in request.url.path:
            return httpx.Response(200, json={"data": {"content": [
                {"publicDate": "2025-01-02T00:00:00", "eventTitleVi": "Cũ", "eventNameVi": "Cổ tức"},
                {"publicDate": "2026-05-01T00:00:00", "eventTitleVi": " Mới ", "eventNameVi": "Niêm yết thêm"},
                {"publicDate": "2026-06-01T00:00:00", "eventTitleVi": None}]}})
        return httpx.Response(200, json=[
            {"Title": "Tin  thật", "PublishTime": "2026-11-20T10:00:00", "URL": "/2026/11/tin-that-830-1.htm"},
            {"Title": "Lạ", "PublishTime": "2026-11-20T10:00:00", "URL": "javascript:alert(1)"},
            {"Title": "Ngoài", "PublishTime": "2026-11-20T10:00:00", "URL": "//evil.example/2026/11/x.htm"}])

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        got = company_remote.fetch_disclosures("HAG", client)
    assert [e["title"] for e in got["events"]] == ["Mới", "Cũ"]
    assert got["news"] == [{"date": "2026-11-20", "title": "Tin thật", "url": "https://vietstock.vn/2026/11/tin-that-830-1.htm", "source": "Vietstock"}]

    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))) as client:
        assert company_remote.fetch_disclosures("HAG", client) == {"events": [], "news": []}
