from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from offload.agents.router import route_capture
from offload.capture import add_capture
from offload.db import session
from offload.models import Nudge, Task
from offload.nudger import apply_reply, check_due_tasks
from tests.test_router import fake_decide


async def _scheduled_task(minutes_from_now: int) -> Task:
    capture = await add_capture("quick_add", "pay the bill")
    due = datetime.now(timezone.utc) + timedelta(minutes=minutes_from_now)
    return await route_capture(capture.id, decide=fake_decide("scheduler", "Pay bill", due))


async def test_due_task_gets_nudged_once():
    task = await _scheduled_task(minutes_from_now=-1)
    sent: list[str] = []

    async def fake_send(task_id: str, text: str) -> bool:
        sent.append(text)
        return True

    nudged = await check_due_tasks(send=fake_send)

    assert nudged == [task.id]
    assert sent == ["⏰ Pay bill"]
    assert await check_due_tasks(send=fake_send) == []  # nudged state, not re-nudged
    async with session() as s:
        nudge = (await s.execute(select(Nudge))).scalar_one()
    assert nudge.delivered is True


async def test_future_task_not_nudged():
    await _scheduled_task(minutes_from_now=60)

    async def fail_send(task_id: str, text: str) -> bool:
        raise AssertionError("should not send")

    assert await check_due_tasks(send=fail_send) == []


async def test_snooze_reschedules_into_future():
    task = await _scheduled_task(minutes_from_now=-1)
    await check_due_tasks(send=lambda tid, txt: _true())

    updated = await apply_reply(task.id, "snooze")

    assert updated.state == "scheduled"
    assert updated.due_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)


async def test_done_reply_completes_task():
    task = await _scheduled_task(minutes_from_now=-1)

    updated = await apply_reply(task.id, "done")

    assert updated.state == "done"


async def test_unknown_action_ignored():
    task = await _scheduled_task(minutes_from_now=-1)
    assert await apply_reply(task.id, "explode") is None
    assert await apply_reply("missing-id", "done") is None


async def _true():
    return True
