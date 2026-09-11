from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

from sqlalchemy import select

from offload.channels.telegram import send_nudge
from offload.config import DEFAULT_SNOOZE_MINUTES
from offload.db import session
from offload.models import Event, Nudge, Task

SendFn = Callable[[str, str], Awaitable[bool]]


async def check_due_tasks(send: SendFn = send_nudge) -> list[str]:
    """Notice scheduled tasks that are due, nudge them. Returns nudged task ids."""
    now = datetime.now(timezone.utc)
    nudged: list[str] = []
    async with session() as s:
        rows = await s.execute(
            select(Task).where(Task.state == "scheduled", Task.due_at <= now)
        )
        for task in rows.scalars():
            delivered = await send(task.id, f"⏰ {task.title}")
            task.state = "nudged"
            s.add(Nudge(task_id=task.id, delivered=delivered))
            s.add(Event(kind="nudge.sent", payload={"task_id": task.id, "delivered": delivered}))
            nudged.append(task.id)
        await s.commit()
    return nudged


async def apply_reply(task_id: str, action: str) -> Task | None:
    """Handle a done/snooze/abandon reply from any channel."""
    async with session() as s:
        task = (await s.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
        if task is None:
            return None
        if action == "done":
            task.state = "done"
        elif action == "abandon":
            task.state = "abandoned"
        elif action == "snooze":
            task.state = "scheduled"
            base = datetime.now(timezone.utc)
            task.due_at = base + timedelta(minutes=DEFAULT_SNOOZE_MINUTES)
        else:
            return None
        s.add(Event(kind=f"task.{action}", payload={"task_id": task.id}))
        await s.commit()
        await s.refresh(task)
        return task
