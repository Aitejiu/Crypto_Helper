from __future__ import annotations

import re
from typing import Any

from pydantic import Field

from crypto_helper.models.common import DomainModel
from crypto_helper.models.registry import KOLRegistryEntry
from crypto_helper.request_context import RequestContext
from crypto_helper.security import (
    SafetyAction,
    check_workflow_permission,
    output_safety_postcheck,
    safety_precheck,
)
from crypto_helper.services.kol_resolver import resolve_kol
from crypto_helper.services.workflow_run_service import (
    append_safety_decision,
    finish_workflow_run,
    start_workflow_run,
)
from crypto_helper.workflows import WorkflowExecutor, WorkflowRegistry


class ManagerFlowResult(DomainModel):
    workflow_id: str
    delegation_target: str
    execution_plan: dict[str, Any]
    safety_decisions: list[dict[str, Any]] = Field(default_factory=list)
    resolved_entities: dict[str, Any] = Field(default_factory=dict)
    response_mode: str
    response_payload: dict[str, Any]
    workflow_run_id: str


def handle_manager_request(
    request_context: RequestContext,
    user_message: str,
) -> ManagerFlowResult:
    registry = WorkflowRegistry()
    registry.load_default_workflows()
    workflow_id = _route_workflow(user_message)
    entity_resolution = _resolve_entities(user_message)
    precheck = safety_precheck(request_context, user_message)
    workflow = registry.get(workflow_id)
    guard = check_workflow_permission(request_context, workflow)
    safety_decisions = [precheck.model_dump(mode="json"), guard.model_dump(mode="json")]
    if precheck.action == SafetyAction.REFUSE:
        return _blocked_result(
            request_context=request_context,
            workflow_id="security_refusal",
            user_message=user_message,
            delegation_target="security-agent",
            response_mode="refusal",
            response_payload={"reason": precheck.reason},
            safety_decisions=safety_decisions,
            resolved_entities=entity_resolution,
            registry=registry,
        )
    if precheck.action == SafetyAction.REQUIRE_ADMIN or guard.action == SafetyAction.REQUIRE_ADMIN:
        return _blocked_result(
            request_context=request_context,
            workflow_id=workflow_id,
            user_message=user_message,
            delegation_target="manager-admin",
            response_mode="blocked",
            response_payload={"reason": "no_permission"},
            safety_decisions=safety_decisions,
            resolved_entities=entity_resolution,
            registry=registry,
        )
    executor = WorkflowExecutor(registry)
    workflow_inputs = _build_workflow_inputs(workflow_id, user_message, entity_resolution)
    plan = executor.build_plan(request_context, workflow_id, workflow_inputs)
    run = start_workflow_run(
        request_context=request_context,
        user_message=user_message,
        workflow_id=workflow_id,
        execution_plan=plan.model_dump(mode="json"),
    )
    for decision in safety_decisions:
        append_safety_decision(run.run_id, decision)
    postcheck = output_safety_postcheck(
        request_context,
        workflow_id,
        {
            "workflow_id": workflow_id,
            "delegation_target": _delegation_target_for_workflow(workflow_id),
            "resolved_entities": entity_resolution,
        },
    )
    append_safety_decision(run.run_id, postcheck.model_dump(mode="json"))
    finish_workflow_run(run.run_id, final_status="planned")
    return ManagerFlowResult(
        workflow_id=workflow_id,
        delegation_target=_delegation_target_for_workflow(workflow_id),
        execution_plan=plan.model_dump(mode="json"),
        safety_decisions=[*safety_decisions, postcheck.model_dump(mode="json")],
        resolved_entities=entity_resolution,
        response_mode="planned",
        response_payload={
            "workflow_id": workflow_id,
            "delegation_target": _delegation_target_for_workflow(workflow_id),
        },
        workflow_run_id=run.run_id,
    )


