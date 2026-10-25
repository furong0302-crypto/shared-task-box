class TaskBridgeError(Exception):
    """Base error for task bridge operations."""


class NotFound(TaskBridgeError):
    pass


class InvalidTransition(TaskBridgeError):
    pass


class IdempotencyConflict(TaskBridgeError):
    pass
