# Agents for Humans: Building Offload, an ADHD Executive-Function Agent with Strands

> Draft for builder.aws.com — review before publishing. Title keeps "Agents for
> Humans" per bonus rules.

I have ADHD. Over the years I've built an embarrassing graveyard of productivity
systems — task apps, Obsidian vaults, kanban boards, sync pipelines between all of
them. Each one worked for two weeks, then became one more thing to maintain. The
pattern is brutal and well-known in the ADHD community: **task systems demand the
exact executive functions that are impaired** — categorizing, scheduling,
prioritizing, and above all *remembering to open the app*.

For the Agents for Humans hackathon I built the inverse: an agent that maintains
the system so I don't have to. It's called
[Offload](https://github.com/ihddirmas/offload-agent), and its contract is one
sentence: *type it, forget it, the agent has it now.*

## The one design rule everything follows

Capture must cost nothing. One Telegram message from my phone, or one line in a web
box — stored append-only in under 100 ms, zero questions asked. No category picker,
no due-date field, no priority dropdown. Any decision demanded at capture time is a
reason the thought stays in my head instead, and thoughts that stay in my head
evaporate.

Everything intelligent happens *after* the write, in the background, on
[Strands Agents](https://strandsagents.com).

## Three agents, three very different jobs

**The Router agent** classifies every raw capture into one of three lanes. This is
where Strands' `structured_output` earned its keep — I define a Pydantic model and
the agent must return it:

```python
class RoutingDecision(BaseModel):
    lane: Literal["executor", "delegator", "scheduler"]
    title: str            # short imperative, never the raw text
    due_at: datetime | None
    reasoning: str

decision = await agent.structured_output_async(
    RoutingDecision,
    f"Current time: {now.isoformat()}\n\nCaptured thought:\n{raw_text}",
)
```

No JSON parsing, no retry-on-malformed-output loops. The system prompt encodes ADHD
domain knowledge that generic task apps never have: fragmentary anxious thoughts
("idk how I'll do X") become a scheduler task whose title is a small concrete first
step — never left as floating dread.

**The Executor agent** actually does the executor-lane work. Strands' `@tool`
decorator made the custom tools trivial — `save_note` writes polished markdown into
my Obsidian vault, `notify_user` pushes to my phone — and they compose cleanly with
prebuilt tools from `strands-agents-tools` (`http_request`, `current_time`). For
"delegator" items (a message to another human is needed), the same agent writes a
ready-to-send draft: right tone, no placeholders, mine to approve.

**The Pattern agent** runs weekly over an append-only event log and reflects my own
behavior back at me — nudge-to-done latency, abandon rate by lane — with a system
prompt that forbids moralizing. Abandoned tasks are data, not failure. That single
prompt line is the difference between a report I'll read and a dashboard I'll
delete.

## The part that surprised me: the agent loop is mostly *not* an LLM

The hackathon brief said it best: the agent should run in the background and only
surface when there's a real decision. In practice that meant a deterministic outer
loop (APScheduler polling an SQLite store) that *invokes* Strands agents at
decision points — routing a new capture, executing a task, writing the weekly
report. Nudges fire as Telegram messages with one-tap Done / Snooze / Drop buttons.
The LLM never sits in the hot path of a reminder firing, which keeps the system
cheap, fast, and predictable — and keeps the agent invisible until it's useful.

## AWS pieces

- **Amazon Bedrock** is the default model provider — Strands' `BedrockModel` made
  this a constructor call, and switching to a direct Anthropic API key for local
  dev is one env var (`MODEL_PROVIDER`), because the model factory is four lines.
- **Bedrock AgentCore Runtime** hosts the routing brain as a managed agent
  (`deploy/agentcore_app.py` wraps it with `BedrockAgentCoreApp` + an
  `@app.entrypoint`), so the intelligence scales independently of the little
  FastAPI surface that owns Telegram and the web inbox.

## What I'd tell you if you're building your own

1. **Put the schema in the type system, not the prompt.** `structured_output` with
   Pydantic beats "respond in JSON" every time.
2. **Make the agent boundary injectable.** Every agent call in Offload accepts a
   `decide=`/`run=` callable, so the entire capture→route→nudge→reply loop has a
   test suite (24 tests) that runs without a single model call.
3. **Domain knowledge belongs in system prompts.** The difference between a generic
   task bot and something that actually helps an ADHD brain is ~30 lines of prompt
   encoding how ADHD thoughts arrive and what they need to become.
4. **Let the boring parts be boring.** Schedulers, buttons, and SQLite don't need
   agency. Spend the intelligence where judgment lives.

Offload is MIT-licensed:
[github.com/ihddirmas/offload-agent](https://github.com/ihddirmas/offload-agent).
Built with Strands Agents SDK for the AWS Agents for Humans hackathon, Everyday
Agents track.
