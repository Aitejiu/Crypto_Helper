from __future__ import annotations

import json
import subprocess
from typing import Any

DEFAULT_QUEUE_DISPATCHER_AGENT = "queue-dispatcher-agent"
DEFAULT_WAKE_MESSAGE = (
    "Process the crypto_helper async delegation queue. "
    "Call crypto_helper_queue_dispatch_until_empty with max_tasks=10 and max_seconds=120. "
    "Return DispatchLoopResult only."
)


def wake_queue_dispatcher_agent(message: str | None = None) -> dict[str, Any]:
    wake_message = message or DEFAULT_WAKE_MESSAGE
    args = [
        "openclaw",
        "agent",
        "--agent",
        DEFAULT_QUEUE_DISPATCHER_AGENT,
        "--message",
        wake_message,
        "--json",
    ]
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            check=False,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired as exc:
        return _warning(
            "OPENCLAW_WAKE_TIMEOUT",
            f"OpenClaw queue dispatcher wake timed out: {exc}",
            args=args,
        )
    except OSError as exc:
        return _warning(
            "OPENCLAW_WAKE_EXEC_ERROR",
            f"OpenClaw queue dispatcher wake failed: {exc}",
            args=args,
        )

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    parsed_stdout = _parse_json(stdout)
    if completed.returncode != 0:
        return _warning(
            "OPENCLAW_WAKE_FAILED",
            f"OpenClaw queue dispatcher wake exited with code {completed.returncode}.",
            args=args,
            exit_code=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            openclaw_result=parsed_stdout,
        )
    if parsed_stdout is None:
        return _warning(
            "OPENCLAW_WAKE_JSON_PARSE_ERROR",
            "OpenClaw queue dispatcher wake did not return valid JSON.",
            args=args,
            exit_code=completed.returncode,
            stdout=stdout,
            stderr=stderr,
        )
    return {
        "ok": True,
        "target_agent": DEFAULT_QUEUE_DISPATCHER_AGENT,
        "message": wake_message,
        "openclaw_result": parsed_stdout,
    }


def _parse_json(payload: str) -> Any | None:
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def _warning(
    code: str,
    warning: str,
    *,
    args: list[str],
    exit_code: int | None = None,
    stdout: str | None = None,
    stderr: str | None = None,
    openclaw_result: Any | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "warning": warning,
        "code": code,
        "target_agent": DEFAULT_QUEUE_DISPATCHER_AGENT,
        "metadata": {
            "args": args,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "openclaw_result": openclaw_result,
        },
    }
