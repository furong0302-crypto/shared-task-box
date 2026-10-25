from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

from .errors import IdempotencyConflict, InvalidTransition, NotFound
from .redact import redact
from .schema import migration_sql

STATUSES = {"pending", "claimed", "running", "done", "failed", "cancelled"}
TERMINAL = {"done", "failed", "cancelled"}
MESSAGE_KINDS = {"question", "answer", "progress", "note"}


def _now() -> float:
    return time.time()


class TaskStore:
    """SQLite persistence for a small chat-to-worker task bridge.

    Each public write requires an idempotency event_id. The store owns only its
    own task database; it has no code for discovering or reading host chat data.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = str(Path(db_path))
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_lock = threading.Lock()
        self._initialized = False
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path, timeout=10.0, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def initialize(self) -> None:
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            db = self._connect()
            try:
                db.executescript(migration_sql())
            finally:
                db.close()
            self._initialized = True

    @contextmanager
    def _write(self):
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _event(self, db: sqlite3.Connection, event_id: str) -> sqlite3.Row | None:
        return db.execute("SELECT * FROM task_events WHERE event_id=?", (event_id,)).fetchone()

    def _idempotent_task(self, db: sqlite3.Connection, event_id: str, action: str) -> dict[str, Any] | None:
        ev = self._event(db, event_id)
        if not ev:
            return None
        if ev["action"] != action:
            raise IdempotencyConflict(
                f"event_id {event_id!r} already belongs to action {ev['action']!r}"
            )
        return self._task_dict(db, int(ev["task_id"]))

    def _task_row(self, db: sqlite3.Connection, task_id: int) -> sqlite3.Row:
        row = db.execute("SELECT * FROM tasks WHERE id=?", (int(task_id),)).fetchone()
        if not row:
            raise NotFound(f"task {task_id} not found")
        return row

    def _task_dict(self, db: sqlite3.Connection, task_id: int, *, public: bool = True) -> dict[str, Any]:
        row = self._task_row(db, task_id)
        out = dict(row)
        out["context"] = json.loads(out.pop("context_json") or "{}")
        out["events"] = [self._event_dict(r, public=public) for r in db.execute(
            "SELECT * FROM task_events WHERE task_id=? ORDER BY id", (task_id,)
        ).fetchall()]
        return redact(out) if public else out

    @staticmethod
    def _event_dict(row: sqlite3.Row, *, public: bool = True) -> dict[str, Any]:
        out = dict(row)
        out["detail"] = json.loads(out.pop("detail_json") or "{}")
        return redact(out) if public else out

    @staticmethod
    def _message_dict(row: sqlite3.Row, *, public: bool = True) -> dict[str, Any]:
        out = dict(row)
        return redact(out) if public else out

    @staticmethod
    def _insert_event(
        db: sqlite3.Connection,
        *,
        event_id: str,
        task_id: int,
        actor: str,
        action: str,
        from_status: str,
        to_status: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        db.execute(
            "INSERT INTO task_events(event_id,task_id,actor,action,from_status,to_status,detail_json,created_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (
                event_id,
                int(task_id),
                actor,
                action,
                from_status,
                to_status,
                json.dumps(detail or {}, ensure_ascii=False, sort_keys=True),
                _now(),
            ),
        )

    @staticmethod
    def _assert_mutable(row: sqlite3.Row) -> None:
        if row["status"] in TERMINAL:
            raise InvalidTransition(f"task is terminal ({row['status']}); terminal tasks are read-only")

    @staticmethod
    def _assert_worker(row: sqlite3.Row, worker: str) -> None:
        claimed_by = row["claimed_by"] or ""
        if claimed_by and claimed_by != worker:
            raise InvalidTransition(f"task is claimed by {claimed_by!r}, not {worker!r}")

    def create_task(
        self,
        *,
        event_id: str,
        sender: str,
        assignee: str,
        title: str,
        content: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._write() as db:
            old = self._idempotent_task(db, event_id, "create")
            if old is not None:
                return {"ok": True, "idempotent": True, "task": old}
            ts = _now()
            cur = db.execute(
                "INSERT INTO tasks(create_event_id,sender,assignee,title,content,context_json,status,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?, 'pending', ?, ?)",
                (
                    event_id,
                    sender,
                    assignee,
                    title,
                    content,
                    json.dumps(context or {}, ensure_ascii=False, sort_keys=True),
                    ts,
                    ts,
                ),
            )
            task_id = int(cur.lastrowid)
            self._insert_event(
                db,
                event_id=event_id,
                task_id=task_id,
                actor=sender,
                action="create",
                from_status="",
                to_status="pending",
                detail={"assignee": assignee, "title": title},
            )
            return {"ok": True, "idempotent": False, "task": self._task_dict(db, task_id)}

    def claim_task(
        self,
        *,
        event_id: str,
        worker: str,
        assignee: str = "coding-worker",
        task_id: int = 0,
    ) -> dict[str, Any]:
        with self._write() as db:
            old = self._idempotent_task(db, event_id, "claim")
            if old is not None:
                return {"ok": True, "idempotent": True, "claimed": old["claimed_by"] == worker, "task": old}
            if task_id:
                row = db.execute(
                    "SELECT * FROM tasks WHERE id=? AND assignee=? AND status='pending'",
                    (int(task_id), assignee),
                ).fetchone()
            else:
                row = db.execute(
                    "SELECT * FROM tasks WHERE assignee=? AND status='pending' ORDER BY created_at,id LIMIT 1",
                    (assignee,),
                ).fetchone()
            if not row:
                return {"ok": True, "idempotent": False, "claimed": False, "task": None}
            ts = _now()
            cur = db.execute(
                "UPDATE tasks SET status='claimed',claimed_by=?,claimed_at=?,updated_at=? "
                "WHERE id=? AND status='pending'",
                (worker, ts, ts, int(row["id"])),
            )
            if cur.rowcount != 1:
                return {"ok": True, "idempotent": False, "claimed": False, "task": None}
            self._insert_event(
                db,
                event_id=event_id,
                task_id=int(row["id"]),
                actor=worker,
                action="claim",
                from_status="pending",
                to_status="claimed",
                detail={"assignee": assignee},
            )
            return {
                "ok": True,
                "idempotent": False,
                "claimed": True,
                "task": self._task_dict(db, int(row["id"])),
            }

    def update_progress(self, *, task_id: int, event_id: str, worker: str, progress: str) -> dict[str, Any]:
        with self._write() as db:
            old = self._idempotent_task(db, event_id, "progress")
            if old is not None:
                return {"ok": True, "idempotent": True, "task": old}
            row = self._task_row(db, task_id)
            self._assert_mutable(row)
            self._assert_worker(row, worker)
            if row["status"] not in {"claimed", "running"}:
                raise InvalidTransition(f"progress requires claimed/running, got {row['status']}")
            before = row["status"]
            ts = _now()
            db.execute(
                "UPDATE tasks SET status='running',progress=?,updated_at=? WHERE id=?",
                (progress, ts, int(task_id)),
            )
            self._insert_event(
                db,
                event_id=event_id,
                task_id=task_id,
                actor=worker,
                action="progress",
                from_status=before,
                to_status="running",
                detail={"progress": progress},
            )
            return {"ok": True, "idempotent": False, "task": self._task_dict(db, task_id)}

    def complete_task(self, *, task_id: int, event_id: str, worker: str, result: str) -> dict[str, Any]:
        with self._write() as db:
            old = self._idempotent_task(db, event_id, "complete")
            if old is not None:
                return {"ok": True, "idempotent": True, "task": old}
            row = self._task_row(db, task_id)
            self._assert_mutable(row)
            self._assert_worker(row, worker)
            if row["status"] not in {"claimed", "running"}:
                raise InvalidTransition(f"complete requires claimed/running, got {row['status']}")
            ts = _now()
            db.execute(
                "UPDATE tasks SET status='done',result=?,progress='',updated_at=?,completed_at=? WHERE id=?",
                (result, ts, ts, int(task_id)),
            )
            self._insert_event(
                db,
                event_id=event_id,
                task_id=task_id,
                actor=worker,
                action="complete",
                from_status=row["status"],
                to_status="done",
                detail={},
            )
            return {"ok": True, "idempotent": False, "task": self._task_dict(db, task_id)}

    def fail_task(
        self,
        *,
        task_id: int,
        event_id: str,
        worker: str,
        reason: str,
        next_step: str = "",
    ) -> dict[str, Any]:
        with self._write() as db:
            old = self._idempotent_task(db, event_id, "fail")
            if old is not None:
                return {"ok": True, "idempotent": True, "task": old}
            row = self._task_row(db, task_id)
            self._assert_mutable(row)
            self._assert_worker(row, worker)
            if row["status"] not in {"claimed", "running"}:
                raise InvalidTransition(f"fail requires claimed/running, got {row['status']}")
            ts = _now()
            db.execute(
                "UPDATE tasks SET status='failed',last_error=?,progress='',updated_at=?,completed_at=? WHERE id=?",
                (reason, ts, ts, int(task_id)),
            )
            self._insert_event(
                db,
                event_id=event_id,
                task_id=task_id,
                actor=worker,
                action="fail",
                from_status=row["status"],
                to_status="failed",
                detail={"reason": reason, "next_step": next_step},
            )
            return {"ok": True, "idempotent": False, "task": self._task_dict(db, task_id)}

    def cancel_task(self, *, task_id: int, event_id: str, actor: str, reason: str = "") -> dict[str, Any]:
        with self._write() as db:
            old = self._idempotent_task(db, event_id, "cancel")
            if old is not None:
                return {"ok": True, "idempotent": True, "task": old}
            row = self._task_row(db, task_id)
            if row["status"] != "pending":
                raise InvalidTransition(f"only pending tasks can be cancelled, got {row['status']}")
            ts = _now()
            db.execute(
                "UPDATE tasks SET status='cancelled',last_error=?,updated_at=?,completed_at=? WHERE id=?",
                (reason, ts, ts, int(task_id)),
            )
            self._insert_event(
                db,
                event_id=event_id,
                task_id=task_id,
                actor=actor,
                action="cancel",
                from_status="pending",
                to_status="cancelled",
                detail={"reason": reason},
            )
            return {"ok": True, "idempotent": False, "task": self._task_dict(db, task_id)}

    def append_message(
        self,
        *,
        task_id: int,
        event_id: str,
        author: str,
        kind: str,
        content: str,
    ) -> dict[str, Any]:
        if kind not in MESSAGE_KINDS:
            raise ValueError(f"kind must be one of {sorted(MESSAGE_KINDS)}")
        with self._write() as db:
            old_event = self._event(db, event_id)
            if old_event:
                if old_event["action"] != f"message:{kind}" or int(old_event["task_id"]) != int(task_id):
                    raise IdempotencyConflict(f"event_id {event_id!r} already used")
                msg = db.execute("SELECT * FROM task_messages WHERE event_id=?", (event_id,)).fetchone()
                if not msg:
                    raise IdempotencyConflict("event exists without matching message")
                return {"ok": True, "idempotent": True, "message": self._message_dict(msg)}
            row = self._task_row(db, task_id)
            self._assert_mutable(row)
            ts = _now()
            cur = db.execute(
                "INSERT INTO task_messages(event_id,task_id,author,kind,content,created_at) VALUES(?,?,?,?,?,?)",
                (event_id, int(task_id), author, kind, content, ts),
            )
            self._insert_event(
                db,
                event_id=event_id,
                task_id=task_id,
                actor=author,
                action=f"message:{kind}",
                from_status=row["status"],
                to_status=row["status"],
                detail={"message_id": int(cur.lastrowid), "kind": kind},
            )
            msg = db.execute("SELECT * FROM task_messages WHERE id=?", (int(cur.lastrowid),)).fetchone()
            return {"ok": True, "idempotent": False, "message": self._message_dict(msg)}

    def get_task(self, task_id: int) -> dict[str, Any]:
        db = self._connect()
        try:
            return self._task_dict(db, int(task_id))
        finally:
            db.close()

    def list_tasks(
        self,
        *,
        assignee: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if status and status not in STATUSES:
            raise ValueError(f"unknown status {status!r}")
        clauses: list[str] = []
        args: list[Any] = []
        if assignee:
            clauses.append("assignee=?")
            args.append(assignee)
        if status:
            clauses.append("status=?")
            args.append(status)
        sql = "SELECT id FROM tasks"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at,id LIMIT ?"
        args.append(max(1, min(int(limit), 1000)))
        db = self._connect()
        try:
            ids = [int(r["id"]) for r in db.execute(sql, args).fetchall()]
            return [self._task_dict(db, task_id) for task_id in ids]
        finally:
            db.close()

    def read_messages(self, task_id: int, *, after_id: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        db = self._connect()
        try:
            self._task_row(db, int(task_id))
            rows = db.execute(
                "SELECT * FROM task_messages WHERE task_id=? AND id>? ORDER BY id LIMIT ?",
                (int(task_id), max(0, int(after_id)), max(1, min(int(limit), 1000))),
            ).fetchall()
            return [self._message_dict(r) for r in rows]
        finally:
            db.close()

    def read_result(self, task_id: int) -> dict[str, Any]:
        task = self.get_task(task_id)
        return {
            "id": task["id"],
            "title": task["title"],
            "status": task["status"],
            "result": task["result"],
            "last_error": task["last_error"],
            "completed_at": task["completed_at"],
        }

    def task_count(self) -> int:
        db = self._connect()
        try:
            return int(db.execute("SELECT count(*) FROM tasks").fetchone()[0])
        finally:
            db.close()

    def table_names(self) -> Iterable[str]:
        db = self._connect()
        try:
            return [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        finally:
            db.close()
