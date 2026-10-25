from pathlib import Path


def migration_sql() -> str:
    here = Path(__file__).resolve()
    candidate = here.parents[2] / "migrations" / "001_initial.sql"
    if candidate.exists():
        return candidate.read_text(encoding="utf-8")
    # Installed wheels do not include repository-level migrations by default.
    return _FALLBACK


_FALLBACK = r'''
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS tasks (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 create_event_id TEXT NOT NULL UNIQUE,
 sender TEXT NOT NULL, assignee TEXT NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL,
 context_json TEXT NOT NULL DEFAULT '{}',
 status TEXT NOT NULL CHECK (status IN ('pending','claimed','running','done','failed','cancelled')),
 claimed_by TEXT NOT NULL DEFAULT '', progress TEXT NOT NULL DEFAULT '', result TEXT NOT NULL DEFAULT '',
 last_error TEXT NOT NULL DEFAULT '', created_at REAL NOT NULL, updated_at REAL NOT NULL,
 claimed_at REAL, completed_at REAL
);
CREATE TABLE IF NOT EXISTS task_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE,
 task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
 actor TEXT NOT NULL, action TEXT NOT NULL, from_status TEXT NOT NULL DEFAULT '',
 to_status TEXT NOT NULL DEFAULT '', detail_json TEXT NOT NULL DEFAULT '{}', created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS task_messages (
 id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE,
 task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
 author TEXT NOT NULL, kind TEXT NOT NULL CHECK (kind IN ('question','answer','progress','note')),
 content TEXT NOT NULL, created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee_status ON tasks(assignee,status,created_at,id);
CREATE INDEX IF NOT EXISTS idx_task_events_task ON task_events(task_id,id);
CREATE INDEX IF NOT EXISTS idx_task_messages_task ON task_messages(task_id,id);
'''
