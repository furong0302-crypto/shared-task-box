from __future__ import annotations

import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from shared_task_box import (
    CallbackNotifier,
    IdempotencyConflict,
    InvalidTransition,
    ProducerClient,
    TaskBridge,
    TaskStore,
    WorkerClient,
)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "bridge.db")
        self.bridge = TaskBridge(self.db)
        self.producer = ProducerClient(self.bridge, sender="host")
        self.worker = WorkerClient(self.bridge, worker="worker-a")

    def tearDown(self):
        self.tmp.cleanup()

    def create(self, event_id="create-1"):
        return self.producer.create(
            event_id=event_id,
            title="Implement parser",
            content="Add parser and tests",
            context={"repo": "example", "api_token": "top-secret-value"},
        )["task"]

    def test_duplicate_event_id_is_idempotent(self):
        first = self.producer.create(
            event_id="same-create",
            title="One",
            content="Body",
            context={},
        )
        second = self.producer.create(
            event_id="same-create",
            title="Ignored on replay",
            content="Different body",
            context={},
        )
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(first["task"]["id"], second["task"]["id"])
        self.assertEqual(1, self.bridge.store.task_count())
        with self.assertRaises(IdempotencyConflict):
            self.worker.claim(event_id="same-create", task_id=first["task"]["id"])

    def test_concurrent_claim_is_atomic(self):
        task = self.create("create-concurrent")
        barrier = threading.Barrier(2)

        def attempt(worker_name, event_id):
            local = WorkerClient(TaskBridge(self.db), worker=worker_name)
            barrier.wait(timeout=3)
            return local.claim(event_id=event_id, task_id=task["id"])

        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(attempt, "worker-a", "claim-a")
            b = pool.submit(attempt, "worker-b", "claim-b")
            results = [a.result(timeout=10), b.result(timeout=10)]
        winners = [r for r in results if r["claimed"]]
        self.assertEqual(1, len(winners))
        final = self.bridge.store.get_task(task["id"])
        self.assertEqual("claimed", final["status"])
        self.assertIn(final["claimed_by"], {"worker-a", "worker-b"})

    def test_illegal_state_transitions_and_cancel(self):
        task = self.create("create-state")
        with self.assertRaises(InvalidTransition):
            self.worker.complete(task["id"], event_id="done-too-soon", result="x")
        cancelled = self.producer.cancel(task["id"], event_id="cancel-1", reason="not needed")
        self.assertEqual("cancelled", cancelled["task"]["status"])
        self.assertFalse(self.worker.claim(event_id="claim-after-cancel", task_id=task["id"])["claimed"])

    def test_terminal_task_is_read_only(self):
        task = self.create("create-terminal")
        self.worker.claim(event_id="claim-terminal", task_id=task["id"])
        self.worker.progress(task["id"], event_id="progress-terminal", text="working")
        self.worker.complete(task["id"], event_id="complete-terminal", result="finished")
        with self.assertRaises(InvalidTransition):
            self.worker.progress(task["id"], event_id="late-progress", text="late")
        with self.assertRaises(InvalidTransition):
            self.worker.note(task["id"], event_id="late-note", content="late")
        with self.assertRaises(InvalidTransition):
            self.worker.fail(task["id"], event_id="late-fail", reason="late")

    def test_message_cursor(self):
        task = self.create("create-msg")
        self.worker.claim(event_id="claim-msg", task_id=task["id"])
        q1 = self.worker.question(task["id"], event_id="q1", content="Question one")["message"]
        a1 = self.producer.answer(task["id"], event_id="a1", content="Answer one")["message"]
        q2 = self.worker.question(task["id"], event_id="q2", content="Question two")["message"]
        newer = self.worker.messages(task["id"], after_id=q1["id"])
        self.assertEqual([a1["id"], q2["id"]], [m["id"] for m in newer])

    def test_redaction_covers_structured_and_text_secrets(self):
        task = self.producer.create(
            event_id="create-secret",
            title="Secret check",
            content="Authorization: Bearer " + ("a" * 20) + " token=" + ("b" * 12),
            context={"password": "hunt" + "er2", "nested": {"api_key": "xyz" + "123456789"}},
        )["task"]
        encoded = json.dumps(task, ensure_ascii=False)
        self.assertNotIn("hunter2", encoded)
        self.assertNotIn("xyz123456789", encoded)
        self.assertNotIn("a" * 20, encoded)
        self.assertIn("[REDACTED]", encoded)

    def test_notifications_are_minimal_metadata(self):
        seen = []
        bridge = TaskBridge(self.db, notifier=CallbackNotifier(seen.append))
        producer = ProducerClient(bridge, sender="host")
        worker = WorkerClient(bridge, worker="worker-a")
        task = producer.create(
            event_id="notify-create", title="Notify", content="private body", context={"secret": "private"}
        )["task"]
        worker.claim(event_id="notify-claim", task_id=task["id"])
        worker.question(task["id"], event_id="notify-question", content="private question")
        self.assertGreaterEqual(len(seen), 3)
        for payload in seen:
            self.assertTrue(set(payload).issubset({"task_id", "title", "status", "kind", "message_id"}))
            self.assertNotIn("content", payload)
            self.assertNotIn("context", payload)
            self.assertNotIn("result", payload)
        self.assertEqual("question", seen[-1]["kind"])
        self.assertIn("message_id", seen[-1])

    def test_end_to_end_loop(self):
        task = self.create("e2e-create")
        claimed = self.worker.claim(event_id="e2e-claim", task_id=task["id"])["task"]
        self.assertEqual("claimed", claimed["status"])
        question = self.worker.question(
            task["id"], event_id="e2e-question", content="Use JSON output?"
        )["message"]
        answer = self.producer.answer(
            task["id"], event_id="e2e-answer", content="Yes, JSON."
        )["message"]
        self.assertGreater(answer["id"], question["id"])
        running = self.worker.progress(
            task["id"], event_id="e2e-progress", text="Tests passing"
        )["task"]
        self.assertEqual("running", running["status"])
        done = self.worker.complete(
            task["id"], event_id="e2e-complete", result="Implemented with tests"
        )["task"]
        self.assertEqual("done", done["status"])
        result = self.producer.result(task["id"])
        self.assertEqual("Implemented with tests", result["result"])
        self.assertEqual("done", result["status"])

    def test_standalone_database_contains_only_bridge_tables(self):
        store = TaskStore(self.db)
        names = set(store.table_names())
        self.assertIn("tasks", names)
        self.assertIn("task_events", names)
        self.assertIn("task_messages", names)
        self.assertFalse(any(name.startswith("chat") or "conversation" in name for name in names))


if __name__ == "__main__":
    unittest.main()
