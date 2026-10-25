from __future__ import annotations

from shared_task_box import CallbackNotifier, ProducerClient, TaskBridge


def host_adapter(metadata: dict) -> None:
    # Replace this with the host's own push/session API when one exists.
    # The payload intentionally has no task body, result, context, or message text.
    print("host notification:", metadata)


bridge = TaskBridge("example.db", notifier=CallbackNotifier(host_adapter))
producer = ProducerClient(bridge, sender="chat-host")
producer.create(
    event_id="notify-create-001",
    title="Small documentation task",
    content="Update the installation note.",
)
