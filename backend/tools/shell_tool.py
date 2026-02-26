from __future__ import annotations
import subprocess
from dataclasses import dataclass
from typing import List, Optional

# Very simple allowlist for MVP (safe, read-only)
ALLOWED_PREFIXES = [
    "ls",
    "pwd",
    "whoami",
    "python --version",
    "python3 --version",
    "pip --version",
    "pip3 --version",
    "git status",
    "git log",
    "cat ",
    "head ",
    "tail ",
    "echo ",
    "curl ",
]

DENY_CONTAINS = [
    "rm ",
    "sudo",
    "shutdown",
    "reboot",
    "mkfs",
    ":(){",        # fork bomb pattern
    "dd ",
    "chmod 777",
    "chown",
]

@dataclass
class ShellResult:
    ok: bool
    blocked: bool
    reason: Optional[str]
    stdout: str
    stderr: str
    returncode: int

def is_allowed(cmd: str) -> tuple[bool, Optional[str]]:
    c = cmd.strip()

    # deny list first
    low = c.lower()
    for bad in DENY_CONTAINS:
        if bad in low:
            return False, f"Blocked for safety: contains '{bad.strip()}'"

    # allowlist
    for p in ALLOWED_PREFIXES:
        if c == p or c.startswith(p):
            return True, None

    return False, "Blocked: command not in allowlist (MVP safety)."

def run_shell(cmd: str, timeout_sec: int = 10) -> ShellResult:
    allowed, reason = is_allowed(cmd)
    if not allowed:
        return ShellResult(
            ok=False,
            blocked=True,
            reason=reason,
            stdout="",
            stderr="",
            returncode=126,
        )

    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        return ShellResult(
            ok=(proc.returncode == 0),
            blocked=False,
            reason=None,
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            returncode=proc.returncode,
        )
    except subprocess.TimeoutExpired:
        return ShellResult(
            ok=False,
            blocked=False,
            reason="Command timed out",
            stdout="",
            stderr="timeout",
            returncode=124,
        )
