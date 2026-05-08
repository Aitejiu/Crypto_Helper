from __future__ import annotations

from pathlib import Path

from crypto_helper.core.paths import get_workflow_runs_dir
from crypto_helper.request_context import RequestContext
from crypto_helper.services.workflow_run_service import (
    append_safety_decision,
    append_tool_call,
    fail_workflow_run,
    finish_workflow_run,
    start_workflow_run,
)


def test_workflow_run_file_is_created(runtime_data_dir: Path) -> None:
    del runtime_data_dir
    record = start_workflow_run(
        request_context=_public_context(),
        user_message="show tracked KOLs",
        workflow_id="kol_list",
        execution_plan={"allowed_tools": ["crypto_helper_registry_list"]},
    )

    run_dir = get_workflow_runs_dir() / record.timestamp.strftime("%Y-%m-%d")
    assert (run_dir / f"{record.run_id}.json").exists()


def test_workflow_run_tool_call_can_append(runtime_data_dir: Path) -> None:
    del runtime_data_dir
    record = start_workflow_run(
        request_context=_public_context(),
        user_message="show tracked KOLs",
        workflow_id="kol_list",
        execution_plan={"allowed_tools": ["crypto_helper_registry_list"]},
    )

    updated = append_tool_call(
        record.run_id, {"tool": "crypto_helper_registry_list", "status": "ok"}
    )

    assert updated.tool_calls[0]["tool"] == "crypto_helper_registry_list"


def test_workflow_run_failed_state_records_error(runtime_data_dir: Path) -> None:
    del runtime_data_dir
    record = start_workflow_run(
        request_context=_private_context(),
        user_message="refresh profile",
        workflow_id="admin_refresh_profile",
        execution_plan={"allowed_tools": ["crypto_helper_get_profile"]},
    )
    append_safety_decision(record.run_id, {"action": "require_admin"})
    finish_workflow_run(record.run_id, final_status="guarded")
    failed = fail_workflow_run(record.run_id, error="admin context missing")

    assert failed.final_status == "failed"
    assert failed.error == "admin context missing"
    assert failed.user_message.startswith("[redacted private content]")


def _public_context() -> RequestContext:
    return RequestContext(
        channel="discord",
        guild_id="guild-1",
        chat_id="chat-1",
        user_id="user-1",
        message_id="msg-1",
        visibility="public",
    )


def _private_context() -> RequestContext:
    return RequestContext(
        channel="telegram",
        guild_id=None,
        chat_id="chat-2",
        user_id="admin-1",
        message_id="msg-2",
        visibility="admin",
        is_admin_context=True,
    )
