from __future__ import annotations

from crypto_helper.core.profile_service import get_profile, refresh_profile


def test_get_profile(runtime_data_dir: object) -> None:
    del runtime_data_dir
    payload = get_profile("KOL_A")
    assert payload["profile"].kol_id == "kol_a"


def test_refresh_profile(runtime_data_dir: object) -> None:
    del runtime_data_dir
    payload = refresh_profile("KOL_A")
    assert payload["mock_only"] is True
    assert payload["profile"].active_symbols
