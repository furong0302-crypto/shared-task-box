from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Protocol


class NotificationSink(Protocol):
    def __call__(self, payload: dict[str, Any]) -> None: ...


def minimal_notification(task: dict[str, Any], *, kind: str = "task", message_id: int | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "task_id": int(task["id"]),
        "title": str(task["title"]),
        "status": str(task["status"]),
        "kind": str(kind),
    }
    if message_id is not None:
        payload["message_id"] = int(message_id)
    return payload


class JsonlNotifier:
    """Example adapter: append minimal notification metadata to a JSONL file."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, payload: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


class CallbackNotifier:
    def __init__(self, callback: Callable[[dict[str, Any]], None]):
        self.callback = callback

    def __call__(self, payload: dict[str, Any]) -> None:
        self.callback(payload)
