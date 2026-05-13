from __future__ import annotations

import subprocess
from typing import Any

import pytest

from crypto_helper.agent_runtime.openclaw_wakeup import (
    DEFAULT_WAKE_MESSAGE,
    wake_queue_dispatcher_agent,
)


def test_wake_queue_dispatcher_uses_openclaw_agent_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        assert kwargs["capture_output"] is True
        assert kwargs["check"] is False
        assert kwargs["text"] is True
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout='{"ok":true,"result":{"processed_count":0}}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = wake_queue_dispatcher_agent()

    assert result["ok"] is True
    assert result["target_agent"] == "queue-dispatcher-agent"
    assert result["message"] == DEFAULT_WAKE_MESSAGE
    assert result["openclaw_result"] == {"ok": True, "result": {"processed_count": 0}}
    assert calls == [
        [
            "openclaw",
            "agent",
            "--agent",
            "queue-dispatcher-agent",
            "--message",
            DEFAULT_WAKE_MESSAGE,
            "--json",
        ]
    ]
    assert "--deliver" not in calls[0]


def test_wake_queue_dispatcher_accepts_custom_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_args: list[str] = []

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        del kwargs
        captured_args.extend(args)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout='{"ok":true}', stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = wake_queue_dispatcher_agent("dispatch once")

    assert result["ok"] is True
    assert "--message" in captured_args
    assert captured_args[captured_args.index("--message") + 1] == "dispatch once"


def test_wake_queue_dispatcher_returns_warning_on_openclaw_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        del kwargs
        return subprocess.CompletedProcess(
            args=args,
            returncode=2,
            stdout='{"ok":false}',
            stderr="agent failed",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = wake_queue_dispatcher_agent()

    assert result["ok"] is False
    assert result["code"] == "OPENCLAW_WAKE_FAILED"
    assert result["warning"]
    assert result["metadata"]["exit_code"] == 2
    assert result["metadata"]["openclaw_result"] == {"ok": False}


def test_wake_queue_dispatcher_returns_warning_on_exec_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        raise OSError("openclaw missing")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = wake_queue_dispatcher_agent()

    assert result["ok"] is False
    assert result["code"] == "OPENCLAW_WAKE_EXEC_ERROR"
    assert "openclaw missing" in result["warning"]


def test_wake_queue_dispatcher_returns_warning_on_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        del kwargs
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="not-json", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = wake_queue_dispatcher_agent()

    assert result["ok"] is False
    assert result["code"] == "OPENCLAW_WAKE_JSON_PARSE_ERROR"
    assert result["metadata"]["stdout"] == "not-json"
