from __future__ import annotations

import pytest

from crypto_helper.core.report_service import generate_daily_market_report, generate_kol_report
from crypto_helper.models.common import DomainError


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
