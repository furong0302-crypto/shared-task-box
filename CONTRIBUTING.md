# Contributing

Keep the core small and embeddable.

1. Do not add automatic host-chat/database discovery.
2. Do not make a model vendor, MCP, terminal manager, or worker launcher a core dependency.
3. Preserve unique event-id idempotency and atomic claims.
4. Add tests for every state transition or persistence change.
5. Keep notification payloads minimal by default.
6. Run `PYTHONPATH=src python -m unittest discover -s tests -v`.
7. Run `python scripts/privacy_scan.py .` before proposing public artifacts.

Changes that add leases, priorities, distributed coordination, or durable notification outboxes should be justified against the project's narrow embedded-bridge scope.
