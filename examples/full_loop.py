from __future__ import annotations

import tempfile
from pathlib import Path

from shared_task_box import ProducerClient, TaskBridge, WorkerClient

with tempfile.TemporaryDirectory() as td:
    bridge = TaskBridge(str(Path(td) / "demo.db"))
    producer = ProducerClient(bridge, sender="chat-host")
    worker = WorkerClient(bridge, worker="coding-worker-1")

    task = producer.create(
        event_id="demo-create",
        title="Add parser regression",
        content="Add a regression test for quoted newlines.",
        context={"repo_ref": "demo-checkout"},
    )["task"]

    worker.claim(event_id="demo-claim", task_id=task["id"])
    q = worker.question(
        task["id"], event_id="demo-question", content="Should the output preserve CRLF?"
    )["message"]
    producer.answer(
        task["id"], event_id="demo-answer", content="Normalize to LF in parsed values."
    )
    worker.progress(
        task["id"], event_id="demo-progress", text="Regression test and parser fix complete."
    )
    worker.complete(
        task["id"], event_id="demo-complete", result="Implemented parser fix; regression passes."
    )

    print("question_message_id=", q["id"])
    print(producer.result(task["id"]))
