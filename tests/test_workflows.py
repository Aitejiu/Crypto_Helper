from __future__ import annotations

import pytest

from crypto_helper.models.common import DomainError
from crypto_helper.request_context import RequestContext
from crypto_helper.workflows import WorkflowExecutor, WorkflowRegistry


def test_workflow_registry_register_and_get() -> None:
    registry = WorkflowRegistry()
    registry.load_default_workflows()

    workflow = registry.get("kol_persona")

    assert workflow.workflow_name == "KOL Persona"
    assert workflow.visibility == "public"


def test_workflow_registry_public_admin_filtering() -> None:
    registry = WorkflowRegistry()
    registry.load_default_workflows()

    public_ids = {workflow.workflow_id for workflow in registry.list_public_workflows()}
    admin_ids = {workflow.workflow_id for workflow in registry.list_admin_workflows()}

    assert "admin_import_pending" not in public_ids
    assert "admin_import_pending" in admin_ids
    assert "admin_disable_kol" in admin_ids
    assert "admin_archive_kol" in admin_ids
    assert "kol_lookup" in public_ids


def test_workflow_registry_find_by_intent() -> None:
    registry = WorkflowRegistry()
    registry.load_default_workflows()

    workflow = registry.find(intent="historical_simulation")

    assert workflow is not None
    assert workflow.workflow_id == "kol_persona"


def test_workflow_executor_builds_plan() -> None:
    registry = WorkflowRegistry()
    registry.load_default_workflows()
    executor = WorkflowExecutor(registry)
    context = RequestContext(
        channel="telegram",
        guild_id=None,
        chat_id="chat-1",
        user_id="user-1",
        visibility="private",
    )

    plan = executor.build_plan(
        context,
        "kol_persona",
        {"kol_query": "Trader Gauls", "topic": "BTC support reclaim"},
    )

    assert plan.workflow_id == "kol_persona"
    assert plan.validated_inputs["kol_query"] == "Trader Gauls"
    assert "crypto_helper_search_evidence" in plan.allowed_tools
    assert "kol_resolver" in plan.plan_steps


def test_workflow_executor_requires_inputs() -> None:
    registry = WorkflowRegistry()
    registry.load_default_workflows()
    executor = WorkflowExecutor(registry)
    context = RequestContext(
        channel="discord",
        guild_id="guild-1",
        chat_id="chat-1",
        user_id="user-1",
        visibility="public",
    )

    with pytest.raises(DomainError) as exc_info:
        executor.build_plan(context, "kol_persona", {"kol_query": "Trader Gauls"})

    assert exc_info.value.code == "WORKFLOW_MISSING_INPUTS"


def test_public_workflows_do_not_reference_admin_only_tools() -> None:
    registry = WorkflowRegistry()
    registry.load_default_workflows()
    forbidden_tools = {
        "crypto_helper_registry_add_mock",
        "crypto_helper_registry_disable_mock",
        "crypto_helper_registry_archive_mock",
    }

    for workflow in registry.list_public_workflows():
        assert forbidden_tools.isdisjoint(set(workflow.allowed_tools))
