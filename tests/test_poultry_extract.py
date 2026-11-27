import json
from datetime import date

import httpx
import pytest

from eu_poultry_pipeline import extract


def test_bronze_keeps_the_payload_and_where_it_came_from(tmp_path):
    payload = [
        {
            "memberStateCode": "PT",
            "memberStateName": "Portugal",
            "price": "€180.17",
            "productName": "Broiler",
        }
    ]

    path = extract.save_bronze(
        payload,
        tmp_path,
        member_state_codes=["PT", "ES"],
    )

    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["payload"] == payload
    assert record["_member_state"] == "ES-PT"
    assert record["_record_count"] == 1
    assert "_ingested_at" in record
    assert "member_state=ES-PT" in str(path)


def fake_answer(status_code):
    """Replace httpx.Client.get with a function that returns a fixed status, without the
    internet.
    """

    def fake_get(self, url, params=None):
        return httpx.Response(status_code, json=[], request=httpx.Request("GET", url))

    return fake_get


def test_a_server_error_is_temporary(monkeypatch):
    monkeypatch.setattr(httpx.Client, "get", fake_answer(503))
    with pytest.raises(extract.TemporarySourceError):
        extract.get_poultry_prices(
            member_state_codes=["PT"],
            begin_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )


def test_a_bad_request_is_permanent(monkeypatch):
    monkeypatch.setattr(httpx.Client, "get", fake_answer(400))
    with pytest.raises(httpx.HTTPStatusError):
        extract.get_poultry_prices(
            member_state_codes=["PT"],
            begin_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )
