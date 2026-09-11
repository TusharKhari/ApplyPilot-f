"""Unit tests for Hermes Agent integration into ApplyPilot."""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import yaml
import pytest

from applypilot import config
from applypilot.apply.launcher import _write_hermes_worker_config


class TestHermesConfig:
    def test_get_hermes_path_env(self, monkeypatch):
        """HERMES_PATH environment variable overrides search."""
        with tempfile.NamedTemporaryFile() as tf:
            monkeypatch.setenv("HERMES_PATH", tf.name)
            assert config.get_hermes_path() == tf.name

    def test_get_hermes_path_shutil(self, monkeypatch):
        """shutil.which finds hermes on PATH."""
        monkeypatch.delenv("HERMES_PATH", raising=False)
        with patch("shutil.which", return_value="/usr/local/bin/hermes"):
            assert config.get_hermes_path() == "/usr/local/bin/hermes"

    def test_get_agent_backend_forced(self, monkeypatch):
        """APPLYPILOT_AGENT environment variable overrides auto-detection."""
        monkeypatch.setenv("APPLYPILOT_AGENT", "claude")
        assert config.get_agent_backend() == "claude"

        monkeypatch.setenv("APPLYPILOT_AGENT", "hermes")
        assert config.get_agent_backend() == "hermes"

    def test_get_tier_unlocked_with_hermes_and_chrome(self, monkeypatch):
        """Tier 3 is unlocked when Hermes + Chrome + LLM key exist, even without Claude."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test_key")
        with (
            patch("shutil.which", side_effect=lambda x: None if x == "claude" else "/bin/chrome"),
            patch("applypilot.config.get_hermes_path", return_value="/fake/hermes"),
            patch("applypilot.config.get_chrome_path", return_value="/fake/chrome"),
        ):
            assert config.get_tier() == 3

    def test_get_tier_unlocked_with_nvidia_hermes_and_chrome(self, monkeypatch):
        """Tier 3 is unlocked when Hermes + Chrome + NVIDIA_API_KEY exist."""
        monkeypatch.setenv("NVIDIA_API_KEY", "test_key")
        with (
            patch("shutil.which", side_effect=lambda x: None if x == "claude" else "/bin/chrome"),
            patch("applypilot.config.get_hermes_path", return_value="/fake/hermes"),
            patch("applypilot.config.get_chrome_path", return_value="/fake/chrome"),
        ):
            assert config.get_tier() == 3

    def test_get_tier_2_when_no_agent_installed(self, monkeypatch):
        """Tier 2 when LLM key exists but neither Hermes nor Claude is installed."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test_key")
        with (
            patch("shutil.which", return_value=None),
            patch("applypilot.config.get_hermes_path", return_value=None),
            patch("applypilot.config.get_chrome_path", return_value="/fake/chrome"),
        ):
            assert config.get_tier() == 2

    def test_check_tier_messages(self):
        """check_tier raises SystemExit with message mentioning Hermes if Tier 3 missing."""
        with patch("applypilot.config.get_tier", return_value=2):
            with pytest.raises(SystemExit):
                config.check_tier(3, "auto-apply")


class TestHermesWorkerConfig:
    def test_write_hermes_worker_config(self, tmp_path):
        """Verify _write_hermes_worker_config produces valid config.yaml and .env."""
        port = 9222
        hermes_dir = _write_hermes_worker_config(
            worker_id=0,
            cdp_port=port,
            model="deepseek-flash",
            base_dir=tmp_path,
        )

        config_yaml = hermes_dir / "config.yaml"
        assert config_yaml.exists()
        cfg = yaml.safe_load(config_yaml.read_text(encoding="utf-8"))

        assert cfg["model"]["default"] == "deepseek-flash"
        assert cfg["model"]["provider"] == "deepseek"
        assert "browser" in cfg["agent"]["disabled_toolsets"]

        pw = cfg["mcp_servers"]["playwright"]
        assert pw["command"] == "npx"
        assert f"--cdp-endpoint=http://localhost:{port}" in pw["args"]
        assert "browser_install" in pw["tools"]["exclude"]

        # Gmail MCP server should have sensitive write tools excluded
        gm = cfg["mcp_servers"]["gmail"]
        assert "draft_email" in gm["tools"]["exclude"]
        assert "delete_email" in gm["tools"]["exclude"]

        env_file = hermes_dir / ".env"
        assert env_file.exists()

    def test_write_hermes_worker_config_nvidia(self, tmp_path, monkeypatch):
        """Verify _write_hermes_worker_config produces valid NVIDIA NIM config for Kimi-K3."""
        port = 9223
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key")
        hermes_dir = _write_hermes_worker_config(
            worker_id=1,
            cdp_port=port,
            model="kimi-k3",
            base_dir=tmp_path,
        )

        config_yaml = hermes_dir / "config.yaml"
        assert config_yaml.exists()
        cfg = yaml.safe_load(config_yaml.read_text(encoding="utf-8"))

        assert cfg["model"]["default"] == "moonshotai/kimi-k3"
        assert cfg["model"]["provider"] == "nvidia"
        assert cfg["model"]["base_url"] == "https://integrate.api.nvidia.com/v1"
        assert "browser" in cfg["agent"]["disabled_toolsets"]

        env_file = hermes_dir / ".env"
        assert env_file.exists()
        assert "NVIDIA_API_KEY=nvapi-test-key" in env_file.read_text(encoding="utf-8")
