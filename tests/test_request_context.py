from __future__ import annotations

from crypto_helper.request_context import (
    build_request_context_from_discord_event,
    build_request_context_from_telegram_event,
    is_admin_context,
    is_public_context,
)


def test_build_request_context_from_discord_event() -> None:
    event = {
        "id": "msg-1",
        "guild_id": "guild-1",
        "channel_id": "channel-1",
        "timestamp": "2026-05-08T08:00:00+00:00",
        "author": {
            "id": "user-1",
            "locale": "zh-CN",
        },
        "member": {
            "permissions": {
                "administrator": True,
            }
        },
    }

    context = build_request_context_from_discord_event(event)

    assert context.channel == "discord"
    assert context.guild_id == "guild-1"
    assert context.chat_id == "channel-1"
    assert context.user_id == "user-1"
    assert context.message_id == "msg-1"
    assert context.visibility == "public"
    assert context.is_admin_context is False
    assert is_public_context(context) is True


def test_build_request_context_from_telegram_event() -> None:
    event = {
        "message_id": "88",
        "date": 1778227200,
        "chat": {
            "id": "-10012345",
            "type": "private",
        },
        "from": {
            "id": "admin-1",
            "language_code": "zh-CN",
            "is_admin": True,
        },
    }

    context = build_request_context_from_telegram_event(event)

    assert context.channel == "telegram"
    assert context.chat_id == "-10012345"
    assert context.user_id == "admin-1"
    assert context.message_id == "88"
    assert context.visibility == "admin"
    assert is_admin_context(context) is True


def test_context_visibility_helpers() -> None:
    public_context = build_request_context_from_telegram_event(
        {
            "message_id": "1",
            "date": "2026-05-08T08:00:00+00:00",
            "chat": {"id": "-1001", "type": "supergroup"},
            "from": {"id": "user-1", "language_code": "en-US"},
        }
    )
    private_context = build_request_context_from_discord_event(
        {
            "id": "dm-1",
            "channel_id": "dm-channel",
            "timestamp": "2026-05-08T08:00:00+00:00",
            "author": {"id": "user-2"},
        }
    )

    assert is_public_context(public_context) is True
    assert is_admin_context(public_context) is False
    assert private_context.visibility == "private"
    assert is_public_context(private_context) is False
    assert is_admin_context(private_context) is False
