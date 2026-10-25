# State machine

| From | Operation | To | Notes |
| --- | --- | --- | --- |
| — | create | `pending` | unique create `event_id` |
| `pending` | claim | `claimed` | atomic `BEGIN IMMEDIATE` claim |
| `pending` | cancel | `cancelled` | producer-side only by API convention |
| `claimed` | progress | `running` | same claimed worker |
| `running` | progress | `running` | same claimed worker |
| `claimed` / `running` | complete | `done` | same claimed worker |
| `claimed` / `running` | fail | `failed` | same claimed worker |

`done`, `failed`, and `cancelled` are terminal. The store rejects progress, messages, completion, failure, or cancellation after a terminal transition.

Messages (`question`, `answer`, `progress`, `note`) do not independently change task status and are rejected once the task is terminal.
