#!/usr/bin/env python3
"""Nexus-CLI command-line interface."""

from __future__ import annotations

import argparse
import sys

from colorama import Fore, Style, init

from nexus.config import ConfigError, load_environment
from nexus.runner import run_user_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Nexus-CLI natural-language sysadmin command runner")
    parser.add_argument("--command", "-c", help="Natural-language command to execute, e.g. 'cek ram'")
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Confirm execution for commands marked as dangerous.",
    )
    return parser


def execute_and_print(command: str, confirmed: bool = False) -> int:
    result = run_user_command(command, confirmed=confirmed, actor="cli")
    color = Fore.GREEN if result.get("success") else Fore.RED
    print(color + result.get("output", "") + Style.RESET_ALL)

    if result.get("requires_confirmation"):
        print(Fore.YELLOW + "Re-run with --yes to confirm this command." + Style.RESET_ALL)

    return 0 if result.get("success") else 1


def interactive_loop() -> int:
    print("Nexus-CLI interactive mode. Type 'exit' or 'quit' to leave.")
    exit_code = 0
    while True:
        try:
            command = input("nexus> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return exit_code

        if command.lower() in {"exit", "quit"}:
            return exit_code
        if not command:
            continue
        exit_code = execute_and_print(command)


def main() -> int:
    init(autoreset=True)
    load_environment()
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command:
            return execute_and_print(args.command, confirmed=args.yes)
        return interactive_loop()
    except ConfigError as exc:
        print(Fore.RED + f"Configuration error: {exc}" + Style.RESET_ALL, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
