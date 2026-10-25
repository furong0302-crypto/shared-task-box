"""Optional MCP adapter example.

Install the Python `mcp` package separately to run this example. The core
`shared_task_box` package has no MCP dependency.
"""
from __future__ import annotations

import os

from shared_task_box import ProducerClient, TaskBridge, WorkerClient

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - optional example
    raise SystemExit("Install the optional `mcp` package to run this example") from exc

DB = os.environ.get("SHARED_TASK_BOX_DB", "shared-task-box.db")
bridge = TaskBridge(DB)
producer = ProducerClient(bridge, sender="chat-host")
worker = WorkerClient(bridge, worker="coding-worker")
mcp = FastMCP("shared-task-box")


@mcp.tool()
def submit_task(event_id: str, title: str, content: str) -> dict:
    return producer.create(event_id=event_id, title=title, content=content)


@mcp.tool()
def claim_task(event_id: str, task_id: int = 0) -> dict:
    return worker.claim(event_id=event_id, task_id=task_id)


@mcp.tool()
def task_messages(task_id: int, after_id: int = 0) -> list[dict]:
    return worker.messages(task_id, after_id=after_id)


@mcp.tool()
def task_progress(task_id: int, event_id: str, text: str) -> dict:
    return worker.progress(task_id, event_id=event_id, text=text)


@mcp.tool()
def complete_task(task_id: int, event_id: str, result: str) -> dict:
    return worker.complete(task_id, event_id=event_id, result=result)


if __name__ == "__main__":  # pragma: no cover - optional example
    mcp.run()
