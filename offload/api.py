import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from pydantic import BaseModel
from sqlalchemy import select

from offload.agents.router import route_capture
from offload.capture import add_capture, list_unrouted
from offload.db import init_db, session
from offload.models import Task
from offload.nudger import apply_reply, check_due_tasks

log = logging.getLogger("offload")


async def route_unrouted_captures() -> None:
    for capture in await list_unrouted():
        try:
            task = await route_capture(capture.id)
            log.info("routed %s -> %s lane=%s", capture.id, task.title, task.lane)
        except Exception:
            log.exception("routing failed for capture %s", capture.id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(route_unrouted_captures, "interval", seconds=15)
    scheduler.add_job(check_due_tasks, "interval", seconds=30)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Offload", lifespan=lifespan)


class CaptureIn(BaseModel):
    text: str
    source_type: str = "quick_add"
    device_id: str | None = None


@app.post("/capture")
async def capture_endpoint(body: CaptureIn):
    row = await add_capture(body.source_type, body.text, device_id=body.device_id)
    return {"id": row.id}


@app.get("/tasks")
async def list_tasks():
    async with session() as s:
        rows = (await s.execute(select(Task).order_by(Task.created_at.desc()))).scalars()
        return [
            {
                "id": t.id,
                "title": t.title,
                "lane": t.lane,
                "state": t.state,
                "due_at": t.due_at.isoformat() if t.due_at else None,
                "result": t.result,
            }
            for t in rows
        ]


class ReplyIn(BaseModel):
    action: str


@app.post("/tasks/{task_id}/reply")
async def reply_endpoint(task_id: str, body: ReplyIn):
    task = await apply_reply(task_id, body.action)
    return {"ok": task is not None, "state": task.state if task else None}


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    update = await request.json()
    callback = update.get("callback_query")
    if callback:
        action, _, task_id = callback.get("data", "").partition(":")
        if task_id:
            await apply_reply(task_id, action)
        return {"ok": True}
    message = update.get("message") or {}
    text = (message.get("text") or "").strip()
    if text:
        await add_capture("telegram", text, raw_payload=message, device_id="telegram")
    return {"ok": True}
