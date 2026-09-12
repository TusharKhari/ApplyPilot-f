"""Unit tests for Stop Before Submit feature (fill full form, user takes last step)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from rich.console import Console

from applypilot.apply.terminal_control import TerminalController
from applypilot.apply.prompt import build_prompt
from applypilot import config


_MINIMAL_PROFILE = {
    "personal": {
        "full_name": "Tushar Khari",
        "preferred_name": "Tushar",
        "email": "tushar@example.com",
        "password": "Password123",
        "phone": "+49 15510834439",
        "address": "Rombacher Strasse 91",
        "city": "Aalen",
        "province_state": "BW",
        "country": "Germany",
        "postal_code": "73430",
    },
    "work_authorization": {
        "legally_authorized_to_work": "Yes",
        "require_sponsorship": "No",
    },
    "availability": {"earliest_start_date": "Immediately"},
    "compensation": {"salary_expectation": "55000", "salary_currency": "EUR"},
    "experience": {"years_of_experience_total": "1", "current_job_title": "Data Analyst"},
    "eeo_voluntary": {},
    "skills_boundary": {},
    "resume_facts": {},
    "site_credentials": {},
    "files": {},
}


def _setup_prompt_env(tmp_path, monkeypatch):
    app_dir = tmp_path / "applypilot_home"
    app_dir.mkdir()
    apply_worker_dir = app_dir / "apply-workers"
    apply_worker_dir.mkdir()

    profile_path = app_dir / "profile.json"
    profile_path.write_text(json.dumps(_MINIMAL_PROFILE), encoding="utf-8")

    search_path = app_dir / "searches.yaml"
    import yaml
    search_path.write_text(yaml.safe_dump({"location": {"primary": "Aalen"}, "queries": []}), encoding="utf-8")

    monkeypatch.setattr(config, "APP_DIR", app_dir)
    monkeypatch.setattr(config, "PROFILE_PATH", profile_path)
    monkeypatch.setattr(config, "SEARCH_CONFIG_PATH", search_path)
    monkeypatch.setattr(config, "APPLY_WORKER_DIR", apply_worker_dir)

    resume_dir = tmp_path / "tailored"
    resume_dir.mkdir()
    txt = resume_dir / "resume.txt"
    txt.write_text("Tushar Khari\nData Analyst\n", encoding="utf-8")
    doc = txt.with_suffix(".pdf")
    doc.write_bytes(b"%PDF-fake")

    return str(txt)


def test_build_prompt_stop_before_submit_true(tmp_path, monkeypatch):
    """When stop_before_submit=True, prompt instructs agent to stop before applying."""
    resume_txt = _setup_prompt_env(tmp_path, monkeypatch)
    job = {
        "url": "https://example.com/job/123",
        "title": "Data Analyst",
        "site": "example.com",
        "fit_score": 9,
        "tailored_resume_path": resume_txt,
    }

    prompt = build_prompt(job, tailored_resume="Resume text", stop_before_submit=True, doc_format="pdf")

    assert "STOP BEFORE APPLYING" in prompt
    assert "DO NOT click the final Submit" in prompt
    assert "RESULT:REVIEW_READY" in prompt
    assert "ONLY FILL THE FULL FORM" in prompt
    assert "The human user will take the final step to submit." in prompt
    # Does not instruct to search for thank you / application received
    assert 'Look for "thank you" or "application received"' not in prompt


def test_build_prompt_auto_submit_false(tmp_path, monkeypatch):
    """When stop_before_submit=False and dry_run=False, prompt instructs normal submit."""
    resume_txt = _setup_prompt_env(tmp_path, monkeypatch)
    job = {
        "url": "https://example.com/job/123",
        "title": "Data Analyst",
        "site": "example.com",
        "fit_score": 9,
        "tailored_resume_path": resume_txt,
    }

    prompt = build_prompt(
        job, tailored_resume="Resume text",
        stop_before_submit=False, dry_run=False, doc_format="pdf"
    )

    assert "STOP BEFORE APPLYING" not in prompt
    assert "Only click Submit after confirming everything is correct" in prompt
    assert 'Look for "thank you" or "application received"' in prompt


def test_prompt_review_ready_enter(monkeypatch):
    """User pressing Enter confirms submission."""
    tc = TerminalController()
    console = Console()
    job = {"title": "Data Analyst", "site": "Veolia", "url": "https://example.com"}

    with patch.object(console, "input", return_value=""):
        res = tc.prompt_review_ready(console, job)
        assert res == "applied"

    with patch.object(console, "input", return_value="done"):
        res = tc.prompt_review_ready(console, job)
        assert res == "applied"


def test_prompt_review_ready_skip(monkeypatch):
    """User typing skip or s skips the job."""
    tc = TerminalController()
    console = Console()
    job = {"title": "Data Analyst", "site": "Veolia", "url": "https://example.com"}

    with patch.object(console, "input", return_value="skip"):
        assert tc.prompt_review_ready(console, job) == "skip"

    with patch.object(console, "input", return_value="s"):
        assert tc.prompt_review_ready(console, job) == "skip"


def test_prompt_review_ready_instructions(monkeypatch):
    """User typing custom instructions returns instructions string."""
    tc = TerminalController()
    console = Console()
    job = {"title": "Data Analyst", "site": "Veolia", "url": "https://example.com"}

    with patch.object(console, "input", return_value="please change location to Berlin"):
        assert tc.prompt_review_ready(console, job) == "please change location to Berlin"
