"""Unit tests for terminal control and pause/play takeover toggle."""

import threading
from unittest.mock import MagicMock, patch
from rich.console import Console

from applypilot.apply.terminal_control import TerminalController
from applypilot.apply.launcher import (
    trigger_takeover,
    trigger_handback,
    is_worker_paused,
    _takeover_events,
    _handback_events,
    _worker_state,
    _worker_state_lock,
)


def test_terminal_controller_non_tty():
    """When stdin is not a TTY, TerminalController behaves as safe no-op."""
    tc = TerminalController()
    # In test environment stdin is not a tty
    assert not tc._is_tty or not tc.is_active
    tc.start()
    assert tc.check_key(timeout=0.01) is None
    tc.stop()


def test_terminal_controller_mock_key():
    """TerminalController correctly reads key when select indicates data is ready."""
    tc = TerminalController()
    tc._is_tty = True
    tc._in_cbreak = True

    with patch("select.select", return_value=([MagicMock()], [], [])), \
         patch("sys.stdin.read", return_value="p"):
        assert tc.check_key() == "p"


def test_terminal_controller_prompt_takeover_empty():
    """When user presses Enter (empty input), instructions is None."""
    tc = TerminalController()
    console = Console()

    with patch.object(console, "input", return_value=""):
        res = tc.prompt_takeover(console, worker_id=0)
        assert res is None


def test_terminal_controller_prompt_takeover_with_instructions():
    """When user enters custom instructions, they are returned."""
    tc = TerminalController()
    console = Console()

    with patch.object(console, "input", return_value="Logged in, please continue"):
        res = tc.prompt_takeover(console, worker_id=0)
        assert res == "Logged in, please continue"


def test_trigger_takeover_and_handback():
    """Test pause (takeover) and resume (handback) state transitions."""
    wid = 99
    _takeover_events[wid] = threading.Event()
    _handback_events[wid] = threading.Event()
    with _worker_state_lock:
        _worker_state[wid] = {"status": "applying"}

    assert not is_worker_paused(wid)

    # 1. Trigger Pause / Takeover
    trigger_takeover(wid)
    assert _takeover_events[wid].is_set()
    assert is_worker_paused(wid)

    # 2. Trigger Resume / Handback
    trigger_handback(wid, instructions="custom context")
    assert not _takeover_events[wid].is_set()
    assert _handback_events[wid].is_set()
    with _worker_state_lock:
        assert _worker_state[wid]["handback_instructions"] == "custom context"
        assert _worker_state[wid]["status"] == "applying"

    # Cleanup
    _takeover_events.pop(wid, None)
    _handback_events.pop(wid, None)
    with _worker_state_lock:
        _worker_state.pop(wid, None)


def test_multiple_pause_and_resume_cycles():
    """Verify that pause and resume can be repeated multiple times without desync."""
    wid = 98
    _takeover_events[wid] = threading.Event()
    _handback_events[wid] = threading.Event()
    with _worker_state_lock:
        _worker_state[wid] = {"status": "applying"}

    for cycle in range(1, 4):
        # 1. Trigger Pause (takeover)
        trigger_takeover(wid)
        assert _takeover_events[wid].is_set(), f"Cycle {cycle}: takeover event must be set"
        assert not _handback_events[wid].is_set(), f"Cycle {cycle}: handback event must be cleared on takeover"
        assert is_worker_paused(wid), f"Cycle {cycle}: worker must report as paused"

        # 2. Trigger Resume (handback)
        instructions = f"Instructions for cycle {cycle}"
        trigger_handback(wid, instructions=instructions)
        assert not _takeover_events[wid].is_set(), f"Cycle {cycle}: takeover event must be cleared on handback"
        assert _handback_events[wid].is_set(), f"Cycle {cycle}: handback event must be set on handback"
        assert not is_worker_paused(wid), f"Cycle {cycle}: worker must report as not paused"

        # 3. Simulate worker loop consuming the handback
        with _worker_state_lock:
            assert _worker_state[wid]["handback_instructions"] == instructions
            assert _worker_state[wid]["status"] == "applying"
            _worker_state[wid]["handback_instructions"] = None
        _handback_events[wid].clear()
        assert not _handback_events[wid].is_set(), f"Cycle {cycle}: handback event must be cleared after worker resumption"

    # Cleanup
    _takeover_events.pop(wid, None)
    _handback_events.pop(wid, None)
    with _worker_state_lock:
        _worker_state.pop(wid, None)


