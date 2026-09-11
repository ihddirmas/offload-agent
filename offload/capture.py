from sqlalchemy import select

from offload.config import VALID_SOURCE_TYPES
from offload.db import session
from offload.models import Capture, Event


async def add_capture(
    source_type: str,
    raw_text: str,
    raw_payload: dict | None = None,
    device_id: str | None = None,
) -> Capture:
    """Fast append-only write. No classification or agent calls happen here."""
    if source_type not in VALID_SOURCE_TYPES:
        raise ValueError(f"unknown source_type: {source_type}")
    if not raw_text.strip():
        raise ValueError("raw_text must not be empty")
    async with session() as s:
        capture = Capture(
            source_type=source_type,
            raw_text=raw_text,
            raw_payload=raw_payload or {},
            device_id=device_id,
        )
        s.add(capture)
        s.add(Event(kind="capture.created", payload={"source_type": source_type}))
        await s.commit()
        await s.refresh(capture)
        return capture


async def list_unrouted() -> list[Capture]:
    async with session() as s:
        rows = await s.execute(
            select(Capture).where(Capture.routed.is_(False)).order_by(Capture.created_at)
        )
        return list(rows.scalars())
