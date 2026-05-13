from __future__ import annotations

from crypto_helper.agent_runtime.queue import get_task
from crypto_helper.request_context import RequestContext
from crypto_helper.services.manager_agent_flow import handle_manager_request


def test_manager_flow_routes_persona_request(runtime_data_dir: object) -> None:
    del runtime_data_dir
    context = RequestContext(
        channel="discord",
        guild_id="guild-1",
        chat_id="chat-1",
        user_id="user-1",
        visibility="public",
    )

    result = handle_manager_request(context, "KOL_A 如果 BTC 跌破 62000，可能怎么看？")

    assert result.workflow_id == "kol_persona"
    assert result.delegation_target == "persona-runtime-agent"
    assert result.response_mode == "queue_enqueued"
    assert result.response_payload["queue_status"] == "pending"
    assert result.response_payload["task_id"]
    assert result.delegate_request is not None
    assert result.delegate_request["target_agent"] == "persona-runtime-agent"
    queued_task = get_task(result.response_payload["task_id"])
    assert queued_task is not None
    assert queued_task.target_agent == "persona-runtime-agent"


def test_manager_flow_blocks_admin_request_in_public_context(runtime_data_dir: object) -> None:
    del runtime_data_dir
    context = RequestContext(
        channel="telegram",
        guild_id=None,
        chat_id="public-chat",
        user_id="user-2",
        visibility="public",
    )

    result = handle_manager_request(context, "导入数据")

    assert result.workflow_id == "admin_import_pending"
    assert result.response_mode == "blocked"
    assert result.response_payload["reason"] == "no_permission"


def test_manager_flow_routes_market_report(runtime_data_dir: object) -> None:
    del runtime_data_dir
    context = RequestContext(
        channel="discord",
        guild_id="guild-2",
        chat_id="chat-2",
        user_id="user-3",
        visibility="public",
    )

    result = handle_manager_request(context, "生成今天的市场情报日报")

    assert result.workflow_id == "daily_market_report"
    assert result.delegation_target == "report-agent"
    assert result.response_mode == "queue_enqueued"
    assert result.response_payload["target_agent"] == "report-agent"


def test_manager_flow_executes_direct_kol_list(runtime_data_dir: object) -> None:
    del runtime_data_dir
    context = RequestContext(
        channel="discord",
        guild_id="guild-3",
        chat_id="chat-3",
        user_id="user-4",
        visibility="public",
    )

    result = handle_manager_request(context, "当前有哪些正在跟踪的 KOL？")

    assert result.workflow_id == "kol_list"
    assert result.response_mode == "direct_result"
    assert result.direct_result is not None
    assert result.direct_result["items"]
