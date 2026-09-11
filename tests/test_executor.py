from sqlalchemy import select

from offload.agents.executor import _write_note, execute_task, process_actionable_tasks
from offload.agents.router import route_capture
from offload.capture import add_capture
from offload.db import session
from offload.models import Event, Task
from tests.test_router import fake_decide


async def _routed_task(lane: str, title: str) -> Task:
    capture = await add_capture("quick_add", f"raw thought for {title}")
    return await route_capture(capture.id, decide=fake_decide(lane, title))


async def fake_run(task, raw_text) -> str:
    return f"did: {task.title}"


async def test_executor_lane_task_completes_with_result():
    task = await _routed_task("executor", "Summarize article")

    updated = await execute_task(task.id, run=fake_run)

    assert updated.state == "done"
    assert updated.result == "did: Summarize article"


async def test_delegator_draft_keeps_awaiting_response():
    task = await _routed_task("delegator", "Message landlord")

    updated = await execute_task(task.id, run=fake_run)

    assert updated.state == "awaiting_response"
    assert updated.result == "did: Message landlord"


async def test_failure_logged_and_task_left_retryable():
    task = await _routed_task("executor", "Flaky thing")

    async def boom(task, raw_text):
        raise RuntimeError("model unavailable")

    updated = await execute_task(task.id, run=boom)

    assert updated.result is None
    assert updated.state == "captured"
    async with session() as s:
        kinds = (await s.execute(select(Event.kind))).scalars().all()
    assert "task.execute_failed" in kinds


async def test_process_actionable_picks_both_lanes_but_not_scheduler():
    a = await _routed_task("executor", "Do thing")
    b = await _routed_task("delegator", "Draft thing")
    await _routed_task("scheduler", "Later thing")

    processed = await process_actionable_tasks(run=fake_run)

    assert set(processed) == {a.id, b.id}
    assert await process_actionable_tasks(run=fake_run) == []  # idempotent


def test_write_note_creates_frontmatter_file(tmp_path, monkeypatch):
    monkeypatch.setenv("NOTES_DIR", str(tmp_path))

    path = _write_note("Buy Protein Powder!", "remember the unflavored kind")

    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\ntitle: Buy Protein Powder!")
    assert "unflavored" in text
