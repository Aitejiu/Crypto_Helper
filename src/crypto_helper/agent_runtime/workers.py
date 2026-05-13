from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from crypto_helper.agent_runtime.schemas import (
    DelegationTask,
    WorkerExecutionResult,
    WorkerExecutionStatus,
)
from crypto_helper.core.import_service import process_pending_imports, promote_imported_kols
from crypto_helper.core.persona_service import ask_persona
from crypto_helper.core.profile_service import refresh_profile
from crypto_helper.core.registry_service import archive_kol, disable_kol
from crypto_helper.core.report_service import generate_daily_market_report, generate_kol_report
from crypto_helper.core.security_review import review_text


def run_persona_runtime_task(task: DelegationTask) -> WorkerExecutionResult:
    kol_query = str(task.inputs.get("kol_query") or task.inputs.get("kol") or "")
    question = str(task.inputs.get("topic") or task.inputs.get("question") or "")
    answer = ask_persona(kol_query, question)
    return WorkerExecutionResult(
        task_id=task.task_id,
        target_agent=task.target_agent,
        status=WorkerExecutionStatus.COMPLETED,
        output_payload=answer.model_dump(mode="json"),
        evidence_refs=[item.model_dump(mode="json") for item in answer.evidence_refs],
        limitations=list(answer.limitations),
        completed_at=datetime.now(UTC),
    )


def run_report_task(task: DelegationTask) -> WorkerExecutionResult:
    if task.workflow_id == "daily_market_report":
        report = generate_daily_market_report(time_range=str(task.inputs.get("range") or "1d"))
    else:
        report = generate_kol_report(
            str(task.inputs.get("kol_query") or task.inputs.get("kol") or ""),
            time_range=str(task.inputs.get("range") or "7d"),
        )
    return WorkerExecutionResult(
        task_id=task.task_id,
        target_agent=task.target_agent,
        status=WorkerExecutionStatus.COMPLETED,
        output_payload=report.model_dump(mode="json"),
        evidence_refs=[item.model_dump(mode="json") for item in report.evidence_refs],
        limitations=list(report.limitations),
        completed_at=datetime.now(UTC),
    )


def run_security_task(task: DelegationTask) -> WorkerExecutionResult:
    text = str(task.inputs.get("user_message") or task.inputs.get("text") or "")
    decision = review_text(text)
    blocked = decision.action.value in {"deny", "require_approval", "redact"}
    return WorkerExecutionResult(
        task_id=task.task_id,
        target_agent=task.target_agent,
        status=WorkerExecutionStatus.BLOCKED if blocked else WorkerExecutionStatus.COMPLETED,
        output_payload=decision.model_dump(mode="json"),
        evidence_refs=[],
        limitations=[decision.reason],
        completed_at=datetime.now(UTC),
    )


def run_manager_admin_task(task: DelegationTask) -> WorkerExecutionResult:
    workflow_id = task.workflow_id
    if workflow_id == "admin_import_pending":
        payload: Any = process_pending_imports()
    elif workflow_id == "admin_refresh_profile":
        payload = refresh_profile(str(task.inputs["kol_query"]))
    elif workflow_id == "admin_disable_kol":
        payload = disable_kol(str(task.inputs["kol_query"]))
    elif workflow_id == "admin_archive_kol":
        payload = archive_kol(str(task.inputs["kol_query"]))
    elif workflow_id == "admin_promote_kols":
        payload = promote_imported_kols(
            source_dir=str(task.inputs["source_dir"]),
            min_signals=int(task.inputs.get("min_signals", 1)),
        )
    else:
        raise ValueError(f"Unsupported admin workflow: {workflow_id}")
    evidence_refs = payload.get("evidence_refs", []) if isinstance(payload, dict) else []
    limitations = payload.get("limitations", []) if isinstance(payload, dict) else []
    return WorkerExecutionResult(
        task_id=task.task_id,
        target_agent=task.target_agent,
        status=WorkerExecutionStatus.COMPLETED,
        output_payload=payload if isinstance(payload, dict) else {"result": payload},
        evidence_refs=evidence_refs if isinstance(evidence_refs, list) else [],
        limitations=limitations if isinstance(limitations, list) else [],
        completed_at=datetime.now(UTC),
    )
