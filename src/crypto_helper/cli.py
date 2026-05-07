from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, TypeVar

import typer

from crypto_helper import __version__
from crypto_helper.core.evidence_store import (
    query_events,
    query_news,
    query_opinions,
    query_trade_calls,
    search_evidence,
)
from crypto_helper.core.persona_service import ask_persona
from crypto_helper.core.profile_service import get_profile, refresh_profile
from crypto_helper.core.registry_service import (
    add_mock_kol,
    archive_kol,
    disable_kol,
    get_active_kols,
    list_kols,
    lookup_kol,
)
from crypto_helper.core.report_service import generate_daily_market_report, generate_kol_report
from crypto_helper.core.security_review import review_text
from crypto_helper.core.soul_store import apply_soul_patch_mock, generate_soul_patch_mock, get_soul
from crypto_helper.core.stats_service import (
    compare_kols,
    get_active_symbols,
    get_kol_performance,
    get_market_summary,
)
from crypto_helper.models.common import DomainError, ok_response, to_jsonable

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

app.add_typer(registry_app, name="registry")
app.add_typer(soul_app, name="soul")
app.add_typer(profile_app, name="profile")
app.add_typer(evidence_app, name="evidence")
app.add_typer(stats_app, name="stats")
app.add_typer(persona_app, name="persona")
app.add_typer(report_app, name="report")
app.add_typer(security_app, name="security")

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


@security_app.command("review")
def security_review_command(
    text: str = typer.Argument(...),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    del json_output
    _emit(lambda: review_text(text))


def main() -> None:
    app()


def _lookup_payload(query: str) -> dict[str, Any]:
    entry = lookup_kol(query)
    if entry is None:
        raise DomainError(
            f"KOL not found: {query}", code="KOL_NOT_FOUND", metadata={"query": query}
        )
    return {"entry": entry, "active_kols": get_active_kols()}


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
