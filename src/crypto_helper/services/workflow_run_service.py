from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import Field

from crypto_helper.core.data_loader import load_json_path, save_json_path
from crypto_helper.core.paths import get_workflow_runs_dir
from crypto_helper.models.common import DomainModel, to_jsonable
from crypto_helper.request_context import RequestContext


class WorkflowRunRecord(DomainModel):
    run_id: str
    timestamp: datetime
    request_context: dict[str, Any]
    user_message: str
    workflow_id: str
    execution_plan: dict[str, Any]
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    safety_decisions: list[dict[str, Any]] = Field(default_factory=list)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    final_status: str
    error: str | None = None


def start_workflow_run(
    *,
    request_context: RequestContext,
    user_message: str,
    workflow_id: str,
    execution_plan: dict[str, Any],
) -> WorkflowRunRecord:
    record = WorkflowRunRecord(
        run_id=f"run_{uuid.uuid4().hex[:12]}",
        timestamp=datetime.now(UTC),
        request_context=_context_summary(request_context),
        user_message=_sanitize_user_message(request_context, user_message),
        workflow_id=workflow_id,
        execution_plan=execution_plan,
        final_status="started",
    )
    _write_record(record)
    return record


def append_tool_call(run_id: str, tool_call: dict[str, Any]) -> WorkflowRunRecord:
    record = _load_record(run_id)
    record.tool_calls.append(tool_call)
    _write_record(record)
    return record


def append_safety_decision(run_id: str, safety_decision: dict[str, Any]) -> WorkflowRunRecord:
    record = _load_record(run_id)
    record.safety_decisions.append(safety_decision)
    _write_record(record)
    return record


def finish_workflow_run(
    run_id: str,
    *,
    final_status: str,
    evidence_refs: list[dict[str, Any]] | None = None,
) -> WorkflowRunRecord:
    record = _load_record(run_id)
    if evidence_refs is not None:
        record.evidence_refs = evidence_refs
    record.final_status = final_status
    record.error = None
    _write_record(record)
    return record


def fail_workflow_run(run_id: str, *, error: str) -> WorkflowRunRecord:
    record = _load_record(run_id)
    record.final_status = "failed"
    record.error = error
    _write_record(record)
    return record


def _load_record(run_id: str) -> WorkflowRunRecord:
    path = _workflow_run_path(run_id)
    return WorkflowRunRecord.model_validate(load_json_path(path))


def _write_record(record: WorkflowRunRecord) -> None:
    save_json_path(
        _workflow_run_path(record.run_id, timestamp=record.timestamp),
        record.model_dump(mode="json"),
    )


def _workflow_run_path(run_id: str, *, timestamp: datetime | None = None) -> Any:
    target_timestamp = timestamp or datetime.now(UTC)
    date_dir = get_workflow_runs_dir() / target_timestamp.strftime("%Y-%m-%d")
    return date_dir / f"{run_id}.json"


def _context_summary(request_context: RequestContext) -> dict[str, Any]:
    return {
        "channel": request_context.channel,
        "guild_id": request_context.guild_id,
        "chat_id": request_context.chat_id,
        "user_id": request_context.user_id,
        "is_admin_context": request_context.is_admin_context,
        "message_id": request_context.message_id,
        "timestamp": to_jsonable(request_context.timestamp),
        "locale": request_context.locale,
        "visibility": request_context.visibility,
    }


def _sanitize_user_message(request_context: RequestContext, user_message: str) -> str:
    if request_context.visibility == "public":
        return user_message
    message_id = request_context.message_id or "unknown"
    return f"[redacted private content] message_id={message_id}"
