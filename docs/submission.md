# Devpost submission package (draft)

Track: **Everyday Agents**

## Project name

Offload — the executive-function agent

## Elevator (for the tagline field)

Type it. Forget it. The agent has it now. An ADHD executive-function agent that
captures thoughts from any device, does what it can by itself, and only surfaces
when there's a real decision to make.

## Text description (paste into Devpost)

**The problem.** ADHD working memory is a leaky bucket. Every "I should..." thought
either interrupts what you're doing or evaporates — and conventional task apps fail
because they demand exactly the executive functions that are impaired: categorizing,
scheduling, prioritizing, remembering to open the app. What's left is floating dread:
dozens of half-remembered obligations with no landing place. I built Offload for
myself first; it's the system I needed and couldn't buy.

**What it does.** Offload inverts the productivity-app contract. Capture costs
nothing: one Telegram message or one line in a web box, stored append-only in under
100 ms, zero decisions asked. All intelligence runs in the background on Strands
Agents:

- A **Router agent** classifies every capture with `structured_output` into three
  lanes — *executor* (agent can do it), *delegator* (a human message is needed),
  *scheduler* (only you can do it, at a time) — extracting a clean imperative title
  and resolving fuzzy times ("before friday") into concrete datetimes.
- An **Executor agent** with custom `@tool`s (`save_note` into an Obsidian vault,
  `notify_user` via Telegram) plus prebuilt `strands_tools` (`http_request`,
  `current_time`) actually does the executor-lane work and writes ready-to-send
  drafts for delegator-lane items.
- A **scheduler loop** fires Telegram nudges with one-tap Done / Snooze / Drop when
  scheduler-lane tasks come due — the agent surfaces only at decision points.
- A **Pattern agent** reads the append-only event log weekly and writes a short,
  non-judgmental reflection: nudge-to-done latency, abandon rates by lane. Abandoned
  tasks are data, not failure.

**Who it's for.** Adults with ADHD (or anyone with an overloaded working memory) who
have tried and abandoned every task app. The design principles come from lived
experience: capture friction kills systems; apps that must be opened don't get
opened; guilt-driven dashboards get deleted.

**How it's built.** Python + Strands Agents SDK. Amazon Bedrock is the default model
provider (Anthropic API switchable via one env var). SQLite append-only store,
APScheduler deterministic outer loop, FastAPI + Telegram Bot API as the cross-device
surface. The agent boundary is injectable everywhere, so the full
capture→route→nudge→reply loop has a test suite that runs without model calls.

## Video script (≤5 min)

| t | Scene | Voiceover beats |
|---|-------|-----------------|
| 0:00–0:30 | Title slide + the problem | "ADHD working memory is a leaky bucket... task apps demand the exact executive functions that are impaired. I built the inverse." |
| 0:30–1:00 | Architecture slide (README diagram) | "One rule: capture costs nothing, intelligence runs in the background, on Strands Agents." |
| 1:00–2:00 | **Live:** Telegram on phone — send "pay electricity bill tonight" · web inbox on laptop shows it routed to scheduler lane with a real due time | "Any device. I never told it a category or a date — the Router agent's structured output did." |
| 2:00–2:45 | **Live:** send "idk how I'll survive the sde interview prep" → routed to scheduler w/ concrete first-step title | "Anxious fragments become one small concrete step — never floating dread." |
| 2:45–3:30 | **Live:** send "remind landlord about the leaking tap" → delegator lane → draft message arrives on Telegram | "The Executor agent wrote the message. I just approve." |
| 3:30–4:00 | **Live:** nudge fires with Done/Snooze/Drop buttons; tap Done; note lands in Obsidian vault folder | "It surfaces only when there's a real decision. Everything else already happened." |
| 4:00–4:30 | Weekly pattern report | "Once a week it reflects my own data back — kindly." |
| 4:30–5:00 | Close: repo, Strands usage recap, track | "Built with Strands Agents on Bedrock. Everyday Agents track. Offload — type it, forget it." |

## Submission checklist

- [ ] Public repo URL (github.com/ihddirmas/offload-agent) — license visible in About
- [ ] README ✅ (in repo)
- [ ] Architecture diagram ✅ (mermaid in README)
- [ ] Demo video ≤5 min uploaded to YouTube/Vimeo, public
- [ ] Text description (above)
- [ ] AWS Builder ID
- [ ] (Optional) Live demo URL
- [ ] (Bonus, +0.2 each, max 0.6) builder.aws.com post(s) with "Agents for Humans" in title
