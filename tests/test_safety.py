from __future__ import annotations

from crypto_helper.request_context import RequestContext
from crypto_helper.security import (
    SafetyAction,
    check_workflow_permission,
    output_safety_postcheck,
    safety_precheck,
)
from crypto_helper.workflows.registry import WorkflowRegistry


def test_public_context_admin_import_is_rejected() -> None:
    registry = WorkflowRegistry()
    registry.load_default_workflows()
    context = RequestContext(
        channel="telegram",
        guild_id=None,
        chat_id="-10001",
        user_id="user-1",
        visibility="public",
    )

    decision = check_workflow_permission(context, registry.get("admin_import_pending"))

    assert decision.action == SafetyAction.REQUIRE_ADMIN


def test_admin_context_admin_import_is_allowed() -> None:
    registry = WorkflowRegistry()
    registry.load_default_workflows()
    context = RequestContext(
        channel="telegram",
        guild_id=None,
        chat_id="admin-chat",
        user_id="admin-1",
        visibility="admin",
        is_admin_context=True,
    )

    decision = check_workflow_permission(context, registry.get("admin_import_pending"))

    assert decision.action == SafetyAction.ALLOW


def test_persona_impersonation_output_is_blocked() -> None:
    context = RequestContext(
        channel="discord",
        guild_id="guild-1",
        chat_id="chat-1",
        user_id="user-1",
        visibility="public",
    )

    decision = output_safety_postcheck(context, "kol_persona", "我是 KOL_A，我现在建议买入。")

    assert decision.action == SafetyAction.REFUSE


def test_direct_investment_advice_is_high_risk() -> None:
    context = RequestContext(
        channel="telegram",
        guild_id=None,
        chat_id="chat-2",
        user_id="user-2",
        visibility="private",
    )

    decision = safety_precheck(context, "现在应该买入 ETH 还是开杠杆做多？")

    assert decision.action == SafetyAction.DOWNGRADE


def test_admin_disable_workflow_plan_contains_audit_log() -> None:
    registry = WorkflowRegistry()
    registry.load_default_workflows()

    workflow = registry.get("admin_disable_kol")

    assert workflow.visibility == "admin"
    assert workflow.public_callable is False
    assert workflow.allowed_agents == ["manager-admin"]
    assert "audit_log" in workflow.plan_steps
