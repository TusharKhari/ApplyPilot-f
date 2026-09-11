"""Tests for applying to a target URL directly via CLI / acquire_job."""

from unittest.mock import patch
from applypilot import config
from applypilot.apply.launcher import acquire_job
from applypilot.config import is_manual_ats, load_no_signup_domains


def test_workday_not_marked_manual_or_no_signup():
    """Workday must not be marked as manual_ats or in no_signup_domains,
    since ApplyPilot natively automates Workday account creation and login."""
    workday_url = "https://valeo.wd3.myworkdayjobs.com/en-US/valeo_jobs/job/123"
    assert not is_manual_ats(workday_url)
    assert "myworkdayjobs.com" not in load_no_signup_domains()


def test_acquire_job_target_url_success(tmp_db):
    """Passing target_url creates/finds the job and acquires it."""
    conn = tmp_db()
    test_url = "https://example.com/jobs/dev-123"
    job = acquire_job(target_url=test_url, worker_id=0)
    assert job is not None
    assert job["url"] == test_url
    assert job["fit_score"] == 10


def test_acquire_job_target_url_overrides_manual_ats(tmp_db):
    """Explicitly passing target_url should attempt the application
    even if the domain is on the manual_ats list."""
    conn = tmp_db()
    manual_url = "https://ibegin.tcsapps.com/candidate/job/456"
    assert is_manual_ats(manual_url)

    job = acquire_job(target_url=manual_url, worker_id=0)
    assert job is not None
    assert job["url"] == manual_url


def test_acquire_job_target_url_resets_previous_status(tmp_db):
    """If a job was previously marked 'manual' or 'failed', targeting it again
    resets the status and re-acquires it."""
    conn = tmp_db()
    test_url = "https://example.com/jobs/failed-before"
    conn.execute("""
        INSERT INTO jobs (url, title, site, application_url, fit_score, apply_status, apply_category, apply_error, state)
        VALUES (?, 'Old Job', 'example.com', ?, 10, 'failed', 'technical', 'network error', 'apply_failed')
    """, (test_url, test_url))
    conn.commit()

    job = acquire_job(target_url=test_url, worker_id=0)
    assert job is not None
    assert job["url"] == test_url
    assert job["apply_status"] != "failed"
