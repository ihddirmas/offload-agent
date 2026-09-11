"""Amazon Bedrock AgentCore Runtime entrypoint for Offload's agent brain.

Deploys the router+executor as a managed AgentCore agent, while the
scheduler/Telegram surface keeps running wherever the service lives.

    uv add bedrock-agentcore bedrock-agentcore-starter-toolkit
    agentcore configure --entrypoint deploy/agentcore_app.py
    agentcore launch
"""

import asyncio

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from offload.agents.router import decide_with_strands
from offload.capture import add_capture
from offload.db import init_db

app = BedrockAgentCoreApp()
_db_ready = False


async def _handle(text: str) -> dict:
    global _db_ready
    if not _db_ready:
        await init_db()
        _db_ready = True
    capture = await add_capture("quick_add", text, device_id="agentcore")
    decision = await decide_with_strands(capture.raw_text, capture.created_at)
    return {
        "capture_id": capture.id,
        "lane": decision.lane,
        "title": decision.title,
        "due_at": decision.due_at.isoformat() if decision.due_at else None,
        "reasoning": decision.reasoning,
    }


@app.entrypoint
def invoke(payload: dict) -> dict:
    """AgentCore invocation: {"prompt": "<captured thought>"} -> routing decision."""
    text = (payload.get("prompt") or "").strip()
    if not text:
        return {"error": "empty prompt"}
    return asyncio.run(_handle(text))


if __name__ == "__main__":
    app.run()
