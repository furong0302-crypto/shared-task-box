from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .bridge import TaskBridge
from .errors import TaskBridgeError
from .producer import ProducerClient
from .worker import WorkerClient


def _json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _context(raw: str) -> dict[str, Any]:
    value = json.loads(raw or "{}")
    if not isinstance(value, dict):
        raise ValueError("--context-json must decode to an object")
    return value


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="shared-task-box", description="共享任务箱：chat-to-coding-worker task bridge")
    p.add_argument("--db", default="shared-task-box.db", help="SQLite database path")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="producer: submit one explicit task")
    c.add_argument("--event-id", required=True)
    c.add_argument("--sender", default="chat-host")
    c.add_argument("--assignee", default="coding-worker")
    c.add_argument("--title", required=True)
    c.add_argument("--content", required=True)
    c.add_argument("--context-json", default="{}")

    l = sub.add_parser("list", help="inspect task state")
    l.add_argument("--assignee", default="")
    l.add_argument("--status", default="")
    l.add_argument("--limit", type=int, default=100)

    g = sub.add_parser("get")
    g.add_argument("task_id", type=int)

    cl = sub.add_parser("claim", help="worker: atomically claim a pending task")
    cl.add_argument("--event-id", required=True)
    cl.add_argument("--worker", required=True)
    cl.add_argument("--assignee", default="coding-worker")
    cl.add_argument("--task-id", type=int, default=0)

    pr = sub.add_parser("progress", help="worker: set running + progress")
    pr.add_argument("task_id", type=int)
    pr.add_argument("--event-id", required=True)
    pr.add_argument("--worker", required=True)
    pr.add_argument("--text", required=True)

    q = sub.add_parser("question", help="worker: append a question")
    q.add_argument("task_id", type=int)
    q.add_argument("--event-id", required=True)
    q.add_argument("--worker", required=True)
    q.add_argument("--content", required=True)

    a = sub.add_parser("answer", help="producer: append an answer")
    a.add_argument("task_id", type=int)
    a.add_argument("--event-id", required=True)
    a.add_argument("--sender", default="chat-host")
    a.add_argument("--content", required=True)

    n = sub.add_parser("note", help="append a note from either side")
    n.add_argument("task_id", type=int)
    n.add_argument("--event-id", required=True)
    n.add_argument("--author", required=True)
    n.add_argument("--content", required=True)

    m = sub.add_parser("messages", help="read task-thread messages with an after_id cursor")
    m.add_argument("task_id", type=int)
    m.add_argument("--after-id", type=int, default=0)
    m.add_argument("--limit", type=int, default=100)

    co = sub.add_parser("complete", help="worker: complete a claimed/running task")
    co.add_argument("task_id", type=int)
    co.add_argument("--event-id", required=True)
    co.add_argument("--worker", required=True)
    co.add_argument("--result", required=True)

    f = sub.add_parser("fail", help="worker: fail a claimed/running task")
    f.add_argument("task_id", type=int)
    f.add_argument("--event-id", required=True)
    f.add_argument("--worker", required=True)
    f.add_argument("--reason", required=True)
    f.add_argument("--next-step", default="")

    x = sub.add_parser("cancel", help="producer: cancel only while pending")
    x.add_argument("task_id", type=int)
    x.add_argument("--event-id", required=True)
    x.add_argument("--sender", default="chat-host")
    x.add_argument("--reason", default="")

    rr = sub.add_parser("result", help="read terminal/current result summary")
    rr.add_argument("task_id", type=int)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    bridge = TaskBridge(args.db)
    try:
        if args.cmd == "create":
            out = ProducerClient(bridge, sender=args.sender).create(
                event_id=args.event_id,
                title=args.title,
                content=args.content,
                assignee=args.assignee,
                context=_context(args.context_json),
            )
        elif args.cmd == "list":
            out = bridge.store.list_tasks(
                assignee=args.assignee or None, status=args.status or None, limit=args.limit
            )
        elif args.cmd == "get":
            out = bridge.store.get_task(args.task_id)
        elif args.cmd == "claim":
            out = WorkerClient(bridge, worker=args.worker, assignee=args.assignee).claim(
                event_id=args.event_id, task_id=args.task_id
            )
        elif args.cmd == "progress":
            out = WorkerClient(bridge, worker=args.worker).progress(
                args.task_id, event_id=args.event_id, text=args.text
            )
        elif args.cmd == "question":
            out = WorkerClient(bridge, worker=args.worker).question(
                args.task_id, event_id=args.event_id, content=args.content
            )
        elif args.cmd == "answer":
            out = ProducerClient(bridge, sender=args.sender).answer(
                args.task_id, event_id=args.event_id, content=args.content
            )
        elif args.cmd == "note":
            out = bridge.append_message(
                task_id=args.task_id,
                event_id=args.event_id,
                author=args.author,
                kind="note",
                content=args.content,
            )
        elif args.cmd == "messages":
            out = bridge.store.read_messages(args.task_id, after_id=args.after_id, limit=args.limit)
        elif args.cmd == "complete":
            out = WorkerClient(bridge, worker=args.worker).complete(
                args.task_id, event_id=args.event_id, result=args.result
            )
        elif args.cmd == "fail":
            out = WorkerClient(bridge, worker=args.worker).fail(
                args.task_id,
                event_id=args.event_id,
                reason=args.reason,
                next_step=args.next_step,
            )
        elif args.cmd == "cancel":
            out = ProducerClient(bridge, sender=args.sender).cancel(
                args.task_id, event_id=args.event_id, reason=args.reason
            )
        elif args.cmd == "result":
            out = bridge.store.read_result(args.task_id)
        else:
            raise AssertionError(args.cmd)
        _json(out)
        return 0
    except (TaskBridgeError, ValueError, json.JSONDecodeError) as exc:
        _json({"ok": False, "error": str(exc), "type": type(exc).__name__})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
