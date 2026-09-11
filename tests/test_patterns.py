from sqlalchemy import select

from offload.agents.patterns import compute_stats, weekly_pattern_report
from offload.agents.router import route_capture
from offload.capture import add_capture
from offload.db import session
from offload.models import Event
from offload.nudger import apply_reply, check_due_tasks
from tests.test_nudger import _scheduled_task
from tests.test_router import fake_decide


async def test_stats_reflect_real_activity():
    task = await _scheduled_task(minutes_from_now=-1)

    async def ok(tid, txt):
        return True

    await check_due_tasks(send=ok)
    await apply_reply(task.id, "done")
    capture = await add_capture("telegram", "another thought")
    await route_capture(capture.id, decide=fake_decide("executor", "Do it"))

    stats = await compute_stats()

    assert stats["captures_total"] == 2
    assert stats["captures_by_source"] == {"quick_add": 1, "telegram": 1}
    assert stats["tasks_by_lane"] == {"scheduler": 1, "executor": 1}
    assert stats["nudges_sent"] == 1
    assert stats["tasks_by_state"]["done"] == 1
    assert stats["median_nudge_to_done_minutes"] is not None
    assert stats["abandon_rate"] == 0.0


async def test_empty_week_has_null_latency_and_rate():
    stats = await compute_stats()

    assert stats["captures_total"] == 0
    assert stats["median_nudge_to_done_minutes"] is None
    assert stats["abandon_rate"] is None


async def test_weekly_report_stored_as_event():
    async def fake_report(stats: dict) -> str:
        return f"you captured {stats['captures_total']} things"

    report = await weekly_pattern_report(run=fake_report)

    assert report == "you captured 0 things"
    async with session() as s:
        event = (
            await s.execute(select(Event).where(Event.kind == "pattern.report"))
        ).scalar_one()
    assert event.payload["report"] == report
    assert "captures_total" in event.payload["stats"]
