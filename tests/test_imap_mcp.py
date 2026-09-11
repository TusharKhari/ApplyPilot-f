"""Tests for IMAP MCP server, email credentials resolution, and MIME parsing."""

import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from unittest.mock import patch, MagicMock

import pytest

from applypilot.apply.imap_mcp import (
    get_email_credentials,
    _decode_mime_header,
    _extract_body_text,
    search_emails,
    read_email,
    server,
)
from applypilot.apply.launcher import _get_gmail_mcp_config


def test_get_email_credentials_env():
    with patch.dict("os.environ", {
        "GMAIL_ADDRESS": "test@gmail.com",
        "GMAIL_APP_PASSWORD": "abcd efgh ijkl mnop",
    }):
        addr, pwd = get_email_credentials()
        assert addr == "test@gmail.com"
        assert pwd == "abcdefghijklmnop"  # spaces stripped


def test_decode_mime_header():
    # Plain ascii
    assert _decode_mime_header("Your verification code") == "Your verification code"
    # Base64 encoded UTF-8
    encoded = "=?utf-8?B?VmVyaWZpY2F0aW9uIENvZGU=?="
    assert _decode_mime_header(encoded) == "Verification Code"


def test_extract_body_text_plain():
    msg = MIMEText("Your verification code is 123456.", "plain", "utf-8")
    body = _extract_body_text(msg)
    assert "123456" in body


def test_extract_body_text_html():
    html_content = """
    <html>
      <body>
        <p>Hello Candidate,</p>
        <p>Please confirm your email by entering code: <b>789012</b></p>
        <a href="https://example.com/verify?token=abc">Verify Link</a>
      </body>
    </html>
    """
    msg = MIMEText(html_content, "html", "utf-8")
    body = _extract_body_text(msg)
    assert "789012" in body
    assert "https://example.com/verify?token=abc" in body


def test_extract_body_text_multipart():
    msg = MIMEMultipart("alternative")
    plain = MIMEText("Plain text: Code 555555", "plain", "utf-8")
    html_part = MIMEText("<p>HTML: Code 555555</p>", "html", "utf-8")
    msg.attach(plain)
    msg.attach(html_part)

    body = _extract_body_text(msg)
    assert "Code 555555" in body


def test_mcp_tools_registered():
    tools = [t.name for t in server._tool_manager.list_tools()]
    assert "search_emails" in tools
    assert "read_email" in tools


def test_search_emails_unconfigured():
    with patch("applypilot.apply.imap_mcp.get_email_credentials", return_value=(None, None)):
        res = search_emails("subject:verification")
        assert "Email credentials not configured" in res


def test_get_gmail_mcp_config_defaults_to_imap():
    with patch("applypilot.apply.imap_mcp.get_email_credentials", return_value=("test@gmail.com", "app_pw")):
        cfg = _get_gmail_mcp_config(backend="hermes")
        assert "-m" in cfg["args"]
        assert "applypilot.apply.imap_mcp" in cfg["args"]
