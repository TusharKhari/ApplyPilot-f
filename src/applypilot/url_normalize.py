"""Rewrite embedded-ATS URLs to their canonical form."""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

# Bare host (no leading "www.") → Greenhouse tenant slug.
GREENHOUSE_HOST_SLUGS: dict[str, str] = {
    "stripe.com":              "stripe",
    "databricks.com":          "databricks",
    "pinterestcareers.com":    "pinterest",
    "careers.airbnb.com":      "airbnb",
    "jobs.dropbox.com":        "dropbox",
    "cast.ai":                 "castai",
    "sproutsocial.com":        "sproutsocial",
    "samsara.com":             "samsara",
    "instacart.careers":       "instacart",
    "hubspot.com":             "hubspot",
    "kentik.com":              "kentik",
    "consensys.io":            "consensys",
    "abnormal.ai":             "abnormalsecurity",
    "careers.toasttab.com":    "toast",
    "netskope.com":            "netskope",
    "upsun.com":               "upsun",
    "prizepicks.com":          "prizepicks",
    "fortisgames.com":         "fortisgames",
    "kaseya.com":              "kaseya",
    "nebius.com":              "nebius",
}

_RUNTIME_SLUGS_PATH: Path | None = None
_runtime_slugs_cache: dict[str, str] | None = None
_runtime_slugs_lock = threading.Lock()


def _runtime_slugs_path() -> Path:
    global _RUNTIME_SLUGS_PATH
    if _RUNTIME_SLUGS_PATH is None:
        from applypilot import config as _cfg
        _RUNTIME_SLUGS_PATH = _cfg.APP_DIR / "greenhouse_slugs_runtime.json"
    return _RUNTIME_SLUGS_PATH


def _load_runtime_slugs() -> dict[str, str]:
    global _runtime_slugs_cache
    if _runtime_slugs_cache is not None:
        return _runtime_slugs_cache
    with _runtime_slugs_lock:
        if _runtime_slugs_cache is not None:
            return _runtime_slugs_cache
        path = _runtime_slugs_path()
        if path.exists():
            try:
                _runtime_slugs_cache = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                logger.debug("Could not load runtime slug cache", exc_info=True)
                _runtime_slugs_cache = {}
        else:
            _runtime_slugs_cache = {}
    return _runtime_slugs_cache


def register_runtime_slug(host: str, slug: str) -> bool:
    if not host or not slug:
        return False
    host_lc = host.lower()
    if host_lc.startswith("www."):
        host_lc = host_lc[4:]
    if GREENHOUSE_HOST_SLUGS.get(host_lc) == slug:
        return False
    _load_runtime_slugs()
    with _runtime_slugs_lock:
        cache = _runtime_slugs_cache
        if cache is None:
            cache = {}
        if cache.get(host_lc) == slug:
            return False
        cache[host_lc] = slug
        try:
            path = _runtime_slugs_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")
            logger.info("Registered runtime greenhouse slug: %s → %s", host_lc, slug)
            return True
        except Exception:
            logger.debug("Could not persist runtime slug cache", exc_info=True)
            return False


def lookup_slug(host: str) -> str | None:
    if not host:
        return None
    host_lc = host.lower()
    if host_lc.startswith("www."):
        host_lc = host_lc[4:]
    static = GREENHOUSE_HOST_SLUGS.get(host_lc)
    if static:
        return static
    return _load_runtime_slugs().get(host_lc)


def canonicalize_application_url(url: str) -> str:
    if not url or not url.startswith(("http://", "https://")):
        return url

    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    if "greenhouse.io" in host:
        return url

    qs = parse_qs(parsed.query)
    gh_jid_vals = qs.get("gh_jid")
    if gh_jid_vals:
        gh_jid = gh_jid_vals[0]
        if gh_jid.isdigit():
            slug = lookup_slug(host)
            if slug:
                return f"https://job-boards.greenhouse.io/{slug}/jobs/{gh_jid}"

    return url


def parse_greenhouse_slug_from_iframe_src(iframe_src: str) -> str | None:
    if not iframe_src or not iframe_src.startswith(("http://", "https://")):
        return None
    parsed = urlparse(iframe_src)
    host = parsed.netloc.lower()
    if not host.endswith("greenhouse.io"):
        return None
    if parsed.path.startswith("/embed/job_app"):
        for_vals = parse_qs(parsed.query).get("for")
        if for_vals and for_vals[0]:
            return for_vals[0]
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 3 and parts[1] == "jobs" and parts[2].isdigit():
        return parts[0]
    return None
