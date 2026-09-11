import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

TASKS_URL = "https://api.ticktick.com/open/v1/task"


def _access_token() -> str | None:
    token = os.getenv("TICKTICK_ACCESS_TOKEN")
    if token:
        return token
    token_file = os.getenv("TICKTICK_TOKEN_FILE")
    if token_file and Path(token_file).exists():
        try:
            data = json.loads(Path(token_file).read_text(encoding="utf-8"))
            return data.get("access_token")
        except (OSError, json.JSONDecodeError):
            return None
    return None


def is_configured() -> bool:
    return _access_token() is not None


def build_task_payload(title: str, due_at: datetime | None, note: str = "") -> dict:
    payload: dict = {"title": title, "content": note or "via Offload agent"}
    if due_at:
        if due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=timezone.utc)
        payload["dueDate"] = due_at.strftime("%Y-%m-%dT%H:%M:%S%z")
        payload["isAllDay"] = False
    return payload


async def push_task(title: str, due_at: datetime | None, note: str = "") -> bool:
    """Mirror a scheduler-lane task into TickTick. No-op when unconfigured."""
    token = _access_token()
    if not token:
        return False
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            TASKS_URL,
            json=build_task_payload(title, due_at, note),
            headers={"Authorization": f"Bearer {token}"},
        )
        return resp.status_code == 200
