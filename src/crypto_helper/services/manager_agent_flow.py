from __future__ import annotations

import re
from typing import Any

from pydantic import Field

from crypto_helper.core.evidence_store import search_evidence
from crypto_helper.core.registry_service import get_active_kols, resolve_kol_query
from crypto_helper.core.stats_service import compare_kols, get_kol_performance
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
    direct_result: dict[str, Any] | None = None
    delegate_request: dict[str, Any] | None = None
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
    direct_result = _execute_direct_workflow(workflow_id, entity_resolution, user_message)
    if direct_result is not None:
        postcheck = output_safety_postcheck(
            request_context,
            workflow_id,
            direct_result,
        )
        append_safety_decision(run.run_id, postcheck.model_dump(mode="json"))
        finish_workflow_run(
            run.run_id,
            final_status="completed",
            evidence_refs=_extract_evidence_refs(direct_result),
        )
        return ManagerFlowResult(
            workflow_id=workflow_id,
            delegation_target="manager-agent",
            execution_plan=plan.model_dump(mode="json"),
            safety_decisions=[*safety_decisions, postcheck.model_dump(mode="json")],
            resolved_entities=entity_resolution,
            response_mode="direct_result",
            response_payload={"result_type": workflow_id},
            direct_result=direct_result,
            delegate_request=None,
            workflow_run_id=run.run_id,
        )
    delegate_request = _build_delegate_request(
        workflow_id=workflow_id,
        user_message=user_message,
        resolved_entities=entity_resolution,
    )
    postcheck = output_safety_postcheck(
        request_context,
        workflow_id,
        {
            "workflow_id": workflow_id,
            "delegation_target": delegate_request["target_agent"],
            "resolved_entities": entity_resolution,
        },
    )
    append_safety_decision(run.run_id, postcheck.model_dump(mode="json"))
    finish_workflow_run(run.run_id, final_status="planned")
    return ManagerFlowResult(
        workflow_id=workflow_id,
        delegation_target=delegate_request["target_agent"],
        execution_plan=plan.model_dump(mode="json"),
        safety_decisions=[*safety_decisions, postcheck.model_dump(mode="json")],
        resolved_entities=entity_resolution,
        response_mode="delegate",
        response_payload={"workflow_id": workflow_id},
        direct_result=None,
        delegate_request=delegate_request,
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
        direct_result=None,
        delegate_request=None,
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


def _execute_direct_workflow(
    workflow_id: str,
    resolved_entities: dict[str, Any],
    user_message: str,
) -> dict[str, Any] | None:
    kol_resolution = resolved_entities.get("kol", {})
    kol_query = kol_resolution.get("display_name")
    symbol = _preferred_symbol(resolved_entities)
    time_range = _extract_time_range(user_message)
    if workflow_id == "kol_list":
        return {
            "items": [entry.model_dump(mode="json") for entry in get_active_kols()],
            "status": "active",
        }
    if workflow_id == "kol_lookup" and kol_query:
        resolution = resolve_kol_query(kol_query)
        entry = resolution.get("entry")
        return {
            "entry": entry.model_dump(mode="json") if isinstance(entry, KOLRegistryEntry) else None,
            "lookup": resolution,
        }
    if workflow_id == "kol_stats":
        if kol_query:
            performance = get_kol_performance(kol_query, symbol=symbol, time_range=time_range)
            return performance.model_dump(mode="json")
        comparison = compare_kols(symbol=symbol, time_range=time_range)
        return comparison.model_dump(mode="json")
    if workflow_id == "evidence_lookup":
        if kol_query is None:
            return None
        evidence = search_evidence(
            kol_query=kol_query,
            symbol=symbol,
            query=user_message,
            limit=5,
        )
        return evidence.model_dump(mode="json")
    return None


def _build_delegate_request(
    *,
    workflow_id: str,
    user_message: str,
    resolved_entities: dict[str, Any],
) -> dict[str, Any]:
    kol_resolution = resolved_entities.get("kol", {})
    payload = {
        "workflow_id": workflow_id,
        "target_agent": _delegation_target_for_workflow(workflow_id),
        "message": user_message,
        "resolved_entities": resolved_entities,
        "suggested_tools": [],
    }
    if workflow_id == "kol_persona":
        payload["suggested_tools"] = [
            "crypto_helper_get_soul",
            "crypto_helper_get_profile",
            "crypto_helper_search_evidence",
        ]
        payload["inputs"] = {
            "kol": kol_resolution.get("display_name"),
            "question": user_message,
        }
    elif workflow_id in {"kol_report", "daily_market_report"}:
        payload["suggested_tools"] = [
            "crypto_helper_generate_report"
            if workflow_id == "kol_report"
            else "crypto_helper_generate_daily_market_report"
        ]
        payload["inputs"] = {
            "kol": kol_resolution.get("display_name"),
            "range": _extract_time_range(user_message),
        }
    elif workflow_id == "security_refusal":
        payload["suggested_tools"] = ["crypto_helper_security_review"]
        payload["inputs"] = {"text": user_message}
    else:
        payload["inputs"] = {}
    return payload


def _preferred_symbol(resolved_entities: dict[str, Any]) -> str | None:
    symbols = resolved_entities.get("symbols", [])
    return symbols[0] if symbols else None


def _extract_time_range(user_message: str) -> str:
    normalized = user_message.lower()
    explicit = re.search(r"\b(\d+[dwmy])\b", normalized)
    if explicit:
        return explicit.group(1)
    chinese_days = re.search(r"最近\s*(\d+)\s*天", user_message)
    if chinese_days:
        return f"{chinese_days.group(1)}d"
    if "今天" in user_message or "today" in normalized:
        return "1d"
    return "7d"


def _extract_evidence_refs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    refs = payload.get("evidence_refs")
    if isinstance(refs, list):
        return [item for item in refs if isinstance(item, dict)]
    result = payload.get("result")
    if isinstance(result, dict) and isinstance(result.get("evidence_refs"), list):
        return [item for item in result["evidence_refs"] if isinstance(item, dict)]
    return []


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)
