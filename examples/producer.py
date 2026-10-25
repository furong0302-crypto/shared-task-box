from shared_task_box import ProducerClient, TaskBridge

bridge = TaskBridge("example.db")
producer = ProducerClient(bridge, sender="chat-host")

print(
    producer.create(
        event_id="example-create-001",
        title="Document retry behavior",
        content="Add a short retry-policy section and tests if behavior changes.",
        context={"repo_ref": "checkout-a"},
    )
)
