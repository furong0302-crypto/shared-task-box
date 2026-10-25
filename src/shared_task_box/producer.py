from __future__ import annotations

from typing import Any

from .bridge import TaskBridge


class ProducerClient:
    """Chat/host-side API. It only sees task data explicitly submitted here."""

    def __init__(self, bridge: TaskBridge, *, sender: str = "chat-host"):
        self.bridge = bridge
        self.sender = sender

    def create(
        self,
        *,
        event_id: str,
        title: str,
        content: str,
        assignee: str = "coding-worker",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.bridge.create_task(
            event_id=event_id,
            sender=self.sender,
            assignee=assignee,
            title=title,
            content=content,
            context=context or {},
        )

    def answer(self, task_id: int, *, event_id: str, content: str) -> dict[str, Any]:
        return self.bridge.append_message(
            task_id=task_id,
            event_id=event_id,
            author=self.sender,
            kind="answer",
            content=content,
        )

    def note(self, task_id: int, *, event_id: str, content: str) -> dict[str, Any]:
        return self.bridge.append_message(
            task_id=task_id,
            event_id=event_id,
            author=self.sender,
            kind="note",
            content=content,
        )

    def cancel(self, task_id: int, *, event_id: str, reason: str = "") -> dict[str, Any]:
        return self.bridge.cancel_task(task_id=task_id, event_id=event_id, actor=self.sender, reason=reason)

    def task(self, task_id: int) -> dict[str, Any]:
        return self.bridge.store.get_task(task_id)

    def result(self, task_id: int) -> dict[str, Any]:
        return self.bridge.store.read_result(task_id)

    def messages(self, task_id: int, *, after_id: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        return self.bridge.store.read_messages(task_id, after_id=after_id, limit=limit)
