from __future__ import annotations

from typing import Any

from .bridge import TaskBridge


class WorkerClient:
    def __init__(self, bridge: TaskBridge, *, worker: str, assignee: str = "coding-worker"):
        self.bridge = bridge
        self.worker = worker
        self.assignee = assignee

    def claim(self, *, event_id: str, task_id: int = 0) -> dict[str, Any]:
        return self.bridge.claim_task(
            event_id=event_id,
            worker=self.worker,
            assignee=self.assignee,
            task_id=task_id,
        )

    def progress(self, task_id: int, *, event_id: str, text: str) -> dict[str, Any]:
        return self.bridge.update_progress(
            task_id=task_id, event_id=event_id, worker=self.worker, progress=text
        )

    def question(self, task_id: int, *, event_id: str, content: str) -> dict[str, Any]:
        return self.bridge.append_message(
            task_id=task_id,
            event_id=event_id,
            author=self.worker,
            kind="question",
            content=content,
        )

    def note(self, task_id: int, *, event_id: str, content: str) -> dict[str, Any]:
        return self.bridge.append_message(
            task_id=task_id,
            event_id=event_id,
            author=self.worker,
            kind="note",
            content=content,
        )

    def complete(self, task_id: int, *, event_id: str, result: str) -> dict[str, Any]:
        return self.bridge.complete_task(
            task_id=task_id, event_id=event_id, worker=self.worker, result=result
        )

    def fail(
        self,
        task_id: int,
        *,
        event_id: str,
        reason: str,
        next_step: str = "",
    ) -> dict[str, Any]:
        return self.bridge.fail_task(
            task_id=task_id,
            event_id=event_id,
            worker=self.worker,
            reason=reason,
            next_step=next_step,
        )

    def messages(self, task_id: int, *, after_id: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        return self.bridge.store.read_messages(task_id, after_id=after_id, limit=limit)

    def task(self, task_id: int) -> dict[str, Any]:
        return self.bridge.store.get_task(task_id)
