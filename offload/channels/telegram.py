import httpx

from offload.config import get_settings

API_BASE = "https://api.telegram.org"


async def send_nudge(task_id: str, text: str) -> bool:
    """Send a nudge with Done/Snooze buttons. Falls back to console when unconfigured."""
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        print(f"[nudge:console] {text} (task {task_id})")
        return True
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{API_BASE}/bot{settings.telegram_bot_token}/sendMessage",
            json={
                "chat_id": settings.telegram_chat_id,
                "text": text,
                "reply_markup": {
                    "inline_keyboard": [
                        [
                            {"text": "✅ Done", "callback_data": f"done:{task_id}"},
                            {"text": "😴 Snooze", "callback_data": f"snooze:{task_id}"},
                            {"text": "🗑 Drop", "callback_data": f"abandon:{task_id}"},
                        ]
                    ]
                },
            },
        )
        return resp.status_code == 200


async def send_text(text: str) -> bool:
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        print(f"[msg:console] {text}")
        return True
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{API_BASE}/bot{settings.telegram_bot_token}/sendMessage",
            json={"chat_id": settings.telegram_chat_id, "text": text},
        )
        return resp.status_code == 200
