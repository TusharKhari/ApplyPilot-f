"""Tests for cover letter handling, document upload priorities, and archiving to applied_cv/."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from applypilot import config
from applypilot.database import (
    sanitize_url_for_filename,
    archive_cover_letter,
    export_applied_json,
)
from applypilot.apply.prompt import build_prompt


def test_sanitize_url_for_filename_basic():
    url = "https://jobs.example.com/posting/123"
    stem = sanitize_url_for_filename(url)
    assert "/" not in stem
    assert ":" not in stem
    assert stem == "https___jobs.example.com_posting_123"


def test_sanitize_url_for_filename_special_chars_and_quotes():
    url = ' “https://example.com/jobs/dev?ref=board&utm=test”\n'
    stem = sanitize_url_for_filename(url)
    assert "/" not in stem
    assert "?" not in stem
    assert "“" not in stem
    assert "”" not in stem
    assert "https___example.com_jobs_dev_ref=board&utm=test" in stem


def test_sanitize_url_for_filename_length_capping():
    long_url = "https://example.com/" + "a" * 300
    stem = sanitize_url_for_filename(long_url, max_len=200)
    assert len(stem) <= 200
    assert "/" not in stem


def test_archive_cover_letter_success(tmp_path, monkeypatch):
    # Set up mock documents and applied_cv directories
    mock_docs = tmp_path / "documents"
    mock_docs.mkdir()
    mock_applied_cv = tmp_path / "applied_cv"
    mock_applied_cv.mkdir()

    source_cl = mock_docs / "cover_letter.pdf"
    source_cl.write_bytes(b"%PDF-1.4 test cover letter content")

    monkeypatch.setattr(config, "DOCUMENTS_DIR", mock_docs)
    monkeypatch.setattr(config, "APPLIED_CV_DIR", mock_applied_cv)
    monkeypatch.setattr(config, "COVER_LETTER_PDF_PATH", source_cl)

    job_url = "https://jobs.gema.de/jobportal/gema/viewAusschreibung/2026-122.html"
    archived_path = archive_cover_letter(job_url)

    assert archived_path is not None
    assert archived_path.exists()
    assert not source_cl.exists()  # File was moved
    assert archived_path.suffix == ".pdf"  # Preserved extension
    assert archived_path.parent == mock_applied_cv
    assert archived_path.read_bytes() == b"%PDF-1.4 test cover letter content"
    assert "jobs.gema.de" in archived_path.name
    assert "/" not in archived_path.name


def test_archive_cover_letter_missing_source(tmp_path, monkeypatch):
    mock_docs = tmp_path / "documents"
    mock_docs.mkdir()
    mock_cl = mock_docs / "cover_letter.pdf"  # Not created

    monkeypatch.setattr(config, "COVER_LETTER_PDF_PATH", mock_cl)
    res = archive_cover_letter("https://example.com/job/1")
    assert res is None


def test_export_applied_json_calls_archive(tmp_path, monkeypatch):
    mock_applied_json = tmp_path / "applied.json"

    monkeypatch.setattr(
        "applypilot.database.get_applied_jobs",
        lambda: [{"url": "https://example.com/job/1", "applied_at": "2026-09-13T10:00:00Z"}]
    )

    with patch("applypilot.database.archive_cover_letter") as mock_archive:
        export_applied_json(target_path=mock_applied_json, job_url="https://example.com/job/1")
        mock_archive.assert_called_once_with("https://example.com/job/1")

    assert mock_applied_json.exists()
    data = json.loads(mock_applied_json.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["url"] == "https://example.com/job/1"


def test_build_prompt_document_priority_hierarchy(tmp_path, monkeypatch):
    # Mock profile and dirs
    worker_dir = tmp_path / "worker-0"
    worker_dir.mkdir(parents=True)
    monkeypatch.setattr(config, "APPLY_WORKER_DIR", tmp_path)

    dummy_resume = tmp_path / "test_resume.pdf"
    dummy_resume.write_bytes(b"%PDF-1.4 resume")

    dummy_cl = tmp_path / "cover_letter.pdf"
    dummy_cl.write_bytes(b"%PDF-1.4 cover letter")

    dummy_other = tmp_path / "other_docs.pdf"
    dummy_other.write_bytes(b"%PDF-1.4 other documents")

    monkeypatch.setattr(config, "COVER_LETTER_PDF_PATH", dummy_cl)
    monkeypatch.setattr(config, "OTHER_DOCS_PDF_PATH", dummy_other)

    dummy_profile = {
        "personal": {
            "full_name": "Tushar Khari",
            "email": "test@example.com",
            "phone": "1234567890",
            "city": "Aalen",
        },
        "work_authorization": {"legally_authorized_to_work": "Yes"},
        "compensation": {"salary_expectation": "14", "salary_currency": "EUR"},
        "files": {
            "cover_letter": str(dummy_cl),
            "other_documents": str(dummy_other),
            "enrollment_certificate": str(tmp_path / "enrollment.pdf"),
            "transcript_of_records": str(tmp_path / "transcript.pdf"),
        }
    }
    monkeypatch.setattr(config, "load_profile", lambda: dummy_profile)
    monkeypatch.setattr(config, "load_search_config", lambda: {})

    job = {
        "url": "https://example.com/jobs/123",
        "title": "Working Student AI",
        "site": "example.com",
        "tailored_resume_path": str(dummy_resume),
    }

    prompt = build_prompt(
        job=job,
        tailored_resume="Python, Machine Learning",
        worker_id=0,
        doc_format="pdf",
    )

    # 1. Verify files section has explicit priorities 1, 2, 3, 4
    assert "== FILES & DOCUMENT UPLOAD HIERARCHY ==" in prompt
    assert "PRIORITY 1 -- RESUME / CV" in prompt
    assert "PRIORITY 2 -- COVER LETTER" in prompt
    assert "PRIORITY 3 -- OTHER DOCUMENTS" in prompt
    assert "PRIORITY 4 -- REMAINING DOCUMENTS" in prompt

    # 2. Verify rules section
    assert "== DOCUMENT UPLOAD PRIORITY & RULES ==" in prompt
    assert "1. RESUME / CV (Lebenslauf): Priority 1" in prompt
    assert "2. COVER LETTER (Anschreiben / Motivationsschreiben): Priority 2" in prompt
    assert "3. OTHER DOCS (other_docs.pdf / Weitere Dokumente / Additional Documents / Zeugnisse / Zertifikate / Anlagen): Priority 3" in prompt
    assert "4. REMAINING DOCUMENTS:" in prompt

    # 3. Verify step 6 follows the priority hierarchy
    assert "6. DOCUMENT UPLOADS — Follow the strict priority order:" in prompt
    assert "6a. Priority 1 (Resume / CV / Lebenslauf)" in prompt
    assert "6b. Priority 2 (Cover Letter / Anschreiben)" in prompt
    assert "6c. Priority 3 (Other Docs / Weitere Dokumente / Zeugnisse / Anlagen)" in prompt
    assert "6d. Priority 4 (Remaining Documents)" in prompt


def test_mark_job_archives_cover_letter():
    from applypilot.apply.launcher import mark_job

    with patch("applypilot.apply.launcher.get_connection") as mock_conn, \
         patch("applypilot.apply.launcher._db_retry_execute"), \
         patch("applypilot.apply.launcher.transition_state"), \
         patch("applypilot.apply.launcher._db_retry_commit"), \
         patch("applypilot.database.archive_cover_letter") as mock_archive, \
         patch("applypilot.database.export_applied_json") as mock_export:

        test_url = "https://example.com/jobs/test-mark"
        mark_job(test_url, "applied")

        mock_archive.assert_called_once_with(test_url)
        mock_export.assert_called_once_with(job_url=test_url)
