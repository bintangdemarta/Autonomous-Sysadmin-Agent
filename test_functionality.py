#!/usr/bin/env python3
"""Smoke tests for Nexus-CLI command parsing."""

from nexus.config import load_commands
from nexus.parser import parse_command


def test_command_parsing():
    commands = load_commands()
    test_cases = [
        ("cek ram", "free -h", False),
        ("check memory", "free -h", False),
        ("hidupkan vm 102", "qm start 102", True),
        ("matikan vm 103", "qm shutdown 103", True),
        ("server uptime", "uptime", False),
    ]

    print("Command parsing test:")
    for user_input, expected_command, expected_confirmation in test_cases:
        parsed = parse_command(user_input, commands)
        actual_command = parsed.command if parsed else None
        actual_confirmation = parsed.requires_confirmation if parsed else False
        print(
            f"Input: {user_input} -> Command: {actual_command}, "
            f"Requires Confirmation: {actual_confirmation}"
        )
        assert actual_command == expected_command
        assert actual_confirmation is expected_confirmation


if __name__ == "__main__":
    test_command_parsing()
