from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

ContextVisibility = Literal["public", "private", "admin"]
ContextChannel = Literal["discord", "telegram"]


class RequestContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    channel: ContextChannel
    guild_id: str | None = None
    chat_id: str
    user_id: str
    is_admin_context: bool = False
    message_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    locale: str = "zh-CN"
    visibility: ContextVisibility = "public"
    raw_event: dict[str, Any] | None = None


def build_request_context_from_discord_event(event: dict[str, Any]) -> RequestContext:
    guild_id = _string_or_none(event.get("guild_id"))
    chat_id = _string_or_none(event.get("channel_id")) or _string_or_none(event.get("chat_id"))
    author = _mapping(event.get("author"))
    member = _mapping(event.get("member"))
    if chat_id is None:
        raise ValueError("Discord event is missing channel_id/chat_id.")
    user_id = _string_or_none(author.get("id")) or _string_or_none(event.get("user_id"))
    if user_id is None:
        raise ValueError("Discord event is missing author.id/user_id.")
    admin_flag = _coerce_bool(
        event.get("is_admin_context"),
        event.get("admin"),
        member.get("is_admin"),
        _mapping(member.get("permissions")).get("administrator"),
    )
    visibility = _derive_visibility(
        explicit=_string_or_none(event.get("visibility")),
        is_group_context=guild_id is not None,
        admin_flag=admin_flag,
    )
    return RequestContext(
        channel="discord",
        guild_id=guild_id,
        chat_id=chat_id,
        user_id=user_id,
        is_admin_context=visibility == "admin",
        message_id=_string_or_none(event.get("id")) or _string_or_none(event.get("message_id")),
        timestamp=_parse_timestamp(event.get("timestamp")),
        locale=_string_or_none(author.get("locale"))
        or _string_or_none(event.get("locale"))
        or "zh-CN",
        visibility=visibility,
        raw_event=event,
    )


def build_request_context_from_telegram_event(event: dict[str, Any]) -> RequestContext:
    chat = _mapping(event.get("chat"))
    sender = _mapping(event.get("from"))
    chat_id = _string_or_none(chat.get("id")) or _string_or_none(event.get("chat_id"))
    if chat_id is None:
        raise ValueError("Telegram event is missing chat.id/chat_id.")
    user_id = _string_or_none(sender.get("id")) or _string_or_none(event.get("user_id"))
    if user_id is None:
        raise ValueError("Telegram event is missing from.id/user_id.")
    chat_type = (_string_or_none(chat.get("type")) or "").lower()
    admin_flag = _coerce_bool(
        event.get("is_admin_context"),
        sender.get("is_admin"),
        event.get("is_chat_admin"),
        event.get("trusted_admin_context"),
        event.get("chat_member_status") in {"administrator", "creator"},
    )
    visibility = _derive_visibility(
        explicit=_string_or_none(event.get("visibility")),
        is_group_context=chat_type in {"group", "supergroup", "channel"},
        admin_flag=admin_flag,
    )
    return RequestContext(
        channel="telegram",
        guild_id=_string_or_none(chat.get("linked_chat_id")),
        chat_id=chat_id,
        user_id=user_id,
        is_admin_context=visibility == "admin",
        message_id=_string_or_none(event.get("message_id")),
        timestamp=_parse_timestamp(event.get("date") or event.get("timestamp")),
        locale=_string_or_none(sender.get("language_code"))
        or _string_or_none(event.get("locale"))
        or "zh-CN",
        visibility=visibility,
        raw_event=event,
    )


def is_public_context(context: RequestContext) -> bool:
    return context.visibility == "public"


def is_admin_context(context: RequestContext) -> bool:
    return context.is_admin_context


def _derive_visibility(
    *,
    explicit: str | None,
    is_group_context: bool,
    admin_flag: bool,
) -> ContextVisibility:
    if explicit in {"public", "private", "admin"}:
        return cast(ContextVisibility, explicit)
    if is_group_context:
        return "public"
    if admin_flag:
        return "admin"
    return "private"


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, str) and value.strip():
        normalized = value.strip().replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return datetime.now(UTC)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_bool(*values: Any) -> bool:
    for value in values:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes"}:
                return True
            if lowered in {"false", "0", "no"}:
                return False
        if isinstance(value, (int, float)) and value in {0, 1}:
            return bool(value)
    return False
