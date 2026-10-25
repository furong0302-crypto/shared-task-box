from __future__ import annotations

import re
from typing import Any

REDACTED = "[REDACTED]"
_SENSITIVE_KEY = re.compile(
    r"(?:password|passwd|pwd|secret|token|api[_-]?key|authorization|cookie|credential|private[_-]?key|access[_-]?key)",
    re.I,
)
_PATTERNS = [
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"(?i)((?:password|passwd|pwd|secret|token|api[_-]?key)\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
]


def redact_text(value: str) -> str:
    out = value
    for pattern in _PATTERNS:
        if pattern.pattern.lower().startswith("(?i)(bearer"):
            out = pattern.sub(lambda m: m.group(1) + REDACTED, out)
        elif pattern.groups:
            out = pattern.sub(lambda m: m.group(1) + REDACTED, out)
        else:
            out = pattern.sub(REDACTED, out)
    return out


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(k): (REDACTED if _SENSITIVE_KEY.search(str(k)) else redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, tuple):
        return tuple(redact(v) for v in value)
    if isinstance(value, str):
        return redact_text(value)
    return value
