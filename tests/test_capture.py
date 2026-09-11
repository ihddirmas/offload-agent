import pytest

from offload.capture import add_capture, list_unrouted


async def test_capture_round_trips_payload_unmodified():
    payload = {"note": "buy protein powder", "nested": {"a": 1}}
    row = await add_capture("quick_add", "buy protein powder", payload, device_id="laptop")

    assert row.id
    assert row.raw_text == "buy protein powder"
    assert row.raw_payload == payload
    assert row.routed is False


async def test_unknown_source_type_rejected():
    with pytest.raises(ValueError):
        await add_capture("carrier_pigeon", "hello")


async def test_empty_text_rejected():
    with pytest.raises(ValueError):
        await add_capture("quick_add", "   ")


async def test_unrouted_listing_returns_in_capture_order():
    await add_capture("quick_add", "first thought")
    await add_capture("telegram", "second thought")

    unrouted = await list_unrouted()

    assert [c.raw_text for c in unrouted] == ["first thought", "second thought"]
