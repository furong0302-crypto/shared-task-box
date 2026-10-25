from shared_task_box import TaskBridge, WorkerClient

bridge = TaskBridge("example.db")
worker = WorkerClient(bridge, worker="coding-worker-1")

claimed = worker.claim(event_id="example-claim-001")
if claimed["claimed"]:
    task = claimed["task"]
    worker.progress(
        task["id"],
        event_id="example-progress-001",
        text="Work started; initial checks passed.",
    )
    print(task)
else:
    print("no pending task")
