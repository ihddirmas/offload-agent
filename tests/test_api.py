import httpx

from offload.api import app
from offload.capture import list_unrouted


def client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_capture_endpoint_writes_row():
    async with client() as c:
        resp = await c.post("/capture", json={"text": "buy milk", "device_id": "web"})

    assert resp.status_code == 200
    assert resp.json()["id"]
    assert len(await list_unrouted()) == 1


async def test_inbox_page_served():
    async with client() as c:
        resp = await c.get("/")
    assert resp.status_code == 200
    assert "Offload" in resp.text


async def test_telegram_webhook_text_message_becomes_capture():
    update = {"message": {"text": "remember to call mom", "chat": {"id": 1}}}
    async with client() as c:
        resp = await c.post("/telegram/webhook", json=update)

    assert resp.status_code == 200
    unrouted = await list_unrouted()
    assert unrouted[0].raw_text == "remember to call mom"
    assert unrouted[0].source_type == "telegram"


async def test_telegram_webhook_callback_applies_reply():
    async with client() as c:
        await c.post("/capture", json={"text": "pay rent"})
        # route it manually through the API-free path
        from offload.agents.router import route_capture
        from tests.test_router import fake_decide

        captures = await list_unrouted()
        task = await route_capture(captures[0].id, decide=fake_decide("scheduler", "Pay rent"))

        resp = await c.post(
            "/telegram/webhook", json={"callback_query": {"data": f"done:{task.id}"}}
        )
        assert resp.status_code == 200

        tasks = (await c.get("/tasks")).json()
    assert tasks[0]["state"] == "done"
