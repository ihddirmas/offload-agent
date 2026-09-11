from datetime import datetime, timezone

from sqlalchemy import select

from offload.agents import router as router_module
from offload.agents.router import route_capture
from offload.capture import add_capture
from offload.channels import ticktick
from offload.db import session
from offload.models import Event
from tests.test_router import fake_decide


def test_payload_has_utc_offset_for_naive_and_aware_datetimes():
    aware = datetime(2026, 9, 13, 18, 0, tzinfo=timezone.utc)
    naive = datetime(2026, 9, 13, 18, 0)

    assert ticktick.build_task_payload("Pay bill", aware)["dueDate"] == "2026-09-13T18:00:00+0000"
    assert ticktick.build_task_payload("Pay bill", naive)["dueDate"] == "2026-09-13T18:00:00+0000"
    assert "dueDate" not in ticktick.build_task_payload("No due", None)


async def test_push_task_noop_when_unconfigured(monkeypatch):
    monkeypatch.delenv("TICKTICK_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("TICKTICK_TOKEN_FILE", raising=False)

    assert ticktick.is_configured() is False
    assert await ticktick.push_task("anything", None) is False


async def test_scheduler_route_mirrors_to_ticktick_when_configured(monkeypatch):
    pushed = []

    async def fake_push(title, due_at, note=""):
        pushed.append(title)
        return True

    monkeypatch.setattr(router_module.ticktick, "is_configured", lambda: True)
    monkeypatch.setattr(router_module.ticktick, "push_task", fake_push)

    capture = await add_capture("quick_add", "pay rent friday")
    due = datetime.now(timezone.utc)
    await route_capture(capture.id, decide=fake_decide("scheduler", "Pay rent", due))

    assert pushed == ["Pay rent"]
    async with session() as s:
        kinds = (await s.execute(select(Event.kind))).scalars().all()
    assert "ticktick.mirrored" in kinds


async def test_executor_route_does_not_mirror(monkeypatch):
    monkeypatch.setattr(router_module.ticktick, "is_configured", lambda: True)

    async def explode(*a, **k):
        raise AssertionError("must not push")

    monkeypatch.setattr(router_module.ticktick, "push_task", explode)
    capture = await add_capture("quick_add", "just a note")

    await route_capture(capture.id, decide=fake_decide("executor", "Write note"))
