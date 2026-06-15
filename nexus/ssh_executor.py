"""SSH command execution backend."""

from __future__ import annotations

from dataclasses import dataclass

import paramiko

from .config import SSHSettings


@dataclass(frozen=True)
class ExecutionResult:
    """Result returned by an execution backend."""

    success: bool
    output: str
    stderr: str = ""
    exit_status: int | None = None


def execute_ssh(command: str, settings: SSHSettings) -> ExecutionResult:
    """Execute a command on a remote host through SSH."""

    ssh_client = paramiko.SSHClient()
    ssh_client.load_system_host_keys()
    ssh_client.set_missing_host_key_policy(paramiko.RejectPolicy())

    connect_kwargs = {
        "hostname": settings.host,
        "username": settings.user,
        "port": settings.port,
        "timeout": settings.timeout,
    }
    if settings.key_path:
        connect_kwargs["key_filename"] = settings.key_path
    if settings.password:
        connect_kwargs["password"] = settings.password

    try:
        ssh_client.connect(**connect_kwargs)
        _stdin, stdout, stderr = ssh_client.exec_command(command, timeout=settings.timeout)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode("utf-8", errors="replace")
        error = stderr.read().decode("utf-8", errors="replace")
        return ExecutionResult(
            success=exit_status == 0,
            output=output,
            stderr=error,
            exit_status=exit_status,
        )
    finally:
        ssh_client.close()
