import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Awaitable, Callable

from sqlalchemy import select

from offload.agents.model_factory import build_model
from offload.db import session
from offload.models import Capture, Event, Task

PATTERN_SYSTEM_PROMPT = """\
You are the weekly reflection module of Offload, an executive-function assistant
for a person with ADHD. You receive a week of behavioral stats from their own
task system. Write a short, kind, non-judgmental report:

- 2 or 3 concrete observations grounded in the numbers (name the numbers).
- 1 practical suggestion (e.g. shift nudge times, split a lane differently).
- Never moralize about productivity. Abandoned tasks are data, not failure.
- Max 120 words, plain text.
"""


async def compute_stats(days: int = 7) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    async with session() as s:
        captures = (
            (await s.execute(select(Capture).where(Capture.created_at >= cutoff)))
            .scalars()
            .all()
        )
        tasks = (
            (await s.execute(select(Task).where(Task.created_at >= cutoff))).scalars().all()
        )
        events = (
            (await s.execute(select(Event).where(Event.created_at >= cutoff))).scalars().all()
        )

    nudge_times: dict[str, datetime] = {}
    done_times: dict[str, datetime] = {}
    for e in events:
        task_id = e.payload.get("task_id")
        if not task_id:
            continue
        if e.kind == "nudge.sent" and task_id not in nudge_times:
            nudge_times[task_id] = e.created_at
        elif e.kind == "task.done":
            done_times[task_id] = e.created_at

    latencies = [
        (done_times[tid] - nudge_times[tid]).total_seconds() / 60
        for tid in done_times
        if tid in nudge_times
    ]

    states = Counter(t.state for t in tasks)
    total_closed = states["done"] + states["abandoned"]
    return {
        "window_days": days,
        "captures_total": len(captures),
        "captures_by_source": dict(Counter(c.source_type for c in captures)),
        "tasks_by_lane": dict(Counter(t.lane for t in tasks)),
        "tasks_by_state": dict(states),
        "abandon_rate": round(states["abandoned"] / total_closed, 2) if total_closed else None,
        "median_nudge_to_done_minutes": round(median(latencies), 1) if latencies else None,
        "nudges_sent": sum(1 for e in events if e.kind == "nudge.sent"),
    }


RunReportFn = Callable[[dict], Awaitable[str]]


async def run_report_with_strands(stats: dict) -> str:
    from strands import Agent

    agent = Agent(model=build_model(), system_prompt=PATTERN_SYSTEM_PROMPT, callback_handler=None)
    result = await agent.invoke_async(
        f"This week's stats as JSON:\n{json.dumps(stats, indent=2)}"
    )
    return str(result).strip()


async def weekly_pattern_report(run: RunReportFn = run_report_with_strands) -> str:
    """Compute the week's stats, have the pattern agent narrate them, store the report."""
    stats = await compute_stats()
    report = await run(stats)
    async with session() as s:
        s.add(Event(kind="pattern.report", payload={"report": report, "stats": stats}))
        await s.commit()
    return report
