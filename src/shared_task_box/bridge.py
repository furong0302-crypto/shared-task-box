from __future__ import annotations

from typing import Any

from .notify import NotificationSink, minimal_notification
from .store import TaskStore


class TaskBridge:
    """High-level API with optional host notification callbacks.

    The callback receives minimal metadata only. Waking a host session or
    starting a worker is deliberately outside this core package.
    """

    def __init__(self, db_path: str, notifier: NotificationSink | None = None):
        self.store = TaskStore(db_path)
        self.notifier = notifier

    def _notify_task(self, result: dict[str, Any], *, kind: str = "task") -> None:
        if not self.notifier or result.get("idempotent"):
            return
        task = result.get("task")
        if task:
            self.notifier(minimal_notification(task, kind=kind))

    def _notify_message(self, task_id: int, result: dict[str, Any]) -> None:
        if not self.notifier or result.get("idempotent"):
            return
        msg = result.get("message")
        if not msg:
            return
        task = self.store.get_task(task_id)
        self.notifier(minimal_notification(task, kind=msg["kind"], message_id=msg["id"]))

    def create_task(self, **kwargs):
        out = self.store.create_task(**kwargs)
        self._notify_task(out, kind="task")
        return out

    def claim_task(self, **kwargs):
        out = self.store.claim_task(**kwargs)
        self._notify_task(out, kind="task")
        return out

    def update_progress(self, **kwargs):
        out = self.store.update_progress(**kwargs)
        self._notify_task(out, kind="progress")
        return out

    def complete_task(self, **kwargs):
        out = self.store.complete_task(**kwargs)
        self._notify_task(out, kind="task")
        return out

    def fail_task(self, **kwargs):
        out = self.store.fail_task(**kwargs)
        self._notify_task(out, kind="task")
        return out

    def cancel_task(self, **kwargs):
        out = self.store.cancel_task(**kwargs)
        self._notify_task(out, kind="task")
        return out

    def append_message(self, **kwargs):
        task_id = int(kwargs["task_id"])
        out = self.store.append_message(**kwargs)
        self._notify_message(task_id, out)
        return out
