from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import typer

from crypto_helper import __version__
from crypto_helper.core.data_loader import load_json_path
from crypto_helper.core.evidence_store import (
    query_events,
    query_news,
    query_opinions,
    query_trade_calls,
    search_evidence,
)
from crypto_helper.core.import_service import (
    import_core_tables,
    process_pending_imports,
    promote_imported_kols,
)
from crypto_helper.core.persona_service import ask_persona
from crypto_helper.core.profile_service import get_profile, refresh_profile
from crypto_helper.core.registry_service import (
    add_mock_kol,
    archive_kol,
    disable_kol,
    get_active_kols,
    list_kols,
    resolve_kol_query,
)
from crypto_helper.core.report_service import (
    collect_report_context,
    finalize_report,
    generate_daily_market_report,
    generate_kol_report,
    generate_report_draft,
    validate_report_claims,
)
from crypto_helper.core.security_review import review_text
from crypto_helper.core.soul_store import apply_soul_patch_mock, generate_soul_patch_mock, get_soul
from crypto_helper.core.stats_service import (
    compare_kols,
    get_active_symbols,
    get_kol_performance,
    get_market_summary,
)
from crypto_helper.models.common import DomainError, ok_response, to_jsonable
from crypto_helper.request_context import RequestContext
from crypto_helper.security.schemas import SafetyAction, SafetyDecision, SafetyLevel
from crypto_helper.services.manager_agent_flow import handle_manager_request

app = typer.Typer(
    name="crypto-helper",
    help="Secure Multi-KOL Agent Workspace domain CLI.",
    no_args_is_help=True,
    invoke_without_command=True,
)
registry_app = typer.Typer(help="Registry operations.")
soul_app = typer.Typer(help="SOUL operations.")
profile_app = typer.Typer(help="Profile operations.")
evidence_app = typer.Typer(help="Evidence operations.")
stats_app = typer.Typer(help="Stats operations.")
persona_app = typer.Typer(help="Persona operations.")
report_app = typer.Typer(help="Report operations.")
security_app = typer.Typer(help="Security operations.")
import_app = typer.Typer(help="Data import operations.")
manager_app = typer.Typer(help="Manager entry workflow operations.")

app.add_typer(registry_app, name="registry")
app.add_typer(soul_app, name="soul")
app.add_typer(profile_app, name="profile")
app.add_typer(evidence_app, name="evidence")
app.add_typer(stats_app, name="stats")
app.add_typer(persona_app, name="persona")
app.add_typer(report_app, name="report")
app.add_typer(security_app, name="security")
app.add_typer(import_app, name="import")
app.add_typer(manager_app, name="manager")

F = TypeVar("F", bound=Callable[[], Any])


