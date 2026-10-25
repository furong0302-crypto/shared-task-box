from __future__ import annotations

import time
import uuid

from shared_task_box import TaskBridge, WorkerClient

bridge = TaskBridge("example.db")
worker = WorkerClient(bridge, worker="worker-example")

while True:
    event_id = "claim-" + uuid.uuid4().hex
    claimed = worker.claim(event_id=event_id)
    if not claimed["claimed"]:
        time.sleep(2)
        continue

    task = claimed["task"]
    print("claimed", task["id"], task["title"])
    # Hand `task` to your existing coding worker here. This example deliberately
    # does not start a model, shell, or subprocess.
    break
