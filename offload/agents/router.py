from datetime import datetime, timezone
from typing import Awaitable, Callable, Literal

from pydantic import BaseModel, Field
from sqlalchemy import select

import logging

from offload.agents.model_factory import build_model
from offload.channels import ticktick
from offload.db import session
from offload.models import Capture, Event, Task

log = logging.getLogger("offload")

ROUTER_SYSTEM_PROMPT = """\
You are the routing brain of Offload, an executive-function assistant for a person
with ADHD. You receive one raw captured thought (typed or forwarded in a rush,
possibly fragmentary) and decide what should happen to it, so the person never has
to hold it in their head again.

Lanes:
- executor: the agent itself can complete this right now (drafting a message,
  looking something up, summarizing, writing a note into their knowledge vault).
- delegator: a message to another person is needed; the agent should prepare a
  draft for the user to approve and send.
- scheduler: it needs to be done by the person at/near a time — schedule a nudge.

Rules:
- Fragmentary anxious thoughts ("idk how I'll do X") become a scheduler task with
  a small concrete first step as the title, never left as floating dread.
- Titles are short imperative actions ("Email landlord about lease"), not copies
  of the raw text.
- If a time is implied ("tomorrow", "before friday", "tonight"), resolve it to a
  concrete datetime using the provided current time. Prefer daytime hours.
- When no time is implied for a scheduler task, pick a sensible default within
  the next 24 hours.
"""


class RoutingDecision(BaseModel):
    lane: Literal["executor", "delegator", "scheduler"]
    title: str = Field(description="Short imperative task title")
    due_at: datetime | None = Field(
        default=None, description="When to nudge, ISO 8601 with timezone; scheduler lane only"
    )
    reasoning: str = Field(description="One sentence: why this lane")


DecideFn = Callable[[str, datetime], Awaitable[RoutingDecision]]


async def decide_with_strands(raw_text: str, now: datetime) -> RoutingDecision:
    from strands import Agent

    agent = Agent(
        model=build_model(),
        system_prompt=ROUTER_SYSTEM_PROMPT,
        callback_handler=None,
    )
    return await agent.structured_output_async(
        RoutingDecision,
        f"Current time: {now.isoformat()}\n\nCaptured thought:\n{raw_text}",
    )


async def route_capture(capture_id: str, decide: DecideFn = decide_with_strands) -> Task:
    """Route one capture into a task. The only mutation of captures is the routed flag."""
    now = datetime.now(timezone.utc)
    async with session() as s:
        capture = (
            await s.execute(select(Capture).where(Capture.id == capture_id))
        ).scalar_one()
        decision = await decide(capture.raw_text, now)

        state = "awaiting_response" if decision.lane == "delegator" else (
            "scheduled" if decision.lane == "scheduler" else "captured"
        )
        task = Task(
            capture_id=capture.id,
            title=decision.title,
            lane=decision.lane,
            state=state,
            due_at=decision.due_at,
        )
        capture.routed = True
        s.add(task)
        s.add(
            Event(
                kind="capture.routed",
                payload={
                    "capture_id": capture.id,
                    "lane": decision.lane,
                    "reasoning": decision.reasoning,
                },
            )
        )
        await s.commit()
        await s.refresh(task)

    if decision.lane == "scheduler" and ticktick.is_configured():
        try:
            mirrored = await ticktick.push_task(
                decision.title, decision.due_at, note=f"Offload: {capture.raw_text[:200]}"
            )
        except Exception:
            log.exception("ticktick mirror failed for task %s", task.id)
            mirrored = False
        if mirrored:
            async with session() as s:
                s.add(Event(kind="ticktick.mirrored", payload={"task_id": task.id}))
                await s.commit()
    return task
