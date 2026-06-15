"""Rule-based natural language command parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ParsedCommand:
    """A command resolved from user input."""

    input_text: str
    command: str
    name: str = ""
    description: str = ""
    category: str = ""
    risk_level: str = "low"
    requires_confirmation: bool = False
    matched_by: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def parse_command(user_input: str, commands: dict[str, list[dict[str, Any]]]) -> ParsedCommand | None:
    """Resolve user input to a configured shell command."""

    normalized = user_input.lower().strip()
    if not normalized:
        return None

    for category, entries in commands.items():
        for entry in entries:
            keyword_match = _match_keyword(normalized, entry.get("keywords", []))
            if keyword_match:
                return _build_parsed_command(user_input, entry, category, "keyword")

            pattern = entry.get("pattern")
            if pattern:
                match = re.search(pattern, normalized)
                if match:
                    command = entry["command"].format(*match.groups())
                    return _build_parsed_command(user_input, entry, category, "pattern", command)

    return None


def _match_keyword(normalized_input: str, keywords: list[str]) -> bool:
    for keyword in keywords:
        if keyword.lower().strip() in normalized_input:
            return True
    return False


def _build_parsed_command(
    user_input: str,
    entry: dict[str, Any],
    category: str,
    matched_by: str,
    rendered_command: str | None = None,
) -> ParsedCommand:
    risk_level = str(entry.get("risk_level", "high" if entry.get("is_dangerous") else "low")).lower()
    requires_confirmation = bool(
        entry.get("requires_confirmation", entry.get("is_dangerous", risk_level in {"high", "critical"}))
    )

    return ParsedCommand(
        input_text=user_input,
        command=rendered_command or entry["command"],
        name=entry.get("name", ""),
        description=entry.get("description", ""),
        category=category,
        risk_level=risk_level,
        requires_confirmation=requires_confirmation,
        matched_by=matched_by,
        metadata={key: value for key, value in entry.items() if key not in {"command", "keywords", "pattern"}},
    )
