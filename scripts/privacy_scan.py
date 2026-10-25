from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
TEXT_EXT = {".py", ".md", ".toml", ".txt", ".sql", ".json", ".yaml", ".yml", ".gitignore"}
PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "credential-assignment": re.compile(r"(?i)(?:password|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    "bearer-token": re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    "openai-like-token": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    "unix-user-path": re.compile(r"/(?:home|Users)/[^/\s]+/"),
    "windows-user-path": re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\\\s]+\\\\"),
}

hits = []
for path in ROOT.rglob("*"):
    if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
        continue
    if path.suffix not in TEXT_EXT and path.name != ".gitignore":
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for label, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            hits.append((str(path.relative_to(ROOT)), line, label))

if hits:
    for item in hits:
        print(f"{item[0]}:{item[1]}: {item[2]}")
    raise SystemExit(1)
print("privacy scan: clean")
