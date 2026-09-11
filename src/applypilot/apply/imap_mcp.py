"""IMAP-based MCP server for Gmail verification codes and application tracking.

Exposes `search_emails` and `read_email` tools over stdio MCP transport,
allowing autonomous agents (Hermes, Claude Code) to retrieve 2FA/verification codes
and activation links without requiring complex Google Cloud Console OAuth setup.
Works directly with a 16-character Google App Password via imap.gmail.com.
"""

import email
import email.header
import html
import imaplib
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional

from mcp.server.mcpserver import MCPServer

logger = logging.getLogger("applypilot.imap_mcp")


def get_email_credentials() -> tuple[Optional[str], Optional[str]]:
    """Resolve Gmail address and App Password from environment or profile.json."""
    # 1. Environment variables
    address = (
        os.environ.get("GMAIL_ADDRESS")
        or os.environ.get("EMAIL_ADDRESS")
    )
    password = (
        os.environ.get("GMAIL_APP_PASSWORD")
        or os.environ.get("EMAIL_APP_PASSWORD")
        or os.environ.get("EMAIL_PASSWORD")
    )

    # 2. Check ~/.applypilot/.env if not in os.environ
    if not password:
        from applypilot.config import ENV_PATH
        if ENV_PATH.exists():
            for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("\"'")
                if k in ("GMAIL_APP_PASSWORD", "EMAIL_APP_PASSWORD", "EMAIL_PASSWORD"):
                    password = v
                elif k in ("GMAIL_ADDRESS", "EMAIL_ADDRESS") and not address:
                    address = v

    # 3. Check profile.json
    if not address or not password:
        from applypilot.config import PROFILE_PATH
        if PROFILE_PATH.exists():
            try:
                data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
                personal = data.get("personal", {})
                if not address:
                    address = personal.get("email")
                if not password:
                    password = (
                        personal.get("email_app_password")
                        or personal.get("email_password")
                    )
            except Exception:
                pass

    if password:
        # Strip spaces from 16-char app passwords (Google displays them as "xxxx xxxx xxxx xxxx")
        password = password.replace(" ", "")

    return address, password


def _decode_mime_header(val: str) -> str:
    """Safely decode MIME-encoded headers (e.g. =?utf-8?b?...?=)."""
    if not val:
        return ""
    try:
        header = email.header.make_header(email.header.decode_header(val))
        return str(header).strip()
    except Exception:
        return val.strip()


def _extract_body_text(msg: email.message.Message) -> str:
    """Extract and clean plain text from an email message (handles multipart & HTML)."""
    plain_parts = []
    html_parts = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in content_disposition:
                continue

            charset = part.get_content_charset() or "utf-8"
            payload = part.get_payload(decode=True)
            if not payload:
                continue

            try:
                text = payload.decode(charset, errors="replace")
            except Exception:
                text = payload.decode("utf-8", errors="replace")

            if content_type == "text/plain":
                plain_parts.append(text)
            elif content_type == "text/html":
                html_parts.append(text)
    else:
        content_type = msg.get_content_type()
        charset = msg.get_content_charset() or "utf-8"
        payload = msg.get_payload(decode=True)
        if payload:
            try:
                text = payload.decode(charset, errors="replace")
            except Exception:
                text = payload.decode("utf-8", errors="replace")

            if content_type == "text/html":
                html_parts.append(text)
            else:
                plain_parts.append(text)

    if plain_parts:
        body = "\n".join(plain_parts)
    elif html_parts:
        # Strip HTML tags and convert breaks to newlines
        raw_html = "\n".join(html_parts)
        # Remove script and style elements
        clean = re.sub(r"<(script|style)[^>]*>[\s\S]*?</\1>", "", raw_html, flags=re.IGNORECASE)
        # Preserve links: convert <a href="url">text</a> to text (url)
        clean = re.sub(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r'\2 (\1)', clean, flags=re.IGNORECASE | re.DOTALL)
        # Convert break and paragraph tags to newlines
        clean = re.sub(r"</?(p|div|tr|br|li)[^>]*>", "\n", clean, flags=re.IGNORECASE)
        # Strip remaining tags
        clean = re.sub(r"<[^>]+>", " ", clean)
        body = html.unescape(clean)
    else:
        body = ""

    # Collapse excessive blank lines
    lines = [line.strip() for line in body.splitlines()]
    compact = []
    prev_blank = False
    for line in lines:
        if not line:
            if not prev_blank:
                compact.append("")
                prev_blank = True
        else:
            compact.append(line)
            prev_blank = False

    return "\n".join(compact).strip()