def _blocked_result(
    *,
    request_context: RequestContext,
    workflow_id: str,
    user_message: str,
    delegation_target: str,
    response_mode: str,
    response_payload: dict[str, Any],
    safety_decisions: list[dict[str, Any]],
    resolved_entities: dict[str, Any],
    registry: WorkflowRegistry,
) -> ManagerFlowResult:
    executor = WorkflowExecutor(registry)
    plan = executor.build_plan(
        request_context,
        workflow_id if registry.find(workflow_id=workflow_id) is not None else "security_refusal",
        _build_workflow_inputs(workflow_id, user_message, resolved_entities, allow_partial=True),
    )
    run = start_workflow_run(
        request_context=request_context,
        user_message=user_message,
        workflow_id=workflow_id,
        execution_plan=plan.model_dump(mode="json"),
    )
    for decision in safety_decisions:
        append_safety_decision(run.run_id, decision)
    finish_workflow_run(run.run_id, final_status=response_mode)
    return ManagerFlowResult(
        workflow_id=workflow_id,
        delegation_target=delegation_target,
        execution_plan=plan.model_dump(mode="json"),
        safety_decisions=safety_decisions,
        resolved_entities=resolved_entities,
        response_mode=response_mode,
        response_payload=response_payload,
        workflow_run_id=run.run_id,
    )


def _route_workflow(user_message: str) -> str:
    lowered = user_message.lower()
    if _contains_any(lowered, ("导入数据", "import pending", "process pending")):
        return "admin_import_pending"
    if _contains_any(lowered, ("刷新画像", "refresh profile")):
        return "admin_refresh_profile"
    if _contains_any(lowered, ("停用", "disable kol")):
        return "admin_disable_kol"
    if _contains_any(lowered, ("归档", "archive kol")):
        return "admin_archive_kol"
    if _contains_any(lowered, ("周报", "report")) and "市场" not in user_message:
        return "kol_report"
    if _contains_any(lowered, ("日报", "today market", "市场情报")):
        return "daily_market_report"
    if _contains_any(lowered, ("为什么", "evidence")):
        return "evidence_lookup"
    if _contains_any(lowered, ("最近", "最准", "performance", "stats")):
        return "kol_stats"
    if _contains_any(lowered, ("当前有哪些", "tracked kol", "list kols")):
        return "kol_list"
    return "kol_persona"


def _resolve_entities(user_message: str) -> dict[str, Any]:
    symbol_matches = re.findall(r"\b[A-Z]{2,10}\b", user_message.upper())
    kol_resolution = _best_kol_resolution(user_message)
    return {
        "kol": kol_resolution,
        "symbols": symbol_matches,
        "topic": user_message,
    }


def _best_kol_resolution(user_message: str) -> dict[str, Any]:
    resolutions: list[dict[str, Any]] = []
    for token in re.findall(r"[\w@.\-\u4e00-\u9fff]+", user_message):
        if len(token) < 2:
            continue
        resolution = resolve_kol(token)
        if resolution["status"] != "not_found":
            resolutions.append(resolution)
    if not resolutions:
        return {"status": "not_found", "kol_id": None, "display_name": None}
    best = max(resolutions, key=lambda item: item.get("confidence", 0.0))
    entry = best.get("entry")
    return {
        **best,
        "entry": entry.model_dump(mode="json") if isinstance(entry, KOLRegistryEntry) else entry,
    }


def _build_workflow_inputs(
    workflow_id: str,
    user_message: str,
    resolved_entities: dict[str, Any],
    *,
    allow_partial: bool = False,
) -> dict[str, Any]:
    inputs: dict[str, Any] = {}
    kol_resolution = resolved_entities.get("kol", {})
    if kol_resolution.get("display_name"):
        inputs["kol_query"] = kol_resolution["display_name"]
    if workflow_id == "kol_persona":
        inputs["topic"] = user_message
    if workflow_id == "security_refusal":
        inputs["user_message"] = user_message
    if allow_partial:
        return inputs
    return inputs


def _delegation_target_for_workflow(workflow_id: str) -> str:
    if workflow_id in {"kol_persona"}:
        return "persona-runtime-agent"
    if workflow_id in {"kol_report", "daily_market_report"}:
        return "report-agent"
    if workflow_id in {
        "admin_import_pending",
        "admin_refresh_profile",
        "admin_promote_kols",
        "admin_disable_kol",
        "admin_archive_kol",
    }:
        return "manager-admin"
    if workflow_id == "security_refusal":
        return "security-agent"
    return "manager-agent"


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)
