from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from offload.agents.router import RoutingDecision, route_capture
from offload.capture import add_capture, list_unrouted
from offload.db import session
from offload.models import Event


def fake_decide(lane: str, title: str, due_at=None):
    async def _decide(raw_text: str, now: datetime) -> RoutingDecision:
        return RoutingDecision(lane=lane, title=title, due_at=due_at, reasoning="test")

    return _decide


async def test_scheduler_capture_becomes_scheduled_task_with_due_time():
    due = datetime.now(timezone.utc) + timedelta(hours=2)
    capture = await add_capture("quick_add", "pay electricity bill tonight")

    task = await route_capture(
        capture.id, decide=fake_decide("scheduler", "Pay electricity bill", due)
    )

    assert task.lane == "scheduler"
    assert task.state == "scheduled"
    assert task.due_at is not None
    assert task.capture_id == capture.id


async def test_delegator_capture_awaits_response():
    capture = await add_capture("telegram", "ask landlord about the leak")

    task = await route_capture(
        capture.id, decide=fake_decide("delegator", "Message landlord about leak")
    )

    assert task.state == "awaiting_response"


async def test_routed_capture_leaves_unrouted_queue_and_logs_event():
    capture = await add_capture("quick_add", "note to self")
    await route_capture(capture.id, decide=fake_decide("executor", "Write note"))

    assert await list_unrouted() == []
    async with session() as s:
        kinds = (await s.execute(select(Event.kind))).scalars().all()
    assert "capture.routed" in kinds