@app.callback()
def root(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show the crypto-helper version and exit.",
        is_eager=True,
    ),
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@registry_app.command("list")
def registry_list(
    status: str = typer.Option("active", "--status"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: {"items": list_kols(status=status), "status": status})


@registry_app.command("lookup")
def registry_lookup(
    query: str = typer.Option(..., "--query"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: _lookup_payload(query))


@registry_app.command("add-mock")
def registry_add_mock(
    display_name: str = typer.Option(..., "--display-name"),
    symbols: str = typer.Option(..., "--symbols"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(
        lambda: add_mock_kol(
            display_name=display_name,
            aliases=[],
            allowed_symbols=[item.strip() for item in symbols.split(",") if item.strip()],
        )
    )


@registry_app.command("disable")
def registry_disable(
    kol: str = typer.Option(..., "--kol"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: disable_kol(kol))


@registry_app.command("archive")
def registry_archive(
    kol: str = typer.Option(..., "--kol"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: archive_kol(kol))


@soul_app.command("get")
def soul_get(
    kol: str = typer.Option(..., "--kol"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: get_soul(kol))


@soul_app.command("patch")
def soul_patch(
    kol: str = typer.Option(..., "--kol"),
    observed_behavior: str = typer.Option(..., "--observed-behavior"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: generate_soul_patch_mock(kol, observed_behavior))


@soul_app.command("apply-patch")
def soul_apply_patch(
    kol: str = typer.Option(..., "--kol"),
    patch_id: str | None = typer.Option(None, "--patch-id"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: apply_soul_patch_mock(kol, patch_id))


@profile_app.command("get")
def profile_get(
    kol: str = typer.Option(..., "--kol"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: get_profile(kol))


@profile_app.command("refresh")
def profile_refresh(
    kol: str = typer.Option(..., "--kol"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: refresh_profile(kol))


@evidence_app.command("search")
def evidence_search(
    kol: str | None = typer.Option(None, "--kol"),
    symbol: str | None = typer.Option(None, "--symbol"),
    query: str | None = typer.Option(None, "--query"),
    source_type: str | None = typer.Option(None, "--source-type"),
    limit: int = typer.Option(5, "--limit"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(
        lambda: search_evidence(
            kol_query=kol, symbol=symbol, query=query, source_type=source_type, limit=limit
        )
    )


@evidence_app.command("trade-calls")
def evidence_trade_calls(
    kol: str | None = typer.Option(None, "--kol"),
    symbol: str | None = typer.Option(None, "--symbol"),
    status: str | None = typer.Option(None, "--status"),
    time_range: str | None = typer.Option(None, "--range"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(
        lambda: {
            "items": query_trade_calls(
                kol_query=kol, symbol=symbol, status=status, time_range=time_range
            )
        }
    )


@evidence_app.command("events")
def evidence_events(
    kol: str | None = typer.Option(None, "--kol"),
    symbol: str | None = typer.Option(None, "--symbol"),
    event_type: str | None = typer.Option(None, "--event-type"),
    time_range: str | None = typer.Option(None, "--range"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(
        lambda: {
            "items": query_events(
                kol_query=kol,
                symbol=symbol,
                event_type=event_type,
                time_range=time_range,
            )
        }
    )


@evidence_app.command("opinions")
def evidence_opinions(
    kol: str | None = typer.Option(None, "--kol"),
    symbol: str | None = typer.Option(None, "--symbol"),
    sentiment: str | None = typer.Option(None, "--sentiment"),
    time_range: str | None = typer.Option(None, "--range"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(
        lambda: {
            "items": query_opinions(
                kol_query=kol,
                symbol=symbol,
                sentiment=sentiment,
                time_range=time_range,
            )
        }
    )


@evidence_app.command("news")
def evidence_news(
    symbol: str | None = typer.Option(None, "--symbol"),
    importance: str | None = typer.Option(None, "--importance"),
    time_range: str | None = typer.Option(None, "--range"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(
        lambda: {"items": query_news(symbol=symbol, importance=importance, time_range=time_range)}
    )


@stats_app.command("compare")
def stats_compare(
    symbol: str | None = typer.Option(None, "--symbol"),
    time_range: str = typer.Option("30d", "--range"),
    include_dynamic: bool = typer.Option(True, "--include-dynamic/--exclude-dynamic"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(
        lambda: compare_kols(symbol=symbol, time_range=time_range, include_dynamic=include_dynamic)
    )


@stats_app.command("performance")
def stats_performance(
    kol: str = typer.Option(..., "--kol"),
    symbol: str | None = typer.Option(None, "--symbol"),
    time_range: str = typer.Option("30d", "--range"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: get_kol_performance(kol, symbol=symbol, time_range=time_range))


@stats_app.command("active-symbols")
def stats_active_symbols(
    kol: str = typer.Option(..., "--kol"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: get_active_symbols(kol))


@stats_app.command("market-summary")
def stats_market_summary(
    symbol: str | None = typer.Option(None, "--symbol"),
    time_range: str = typer.Option("1d", "--range"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: get_market_summary(symbol=symbol, time_range=time_range))


@persona_app.command("ask")
def persona_ask(
    kol: str = typer.Option(..., "--kol"),
    question: str = typer.Option(..., "--question"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: ask_persona(kol, question))


@report_app.command("kol")
def report_kol(
    kol: str = typer.Option(..., "--kol"),
    time_range: str = typer.Option("7d", "--range"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: generate_kol_report(kol, time_range=time_range))


@report_app.command("daily-market")
def report_daily_market(
    time_range: str = typer.Option("1d", "--range"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: generate_daily_market_report(time_range=time_range))


@report_app.command("collect-context")
def report_collect_context(
    kol_id: str = typer.Option(..., "--kol-id"),
    time_range: str = typer.Option("7d", "--range"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: collect_report_context(kol_id, time_range=time_range))


@report_app.command("generate-draft")
def report_generate_draft(
    context_file: str = typer.Option(..., "--context-file"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: generate_report_draft(load_json_path(Path(context_file))))


@report_app.command("validate-claims")
def report_validate_claims(
    draft_file: str = typer.Option(..., "--draft-file"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(
        lambda: validate_report_claims(
            load_json_path(Path(draft_file)),
            {
                ref["evidence_id"]: ref
                for ref in load_json_path(Path(draft_file)).get("evidence_refs", [])
            },
        )
    )


@report_app.command("finalize")
def report_finalize(
    validated_draft_file: str = typer.Option(..., "--validated-draft-file"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(
        lambda: finalize_report(
            load_json_path(Path(validated_draft_file)),
            SafetyDecision(
                action=SafetyAction.ALLOW,
                safety_level=SafetyLevel.GUARDED,
                reason="CLI finalize default safety gate.",
            ),
        )
    )


@security_app.command("review")
def security_review_command(
    text: str = typer.Argument(...),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: review_text(text))


@import_app.command("core-tables")
def import_core_tables_command(
    source_dir: str = typer.Option(..., "--source-dir"),
    output_dir: str | None = typer.Option(None, "--output-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: import_core_tables(source_dir=source_dir, output_dir=output_dir))


@import_app.command("promote-kols")
def import_promote_kols_command(
    source_dir: str = typer.Option(..., "--source-dir"),
    output_dir: str | None = typer.Option(None, "--output-dir"),
    min_signals: int = typer.Option(1, "--min-signals"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(
        lambda: promote_imported_kols(
            source_dir=source_dir,
            output_dir=output_dir,
            min_signals=min_signals,
        )
    )


@import_app.command("process-pending")
def import_process_pending_command(
    pending_dir: str | None = typer.Option(None, "--pending-dir"),
    output_dir: str | None = typer.Option(None, "--output-dir"),
    min_signals: int = typer.Option(1, "--min-signals"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(
        lambda: process_pending_imports(
            pending_dir=pending_dir,
            output_dir=output_dir,
            min_signals=min_signals,
        )
    )


@manager_app.command("handle-request")
def manager_handle_request_command(
    message: str = typer.Option(..., "--message"),
    channel: str = typer.Option(..., "--channel"),
    chat_id: str = typer.Option(..., "--chat-id"),
    user_id: str = typer.Option(..., "--user-id"),
    guild_id: str | None = typer.Option(None, "--guild-id"),
    is_admin_context: bool = typer.Option(False, "--is-admin-context"),
    message_id: str | None = typer.Option(None, "--message-id"),
    timestamp: str | None = typer.Option(None, "--timestamp"),
    locale: str = typer.Option("zh-CN", "--locale"),
    visibility: str = typer.Option("public", "--visibility"),
    raw_event_file: str | None = typer.Option(None, "--raw-event-file"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(
        lambda: handle_manager_request(
            _build_request_context(
                channel=channel,
                guild_id=guild_id,
                chat_id=chat_id,
                user_id=user_id,
                is_admin_context=is_admin_context,
                message_id=message_id,
                timestamp=timestamp,
                locale=locale,
                visibility=visibility,
                raw_event_file=raw_event_file,
            ),
            message,
        )
    )


def main() -> None:
    app()


def _lookup_payload(query: str) -> dict[str, Any]:
    resolution = resolve_kol_query(query)
    entry = resolution["entry"]
    if entry is None:
        raise DomainError(
            f"KOL not found: {query}",
            code="KOL_AMBIGUOUS_QUERY" if resolution["ambiguous"] else "KOL_NOT_FOUND",
            metadata={
                "query": query,
                "suggestions": resolution["suggestions"],
                "hint": resolution["hint"],
                "list_command": resolution["list_command"],
            },
        )
    return {
        "entry": entry,
        "lookup": {
            "query": query,
            "matched_by": resolution["matched_by"],
            "matched_value": resolution["matched_value"],
            "confidence": resolution["confidence"],
        },
        "active_kols": get_active_kols(),
    }


def _emit(callback: F) -> None:
    try:
        payload = ok_response(callback())
        typer.echo(json.dumps(to_jsonable(payload), ensure_ascii=False))
    except DomainError as exc:
        typer.echo(json.dumps(exc.to_response(), ensure_ascii=False))
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # pragma: no cover
        typer.echo(
            json.dumps(
                {
                    "ok": False,
                    "error": str(exc),
                    "code": "UNEXPECTED_ERROR",
                    "metadata": {},
                },
                ensure_ascii=False,
            )
        )
        raise typer.Exit(code=1) from exc


def _build_request_context(
    *,
    channel: str,
    guild_id: str | None,
    chat_id: str,
    user_id: str,
    is_admin_context: bool,
    message_id: str | None,
    timestamp: str | None,
    locale: str,
    visibility: str,
    raw_event_file: str | None,
) -> RequestContext:
    raw_event = load_json_path(Path(raw_event_file)) if raw_event_file else None
    payload: dict[str, Any] = {
        "channel": channel,
        "guild_id": guild_id,
        "chat_id": chat_id,
        "user_id": user_id,
        "is_admin_context": is_admin_context,
        "message_id": message_id,
        "locale": locale,
        "visibility": visibility,
        "raw_event": raw_event,
    }
    if timestamp is not None:
        payload["timestamp"] = timestamp
    return RequestContext.model_validate(payload)