class GmailIMAPClient:
    """Client for querying Gmail via IMAP with SSL."""

    def __init__(self, host: str = "imap.gmail.com", port: int = 993):
        self.host = host
        self.port = port

    def connect(self) -> tuple[Optional[imaplib.IMAP4_SSL], Optional[str]]:
        address, password = get_email_credentials()
        if not address or not password:
            return None, (
                "Email credentials not configured. Please set GMAIL_APP_PASSWORD in "
                "~/.applypilot/.env or ~/.applypilot/profile.json (generate an App Password "
                "at https://myaccount.google.com/apppasswords)."
            )

        try:
            mail = imaplib.IMAP4_SSL(self.host, self.port)
            mail.login(address, password)
            return mail, None
        except imaplib.IMAP4.error as e:
            return None, f"Gmail IMAP authentication failed for {address}: {e}"
        except Exception as e:
            return None, f"Gmail IMAP connection failed: {e}"

    def search_emails(self, query: str, max_results: int = 10) -> str:
        """Search Gmail using X-GM-RAW query syntax."""
        mail, err = self.connect()
        if err or not mail:
            return err or "Failed to connect to Gmail"

        try:
            # Select INBOX first; if query contains in:spam or is searching for verification,
            # we check INBOX and if nothing found, check [Gmail]/All Mail
            mail.select("INBOX", readonly=True)

            msg_ids = []
            # Try Gmail's native X-GM-RAW extension
            try:
                # Remove quotes around entire query if any
                clean_query = query.strip()
                status, data = mail.search(None, "X-GM-RAW", f'"{clean_query}"')
                if status == "OK" and data and data[0]:
                    msg_ids = data[0].split()
            except Exception:
                pass

            # Fallback if X-GM-RAW returned nothing and "to:" was in query
            if not msg_ids and "to:" in query:
                # Strip "to:..." and try keyword search
                sub_query = re.sub(r'to:[^\s]+\s*', '', query).strip()
                if sub_query:
                    try:
                        status, data = mail.search(None, "X-GM-RAW", f'"{sub_query}"')
                        if status == "OK" and data and data[0]:
                            msg_ids = data[0].split()
                    except Exception:
                        pass

            # If still nothing found in INBOX, try [Gmail]/All Mail
            if not msg_ids:
                try:
                    mail.select('"[Gmail]/All Mail"', readonly=True)
                    status, data = mail.search(None, "X-GM-RAW", f'"{query.strip()}"')
                    if status == "OK" and data and data[0]:
                        msg_ids = data[0].split()
                except Exception:
                    pass

            if not msg_ids:
                # If still nothing, return empty result
                return "No emails found matching query."

            # Most recent first
            msg_ids.reverse()
            msg_ids = msg_ids[:max_results]

            results = []
            for mid in msg_ids:
                mid_str = mid.decode("ascii") if isinstance(mid, bytes) else str(mid)
                # Fetch header fields only for fast preview
                status, data = mail.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE TO)])")
                if status != "OK" or not data:
                    continue

                raw_header = b""
                for item in data:
                    if isinstance(item, tuple) and len(item) > 1:
                        raw_header = item[1]
                        break

                hdr_msg = email.message_from_bytes(raw_header)
                subject = _decode_mime_header(hdr_msg.get("Subject", "(No Subject)"))
                from_addr = _decode_mime_header(hdr_msg.get("From", "(Unknown)"))
                date_str = _decode_mime_header(hdr_msg.get("Date", ""))

                results.append(
                    f"ID: {mid_str}\n"
                    f"Subject: {subject}\n"
                    f"From: {from_addr}\n"
                    f"Date: {date_str}\n"
                    f"Snippet: {subject}"
                )

            return "\n\n".join(results)

        except Exception as e:
            logger.exception("Error searching emails: %s", e)
            return f"Error searching emails: {e}"
        finally:
            try:
                mail.close()
                mail.logout()
            except Exception:
                pass

    def read_email(self, email_id: str) -> str:
        """Fetch and parse full email text by ID."""
        mail, err = self.connect()
        if err or not mail:
            return err or "Failed to connect to Gmail"

        try:
            # Try INBOX first, then [Gmail]/All Mail if not found
            mail.select("INBOX", readonly=True)
            status, data = mail.fetch(email_id.encode("ascii"), "(RFC822)")
            if status != "OK" or not data or not data[0]:
                try:
                    mail.select('"[Gmail]/All Mail"', readonly=True)
                    status, data = mail.fetch(email_id.encode("ascii"), "(RFC822)")
                except Exception:
                    pass

            if status != "OK" or not data or not data[0]:
                return f"Error: Email with ID {email_id} not found."

            raw_email = b""
            for item in data:
                if isinstance(item, tuple) and len(item) > 1:
                    raw_email = item[1]
                    break

            if not raw_email:
                return f"Error: Could not read content for email ID {email_id}."

            msg = email.message_from_bytes(raw_email)
            subject = _decode_mime_header(msg.get("Subject", "(No Subject)"))
            from_addr = _decode_mime_header(msg.get("From", "(Unknown)"))
            to_addr = _decode_mime_header(msg.get("To", "(Unknown)"))
            date_str = _decode_mime_header(msg.get("Date", ""))
            body = _extract_body_text(msg)

            return (
                f"Subject: {subject}\n"
                f"From: {from_addr}\n"
                f"To: {to_addr}\n"
                f"Date: {date_str}\n\n"
                f"{body}"
            )

        except Exception as e:
            logger.exception("Error reading email %s: %s", email_id, e)
            return f"Error reading email {email_id}: {e}"
        finally:
            try:
                mail.close()
                mail.logout()
            except Exception:
                pass


# Create MCP server instance
server = MCPServer("gmail")
_client = GmailIMAPClient()


@server.tool()
def search_emails(query: str, maxResults: int = 10) -> str:
    """Search Gmail for messages matching a query.

    Args:
        query: Gmail search query (e.g. 'to:user@gmail.com newer_than:2m verification').
        maxResults: Maximum number of results to return (default 10).

    Returns:
        List of matching emails with ID, Subject, From, Date, and Snippet.
    """
    return _client.search_emails(query, max_results=maxResults)


@server.tool()
def read_email(email_id: str) -> str:
    """Read full email message content and extract verification code or activation link.

    Args:
        email_id: The ID of the email to read (from search_emails).

    Returns:
        Full email details including Subject, From, To, Date, and decoded body text.
    """
    return _client.read_email(email_id)


def main():
    """Run the Gmail IMAP MCP server over stdio."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
