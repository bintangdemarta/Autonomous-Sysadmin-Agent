"""JSONL audit logging."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import get_audit_log_path


def write_audit_event(event: dict[str, Any], path: Path | None = None) -> None:
    """Append a structured audit event to the JSONL audit log."""

    audit_path = path or get_audit_log_path()
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), **event}
    with audit_path.open("a", encoding="utf-8") as file_handle:
        file_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
