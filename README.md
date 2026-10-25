# 共享任务箱

A small, provider-neutral task bridge for **existing chat products that need to hand explicit technical work to an existing coding worker**.

This candidate intentionally does **not** become a general multi-agent framework. The host chat keeps its own conversations, personality, memory, UI, auth, and model choices. The bridge stores only task data that the host explicitly submits.

> 当前项目名：**共享任务箱**。开源许可证：**MIT License**。

## Problem

A chat product can be good at understanding a user's request while a separate coding worker is better placed to edit files, run tests, or work for longer. Without a bridge, a person often relays instructions and results manually between the two.

共享任务箱 provides a narrow contract:

1. the chat side explicitly creates a task;
2. one coding worker atomically claims it;
3. producer and worker exchange scoped task-thread messages;
4. the worker reports progress and a terminal result;
5. an optional adapter emits **minimal metadata** so the host can decide whether to surface or wake anything.

The core only guarantees durable task storage and task-thread coordination. It does **not** promise that a normal browser chat can be awakened in the background, and it does **not** launch coding workers by itself.

## Architecture

```text
Existing chat product                    Existing coding worker
┌──────────────────────┐                 ┌──────────────────────┐
│ conversations/memory │                 │ editor/shell/git/etc │
│ remain host-owned    │                 │ remain worker-owned  │
└──────────┬───────────┘                 └──────────┬───────────┘
           │ explicit ProducerClient                │ WorkerClient
           ▼                                        ▼
       ┌───────────────────────────────────────────────────┐
       │               共享任务箱                │
       │ tasks | task_events | task_messages               │
       │ idempotency | atomic claim | task-thread cursor   │
       └──────────────────────┬────────────────────────────┘
                              │ minimal notification metadata
                              ▼
                    host-supplied adapter
              (push/webhook/session wake/none)
```

The bridge has no API that scans a host chat database. Task content enters only through `create(...)` or the corresponding CLI command.

## Quick start

Python 3.10+; the core has no runtime dependencies outside the standard library.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .

shared-task-box --db demo.db create \
  --event-id create-001 \
  --title "Add parser tests" \
  --content "Add regression tests for the parser"

shared-task-box --db demo.db claim \
  --event-id claim-001 \
  --worker worker-a
```

## Full loop

The included `examples/full_loop.py` demonstrates:

```text
create → claim → question → answer → progress → complete → result
```

Run it with:

```bash
PYTHONPATH=src python examples/full_loop.py
```

The producer and worker examples use their own temporary or demo database. They do not import or inspect any host application source.

## Core guarantees

- SQLite persistence with WAL and foreign keys.
- `tasks` stores current state.
- `task_events` is an append-only audit log with unique `event_id` values.
- `task_messages` stores only `question`, `answer`, `progress`, and `note` thread messages.
- States: `pending`, `claimed`, `running`, `done`, `failed`, `cancelled`.
- Every write takes an idempotency key (`event_id`).
- Claims run inside `BEGIN IMMEDIATE`, so competing workers cannot both claim the same pending task.
- Only `pending` tasks can be cancelled.
- Terminal tasks are read-only.
- Message reads support an `after_id` cursor.
- Public reads apply defensive redaction to structured sensitive fields and common credential-like patterns.
- Notification callbacks receive only minimal task metadata: `task_id`, `title`, `status`, `kind`, and optional `message_id`.

See `docs/STATE_MACHINE.md`, `docs/API_CLI.md`, and `docs/MIGRATIONS.md`.

## Producer / chat-side API

```python
from shared_task_box import TaskBridge, ProducerClient

bridge = TaskBridge("tasks.db")
chat = ProducerClient(bridge, sender="chat-host")

created = chat.create(
    event_id="create-42",
    title="Fix CSV parser",
    content="Handle quoted newlines and add tests.",
    context={"repo_ref": "checkout-a"},
)
```

The bridge knows nothing about where that task text came from. The host is responsible for deciding what conversation material, if any, to explicitly place into the task.

## Worker API

```python
from shared_task_box import TaskBridge, WorkerClient

worker = WorkerClient(TaskBridge("tasks.db"), worker="worker-a")
claimed = worker.claim(event_id="claim-42")
if claimed["claimed"]:
    task = claimed["task"]
    worker.progress(task["id"], event_id="progress-42", text="tests added")
    worker.complete(task["id"], event_id="done-42", result="Implemented and verified")