def test_terminal_controller_flush():
    """Test flush method executes safely without errors."""
    tc = TerminalController()
    # On non-tty, flush is a no-op
    tc.flush()

    tc._is_tty = True
    with patch("applypilot.apply.terminal_control._HAS_TERMIOS", True), \
         patch("sys.stdin.fileno", return_value=0), \
         patch("applypilot.apply.terminal_control.termios.tcflush") as mock_tcflush:
        tc.flush()
        import termios
        mock_tcflush.assert_called_once_with(0, termios.TCIFLUSH)


def test_terminal_controller_start_stop_idempotent():
    """Test repeated start() and stop() calls preserve original terminal attributes."""
    tc = TerminalController()
    tc._is_tty = True

    dummy_attrs = [1, 2, 3, 4, 5, 6, [7]]
    with patch("applypilot.apply.terminal_control._HAS_TERMIOS", True), \
         patch("sys.stdin.fileno", return_value=0), \
         patch("applypilot.apply.terminal_control.termios.tcgetattr", return_value=dummy_attrs), \
         patch("applypilot.apply.terminal_control.tty.setcbreak") as mock_cbreak, \
         patch("applypilot.apply.terminal_control.termios.tcsetattr") as mock_setattr:

        # Cycle 1
        tc.start()
        assert tc.is_active
        mock_cbreak.assert_called_once()

        tc.stop()
        assert not tc.is_active
        mock_setattr.assert_called_once_with(0, mock_setattr.call_args[0][1], dummy_attrs)

        # Cycle 2 - Ensure _orig_term was not overwritten by cbreak mode
        tc.start()
        assert tc.is_active
        tc.stop()
        assert not tc.is_active


def test_worker_wait_loop_multiple_cycles():
    """Verify that a worker thread waiting for handback correctly blocks on repeated cycles."""
    import time
    wid = 77
    _takeover_events[wid] = threading.Event()
    _handback_events[wid] = threading.Event()
    with _worker_state_lock:
        _worker_state[wid] = {"status": "applying"}

    stop_event = threading.Event()

    def simulate_worker_wait():
        hb_event = _handback_events.get(wid)
        with _worker_state_lock:
            ws_check = _worker_state.get(wid)
            already_resumed = ws_check and ws_check.get("status") == "applying"
        if hb_event and not already_resumed:
            hb_event.clear()

        while not stop_event.is_set():
            with _worker_state_lock:
                ws = _worker_state.get(wid)
                if ws and ws.get("status") == "applying":
                    break
            if hb_event and hb_event.is_set():
                break
            if hb_event and hb_event.wait(timeout=0.05):
                break
        if hb_event:
            hb_event.clear()

    for cycle in range(1, 4):
        # 1. Takeover triggered
        trigger_takeover(wid)
        worker_resumed = threading.Event()

        def worker_runner():
            simulate_worker_wait()
            worker_resumed.set()

        t = threading.Thread(target=worker_runner)
        t.start()

        # Ensure worker is indeed waiting (blocked) and has not prematurely resumed
        time.sleep(0.08)
        assert not worker_resumed.is_set(), f"Cycle {cycle}: Worker should be blocked waiting for handback!"

        # 2. Handback triggered
        trigger_handback(wid, instructions=f"Resume cycle {cycle}")

        # Worker should unblock promptly
        t.join(timeout=1.0)
        assert worker_resumed.is_set(), f"Cycle {cycle}: Worker should have unblocked after handback!"

    # Cleanup
    _takeover_events.pop(wid, None)
    _handback_events.pop(wid, None)
    with _worker_state_lock:
        _worker_state.pop(wid, None)


def test_orchestrator_imports_get_state():
    """Ensure get_state is accessible in orchestrator module."""
    import applypilot.apply.orchestrator as orch
    assert hasattr(orch, "get_state")


