# API and CLI reference

## Python surface

### ProducerClient

- `create(event_id, title, content, assignee="coding-worker", context={})`
- `answer(task_id, event_id, content)`
- `note(task_id, event_id, content)`
- `cancel(task_id, event_id, reason="")`
- `task(task_id)`
- `result(task_id)`
- `messages(task_id, after_id=0, limit=100)`

### WorkerClient

- `claim(event_id, task_id=0)` — `task_id=0` claims the oldest matching pending task.
- `question(task_id, event_id, content)`
- `note(task_id, event_id, content)`
- `progress(task_id, event_id, text)`
- `complete(task_id, event_id, result)`
- `fail(task_id, event_id, reason, next_step="")`
- `messages(task_id, after_id=0, limit=100)`
- `task(task_id)`

### TaskStore

Low-level methods mirror the same operations and expose `list_tasks`, `read_messages`, `read_result`, and `get_task`. Public reads are redacted.

## CLI

All commands accept `--db PATH` before the subcommand.

```text
create --event-id ID --title TITLE --content BODY [--sender ID] [--assignee ID] [--context-json JSON]
list [--assignee ID] [--status STATUS] [--limit N]
get TASK_ID
claim --event-id ID --worker ID [--assignee ID] [--task-id TASK_ID]
progress TASK_ID --event-id ID --worker ID --text TEXT
question TASK_ID --event-id ID --worker ID --content TEXT
answer TASK_ID --event-id ID [--sender ID] --content TEXT
note TASK_ID --event-id ID --author ID --content TEXT
messages TASK_ID [--after-id MESSAGE_ID] [--limit N]
complete TASK_ID --event-id ID --worker ID --result TEXT
fail TASK_ID --event-id ID --worker ID --reason TEXT [--next-step TEXT]
cancel TASK_ID --event-id ID [--sender ID] [--reason TEXT]
result TASK_ID
```

## Idempotency

Every mutating call requires an `event_id`. Repeating the same `event_id` for the same action returns the already-recorded outcome. Reusing an `event_id` for a different action raises `IdempotencyConflict`.