```

## Notifications and waking hosts

`TaskBridge(..., notifier=...)` accepts a callback. The default package does not perform networking and does not wake sessions. `JsonlNotifier` and `examples/host_notification.py` demonstrate the boundary.

There are three separate concerns:

1. **Store task state** — guaranteed by this package.
2. **Wake an already-running host session** — possible only if the host exposes an appropriate push/session API; supply an adapter.
3. **Start a new worker process** — an orchestration choice outside this package; supply an adapter or supervisor.

A typical browser chat cannot be assumed to support reliable background wake-up. The bridge therefore never claims that persistence equals delivery.

## Security and privacy model

- No automatic chat-history discovery.
- No model-provider API dependency.
- No remote service, account, or relay is required by the core.
- SQLite database path is host-configurable.
- Notification metadata excludes task content, context, results, and message bodies.
- Redaction is defense-in-depth for public reads; it is **not** a substitute for avoiding credentials in submitted task text.
- Worker execution permissions are outside this package. The bridge does not grant shell, Git, browser, filesystem, or network access.
- An untrusted caller with direct filesystem access to the SQLite database can read raw stored task content. Protect the database with normal OS permissions.

See `SECURITY.md`.

## Where this differs from nearby projects

This space already has useful projects. This candidate does not claim to be first or universally better.

| Project | Publicly described focus | Difference in this candidate |
| --- | --- | --- |
| [HakAl/agent-comms](https://github.com/HakAl/agent-comms) | Local SQLite mailbox for multiple terminal-based coding agents, with MCP messaging/status tools | This candidate is task-centric and designed to embed into an existing chat product; it does not maintain a general agent directory/mailbox |
| [sushiHex/hardline-mcp](https://github.com/sushiHex/hardline-mcp) | Durable shared mailbox, named session lanes, wake signals, and delegated agent jobs | This candidate deliberately avoids session ownership and worker launching; those are adapter concerns |
| [office233/free-coding-agent](https://github.com/office233/free-coding-agent) | Provider-neutral coding execution layer plus durable multi-agent task kernel and verification gates | This candidate supplies no workstation/execution tools or verifier loop; it only bridges an existing chat host to an existing worker |
| [daniel-aranda/Agents-todo](https://github.com/daniel-aranda/Agents-todo) | Repo-local SQLite task queue for humans/Codex with project-bound workflow | This candidate is host-embeddable, includes producer/worker thread messaging and minimal notification adapters, and is not tied to a Git repo |
| [Dicklesworthstone/mcp_agent_mail](https://github.com/Dicklesworthstone/mcp_agent_mail) | Mail-like multi-agent coordination with identities, searchable history, and file reservations | This candidate is not an agent directory/mail system and has no file-reservation feature |
| [tkellogg/postal-mcp](https://github.com/tkellogg/postal-mcp) | HTTP MCP mailbox for agents to send/check messages | This candidate models explicit task state, atomic claiming, terminal results, and a producer/worker boundary rather than a general mailbox |

The practical niche is deliberately narrow: **drop a task handoff protocol into a chat product without importing that product's chat/memory model into the bridge**.

## Optional MCP adapter

`examples/mcp_adapter.py` shows how a host may expose selected producer/worker operations through MCP when the `mcp` Python package is installed. The core package does not depend on MCP or any model vendor.

## Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/privacy_scan.py .
```

Coverage includes duplicate `event_id`, concurrent claiming, illegal transitions, cancellation, terminal-write rejection, message cursors, redaction, minimal notifications, CLI round-trip, and the complete producer/worker loop.

## Project name and license

项目名确定为 **共享任务箱**。Python distribution 名称使用 `shared-task-box`，导入模块使用 `shared_task_box`。

本项目采用 **MIT License**：允许使用、修改、分发、商用和闭源集成，只需保留版权与许可证声明。

## Current limitations

- SQLite is appropriate for a local/single-host bridge, not an internet-scale distributed queue.
- Claims do not currently expire; abandoned work requires an explicit recovery policy added by the embedding host.
- There are no task priorities, dependencies, leases, or verification gates in this intentionally small core.
- Redaction catches common patterns but cannot guarantee removal of arbitrary secrets.
- Notification callbacks are best-effort from the caller's process; durable external delivery needs an adapter/outbox if required.
- The core does not authenticate producer/worker identity. Embed it behind the host's trust boundary or add an authenticated transport adapter.

## Release status

`v0.1.0` is the first public GitHub release of **共享任务箱**. Source is published at `furong0302-crypto/shared-task-box` under the MIT License. PyPI publication is intentionally separate and has not been performed yet.
