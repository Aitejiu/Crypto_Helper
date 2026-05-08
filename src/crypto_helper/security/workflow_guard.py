from __future__ import annotations

from crypto_helper.request_context import RequestContext, is_public_context
from crypto_helper.security.schemas import (
    SafetyAction,
    SafetyDecision,
    SafetyIssue,
    SafetyLevel,
)
from crypto_helper.workflows.schemas import WorkflowDefinition


def check_workflow_permission(
    request_context: RequestContext,
    workflow_definition: WorkflowDefinition,
) -> SafetyDecision:
    if not workflow_definition.public_callable and not request_context.is_admin_context:
        return _decision(
            action=SafetyAction.REQUIRE_ADMIN,
            level=SafetyLevel.ADMIN_ONLY,
            reason="This workflow is not callable from public or non-admin context.",
            issue_code="public_callable_denied",
        )
    if workflow_definition.visibility == "admin" and not request_context.is_admin_context:
        return _decision(
            action=SafetyAction.REQUIRE_ADMIN,
            level=SafetyLevel.ADMIN_ONLY,
            reason="Admin workflow is not allowed in public or non-admin context.",
            issue_code="admin_workflow_denied",
        )
    if (
        workflow_definition.safety_level == SafetyLevel.ADMIN_ONLY
        and not request_context.is_admin_context
    ):
        return _decision(
            action=SafetyAction.REQUIRE_ADMIN,
            level=SafetyLevel.ADMIN_ONLY,
            reason="This workflow requires an admin context.",
            issue_code="admin_safety_level_denied",
        )
    if workflow_definition.visibility == "public" and is_public_context(request_context):
        return _decision(
            action=SafetyAction.ALLOW,
            level=SafetyLevel.STANDARD,
            reason="Public workflow is allowed in public context.",
            issue_code="public_workflow_allowed",
        )
    return _decision(
        action=SafetyAction.ALLOW,
        level=SafetyLevel.GUARDED,
        reason="Workflow is allowed in the current context.",
        issue_code="workflow_allowed",
    )


def _decision(
    *,
    action: SafetyAction,
    level: SafetyLevel,
    reason: str,
    issue_code: str,
) -> SafetyDecision:
    return SafetyDecision(
        action=action,
        safety_level=level,
        reason=reason,
        issues=[
            SafetyIssue(
                code=issue_code,
                message=reason,
                severity=level,
            )
        ],
    )
