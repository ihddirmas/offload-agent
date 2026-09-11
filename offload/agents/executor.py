import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

from sqlalchemy import select
from strands import tool

from offload.agents.model_factory import build_model
from offload.channels import ticktick
from offload.channels.telegram import send_text
from offload.db import session
from offload.models import Capture, Event, Task

EXECUTOR_SYSTEM_PROMPT = """\
You are the hands of Offload, an executive-function assistant for a person with
ADHD. You receive one task the routing brain decided you can handle. Do the work
now, completely, with the tools you have — the whole point is that the person
never has to think about this again.

- For notes/ideas/things-to-remember: polish into a useful note and call save_note.
- For information lookups: use http_request, then send the answer with notify_user.
- For messages to other people (delegated drafts): write the message ready to
  copy-paste — right tone, no placeholders left — and call notify_user with it.
- Be brief. One tool call chain, no essays. Finish by returning a one-line summary
  of what you did.
"""


def _notes_dir() -> Path:
    return Path(os.getenv("NOTES_DIR", "notes-out"))


def _write_note(title: str, content: str) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "note"
    path = _notes_dir() / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    path.write_text(
        f"---\ntitle: {title}\ncaptured: {stamp}\nsource: offload-agent\n---\n\n{content}\n",
        encoding="utf-8",
    )
    return path


@tool
def save_note(title: str, content: str) -> str:
    """Save a polished markdown note into the user's knowledge vault inbox."""
    path = _write_note(title, content)
    return f"saved note to {path}"


@tool
async def notify_user(message: str) -> str:
    """Send a short message to the user's phone (Telegram)."""
    ok = await send_text(message)
    return "delivered" if ok else "delivery failed"


@tool
async def add_task_to_ticktick(title: str, due_at_iso: str = "") -> str:
    """Add a task to the user's TickTick task manager, optionally with an ISO 8601 due time."""
    due = datetime.fromisoformat(due_at_iso) if due_at_iso else None
    ok = await ticktick.push_task(title, due)
    return "added to TickTick" if ok else "TickTick not configured"


RunFn = Callable[[Task, str], Awaitable[str]]


async def run_with_strands(task: Task, raw_text: str) -> str:
    from strands import Agent
    from strands_tools import current_time, http_request

    agent = Agent(
        model=build_model(),
        system_prompt=EXECUTOR_SYSTEM_PROMPT,
        tools=[save_note, notify_user, add_task_to_ticktick, current_time, http_request],
        callback_handler=None,
    )
    result = await agent.invoke_async(
        f"Task: {task.title}\nLane: {task.lane}\nOriginal captured thought:\n{raw_text}"
    )
    return str(result).strip()


async def execute_task(task_id: str, run: RunFn = run_with_strands) -> Task | None:
    """Run the executor agent on one task and record the outcome."""
    async with session() as s:
        task = (await s.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
        if task is None or task.result is not None:
            return task
        raw_text = ""
        if task.capture_id:
            capture = (
                await s.execute(select(Capture).where(Capture.id == task.capture_id))
            ).scalar_one_or_none()
            raw_text = capture.raw_text if capture else ""
    try:
        summary = await run(task, raw_text)
    except Exception as exc:
        summary = None
        error = repr(exc)
    async with session() as s:
        task = (await s.execute(select(Task).where(Task.id == task_id))).scalar_one()
        if summary is None:
            s.add(Event(kind="task.execute_failed", payload={"task_id": task.id, "error": error}))
        else:
            task.result = summary
            if task.lane == "executor":
                task.state = "done"
            s.add(Event(kind="task.executed", payload={"task_id": task.id, "lane": task.lane}))
        await s.commit()
        await s.refresh(task)
        return task


async def process_actionable_tasks(run: RunFn = run_with_strands) -> list[str]:
    """Background job: run executor on new executor-lane tasks and delegator drafts."""
    async with session() as s:
        rows = await s.execute(
            select(Task.id).where(
                Task.result.is_(None),
                (
                    (Task.lane == "executor") & (Task.state == "captured")
                    | (Task.lane == "delegator") & (Task.state == "awaiting_response")
                ),
            )
        )
        ids = list(rows.scalars())
    for task_id in ids:
        await execute_task(task_id, run=run)
    return ids
