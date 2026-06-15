"""Safety policy checks for command execution."""

from __future__ import annotations

from dataclasses import dataclass

from .parser import ParsedCommand


@dataclass(frozen=True)
class SafetyDecision:
    """Result of evaluating a command against safety policy."""

    allowed: bool
    reason: str = ""
    requires_confirmation: bool = False


def evaluate(parsed_command: ParsedCommand, confirmed: bool = False) -> SafetyDecision:
    """Apply conservative safety checks before command execution."""

    if parsed_command.risk_level == "blocked":
        return SafetyDecision(False, "Command is blocked by policy.", False)

    if parsed_command.requires_confirmation and not confirmed:
        return SafetyDecision(
            False,
            "Command requires explicit confirmation before execution.",
            True,
        )

    return SafetyDecision(True)
