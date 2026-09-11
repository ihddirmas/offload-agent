# Deploying Offload

## Option A — anywhere (simplest)

Offload is a single FastAPI service with an embedded scheduler:

```bash
uv run uvicorn offload.api:app --host 0.0.0.0 --port 8000
```

Any box that can keep a process alive works (EC2 t4g.nano, Lightsail, a Pi).
Point the Telegram webhook at `https://<host>/telegram/webhook`.

## Option B — Amazon Bedrock AgentCore Runtime (agent brain, managed)

[deploy/agentcore_app.py](agentcore_app.py) wraps the Router agent as an AgentCore
entrypoint so the classification brain runs fully managed on AWS:

```bash
uv add bedrock-agentcore bedrock-agentcore-starter-toolkit
uv run agentcore configure --entrypoint deploy/agentcore_app.py
uv run agentcore launch          # builds + deploys to AgentCore Runtime
uv run agentcore invoke '{"prompt": "pay electricity bill tonight"}'
```

Prereqs: AWS credentials configured, Bedrock model access enabled for the
Claude model in `BEDROCK_MODEL_ID`, and Docker running (AgentCore builds a
container image).

The FastAPI surface (Telegram webhook, web inbox, nudge scheduler) still runs as
in Option A and can call the AgentCore-hosted brain instead of the in-process
one by swapping `decide_with_strands` for an `agentcore invoke` client call.
