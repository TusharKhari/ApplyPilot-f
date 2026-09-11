"""Tests for dry-run gate injection and release."""
from applypilot.apply.chrome import _DRY_RUN_GATE_JS, _RELEASE_GATE_JS, inject_dry_run_gate, release_dry_run_gate


def test_dry_run_gate_js_structure():
    assert "__ap_dry_run_active = true" in _DRY_RUN_GATE_JS
    assert "if (!window.__ap_dry_run_active) return;" in _DRY_RUN_GATE_JS
    assert "submit" in _DRY_RUN_GATE_JS
    assert "SUBMIT_RE" in _DRY_RUN_GATE_JS


def test_release_gate_js_structure():
    assert "window.__ap_dry_run_active = false" in _RELEASE_GATE_JS
    assert "ApplyPilot dry-run" in _RELEASE_GATE_JS


def test_functions_callable_with_mock():
    # Calling on non-existent port returns False gracefully without crash
    assert release_dry_run_gate(65432) is False
    assert inject_dry_run_gate(65432) is False
