from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, cast

from crypto_helper.core.data_loader import append_jsonl
from crypto_helper.models.common import to_jsonable
from crypto_helper.request_context import RequestContext

AuditStream = Literal["registry", "import", "profile", "security"]


def write_audit_event(
    stream: AuditStream,
    *,
    event_type: str,
    actor: str,
    target_type: str,
    target_id: str,
    action: str,
    request_context: RequestContext | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    status: str = "success",
    error: str | None = None,
) -> str:
    record = {
        "timestamp": _now(),
        "event_type": event_type,
        "actor": actor,
        "request_context_summary": _context_summary(request_context),
        "target_type": target_type,
        "target_id": target_id,
        "action": action,
        "before": before,
        "after": after,
        "status": status,
        "error": error,
    }
    return str(append_jsonl(f"audit/{stream}.jsonl", record))


def write_registry_audit(**kwargs: Any) -> str:
    return write_audit_event("registry", **kwargs)


def write_import_audit(**kwargs: Any) -> str:
    return write_audit_event("import", **kwargs)


def write_profile_audit(**kwargs: Any) -> str:
    return write_audit_event("profile", **kwargs)


def write_security_audit(**kwargs: Any) -> str:
    return write_audit_event("security", **kwargs)


def _context_summary(request_context: RequestContext | None) -> dict[str, Any] | None:
    if request_context is None:
        return None
    return {
        "channel": request_context.channel,
        "guild_id": request_context.guild_id,
        "chat_id": request_context.chat_id,
        "user_id": request_context.user_id,
        "visibility": request_context.visibility,
        "is_admin_context": request_context.is_admin_context,
        "message_id": request_context.message_id,
        "locale": request_context.locale,
    }


def _now() -> str:
    return cast(str, to_jsonable(datetime.now(UTC)))
