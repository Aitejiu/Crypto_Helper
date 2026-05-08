from __future__ import annotations

from typing import Any, Callable, cast

import pytest

from crypto_helper.core import report_service
from crypto_helper.models.evidence import EvidenceSearchResult
from crypto_helper.core.report_service import (
    collect_report_context,
    finalize_report,
    generate_daily_market_report,
    generate_kol_report,
    generate_report_draft,
    validate_report_claims,
)
from crypto_helper.models.common import DomainError
from crypto_helper.security.schemas import SafetyAction, SafetyDecision, SafetyLevel


def test_kol_a_report_includes_evidence_appendix(runtime_data_dir: object) -> None:
    del runtime_data_dir
    report = generate_kol_report("KOL_A", time_range="7d")
    assert "Evidence Appendix" in report.markdown


def test_kol_x_report_includes_low_confidence_limitation(runtime_data_dir: object) -> None:
    del runtime_data_dir
    report = generate_kol_report("KOL_X", time_range="7d")
    assert any("low confidence" in limitation.lower() for limitation in report.limitations)


def test_not_found_kol_report_refused(runtime_data_dir: object) -> None:
    del runtime_data_dir
    with pytest.raises(DomainError):
        generate_kol_report("KOL_Z", time_range="7d")


def test_daily_market_report_includes_news_evidence(runtime_data_dir: object) -> None:
    del runtime_data_dir
    report = generate_daily_market_report(time_range="1d")
    assert any(ref.source_type == "news" for ref in report.evidence_refs)


def test_collect_report_context_uses_search_evidence(
    monkeypatch: pytest.MonkeyPatch,
    runtime_data_dir: object,
) -> None:
    del runtime_data_dir
    called = {"count": 0}
    original = cast(
        Callable[..., EvidenceSearchResult],
        getattr(report_service, "search_evidence"),
    )

    def wrapped_search_evidence(
        kol_query: str | None = None,
        symbol: str | None = None,
        query: str | None = None,
        source_type: str | None = None,
        limit: int = 5,
    ) -> EvidenceSearchResult:
        called["count"] += 1
        return original(
            kol_query=kol_query,
            symbol=symbol,
            query=query,
            source_type=source_type,
            limit=limit,
        )

    monkeypatch.setattr(report_service, "search_evidence", wrapped_search_evidence)

    context = collect_report_context("KOL_A", time_range="7d")

    assert context["evidence_refs"]
    assert called["count"] == 1


def test_report_draft_generation(runtime_data_dir: object) -> None:
    del runtime_data_dir
    context = collect_report_context("KOL_A", time_range="7d")
    draft = generate_report_draft(context)
    assert draft["claims"]


def test_report_validate_claims_flags_unsupported_claim(runtime_data_dir: object) -> None:
    del runtime_data_dir
    context = collect_report_context("KOL_A", time_range="7d")
    draft = generate_report_draft(context)
    draft["claims"][0]["evidence_refs"] = []
    validated = validate_report_claims(
        draft,
        {ref["evidence_id"]: ref for ref in draft["evidence_refs"]},
    )
    assert validated["claim_issues"]


def test_final_report_is_safe(runtime_data_dir: object) -> None:
    del runtime_data_dir
    context = collect_report_context("KOL_A", time_range="7d")
    draft = generate_report_draft(context)
    validated = validate_report_claims(
        draft,
        {ref["evidence_id"]: ref for ref in draft["evidence_refs"]},
    )
    final = finalize_report(
        validated,
        SafetyDecision(
            action=SafetyAction.ALLOW,
            safety_level=SafetyLevel.GUARDED,
            reason="ok",
        ),
    )
    assert "buy now" not in final["report"]["markdown"].lower()
