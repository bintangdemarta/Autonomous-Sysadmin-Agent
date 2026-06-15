"""High-level command parsing, safety, execution, and audit workflow."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .audit import write_audit_event
from .config import ConfigError, get_ssh_settings, load_commands
from .parser import parse_command
from .safety import evaluate
from .ssh_executor import ExecutionResult, execute_ssh


def run_user_command(user_input: str, confirmed: bool = False, actor: str = "anonymous") -> dict[str, Any]:
    """Parse and execute a natural-language command."""

    commands = load_commands()
    parsed = parse_command(user_input, commands)
    if not parsed:
        result = {
            "success": False,
            "output": f"Command '{user_input}' not recognized.",
            "parsed_command": None,
            "requires_confirmation": False,
        }
        write_audit_event({"actor": actor, "input": user_input, "success": False, "reason": "not_recognized"})
        return result

    decision = evaluate(parsed, confirmed=confirmed)
    if not decision.allowed:
        result = {
            "success": False,
            "output": decision.reason,
            "parsed_command": parsed.command,
            "requires_confirmation": decision.requires_confirmation,
            "risk_level": parsed.risk_level,
        }
        write_audit_event(
            {
                "actor": actor,
                "input": user_input,
                "parsed": asdict(parsed),
                "success": False,
                "reason": decision.reason,
            }
        )
        return result

    try:
        ssh_settings = get_ssh_settings()
        execution = execute_ssh(parsed.command, ssh_settings)
    except ConfigError as exc:
        execution = ExecutionResult(False, str(exc))
    except Exception as exc:  # noqa: BLE001 - user-facing execution failure should be reported.
        execution = ExecutionResult(False, f"Failed to execute command via SSH: {exc}")

    output_parts = [f"Command: {parsed.command}"]
    if parsed.description:
        output_parts.append(f"Description: {parsed.description}")
    if execution.stderr:
        output_parts.append(f"Error: {execution.stderr}")
    if execution.output:
        output_parts.append(execution.output)
    if not execution.output and not execution.stderr:
        output_parts.append("No output returned.")

    result = {
        "success": execution.success,
        "output": "\n".join(output_parts),
        "parsed_command": parsed.command,
        "requires_confirmation": False,
        "risk_level": parsed.risk_level,
        "exit_status": execution.exit_status,
    }
    write_audit_event(
        {
            "actor": actor,
            "input": user_input,
            "parsed": asdict(parsed),
            "success": execution.success,
            "exit_status": execution.exit_status,
        }
    )
    return result
