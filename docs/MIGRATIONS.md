# Database migrations

The candidate starts with `migrations/001_initial.sql`.

It creates exactly three application tables:

- `tasks` — mutable current state;
- `task_events` — append-only event/audit history with unique `event_id`;
- `task_messages` — scoped thread messages with unique `event_id`.

SQLite's internal `sqlite_sequence` table may also exist because integer autoincrement keys are used.

`TaskStore` applies the initial schema automatically. Future releases should add numbered, forward-only migrations and a small schema-version table rather than editing already-applied migration files in place.

The database path is supplied by the embedding host. The package never searches for another application's database.
