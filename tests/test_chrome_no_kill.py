"""Tests verifying Chrome is never closed, terminated, or killed."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from applypilot.apply import chrome


def test_cleanup_worker_never_kills_chrome():
    """cleanup_worker should remove tracking without killing the Chrome process or tree."""
    mock_proc = MagicMock(spec=subprocess.Popen)
    mock_proc.pid = 99999
    mock_proc.poll.return_value = None

    with patch.object(chrome, "_kill_process_tree") as mock_kill_tree, \
         patch.object(chrome, "_kill_on_port") as mock_kill_port:
        chrome.cleanup_worker(0, mock_proc)

        mock_kill_tree.assert_not_called()
        mock_kill_port.assert_not_called()
        mock_proc.kill.assert_not_called()
        mock_proc.terminate.assert_not_called()


def test_kill_all_chrome_is_noop():
    """kill_all_chrome should never kill processes or ports."""
    mock_proc = MagicMock(spec=subprocess.Popen)
    mock_proc.pid = 88888
    mock_proc.poll.return_value = None

    with chrome._chrome_lock:
        chrome._chrome_procs[0] = mock_proc

    with patch.object(chrome, "_kill_process_tree") as mock_kill_tree, \
         patch.object(chrome, "_kill_on_port") as mock_kill_port:
        chrome.kill_all_chrome(force=True)

        mock_kill_tree.assert_not_called()
        mock_kill_port.assert_not_called()
        mock_proc.kill.assert_not_called()


def test_cleanup_on_exit_is_noop():
    """cleanup_on_exit should never kill processes or ports."""
    with patch.object(chrome, "_kill_process_tree") as mock_kill_tree, \
         patch.object(chrome, "_kill_on_port") as mock_kill_port:
        chrome.cleanup_on_exit()

        mock_kill_tree.assert_not_called()
        mock_kill_port.assert_not_called()


def test_keep_browser_always_true():
    """Chrome keep_browser is permanently True and cannot be disabled."""
    chrome.set_keep_browser(False)
    assert chrome.get_keep_browser() is True


def test_launch_chrome_adopts_existing_running_instance():
    """launch_chrome adopts existing running Chrome on the port without launching new proc or killing."""
    with patch("applypilot.apply.chrome.probe_existing_chrome", return_value=54321), \
         patch("applypilot.apply.chrome._kill_on_port") as mock_kill_port, \
         patch("subprocess.Popen") as mock_popen:
        proc = chrome.launch_chrome(worker_id=0, port=9222)

        assert isinstance(proc, chrome._AdoptedChromeProcess)
        assert proc.pid == 54321
        mock_kill_port.assert_not_called()
        mock_popen.assert_not_called()


def test_find_chrome_pid_for_port_macos():
    """_find_chrome_pid_for_port calls lsof on non-Linux platforms."""
    with patch("platform.system", return_value="Darwin"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=" 12345 \n", returncode=0)
        pid = chrome._find_chrome_pid_for_port(9222)
        assert pid == 12345
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "lsof" in args
