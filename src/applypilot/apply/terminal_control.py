"""Terminal control for interactive pause / resume (human takeover) during apply runs."""

import atexit
import select
import sys
import threading
from rich.console import Console

try:
    import termios
    import tty
    _HAS_TERMIOS = True
except ImportError:
    _HAS_TERMIOS = False


class TerminalController:
    """Manages terminal raw/cbreak mode and non-blocking keyboard controls."""

    def __init__(self) -> None:
        self._is_tty = sys.stdin.isatty() if hasattr(sys.stdin, "isatty") else False
        self._orig_term = None
        self._old_term = None
        self._in_cbreak = False
        self._lock = threading.Lock()
        if self._is_tty and _HAS_TERMIOS:
            try:
                self._orig_term = termios.tcgetattr(sys.stdin.fileno())
            except Exception:
                pass

    @property
    def is_active(self) -> bool:
        """Return True if cbreak mode is active."""
        return self._in_cbreak

    def start(self) -> None:
        """Enable non-blocking single-key input if running in an interactive TTY."""
        if not self._is_tty or not _HAS_TERMIOS:
            return
        with self._lock:
            if self._in_cbreak:
                return
            try:
                if self._orig_term is None:
                    self._orig_term = termios.tcgetattr(sys.stdin.fileno())
                self._old_term = self._orig_term
                tty.setcbreak(sys.stdin.fileno())
                self._in_cbreak = True
                atexit.register(self.stop)
            except Exception:
                self._in_cbreak = False

    def stop(self) -> None:
        """Restore original canonical terminal settings."""
        if not self._is_tty or not _HAS_TERMIOS:
            return
        with self._lock:
            if not self._in_cbreak:
                return
            try:
                restore_attr = self._orig_term or self._old_term
                if restore_attr is not None:
                    termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, restore_attr)
            except Exception:
                pass
            finally:
                self._in_cbreak = False

    def flush(self) -> None:
        """Flush unread characters from terminal input buffer."""
        if not self._is_tty or not _HAS_TERMIOS:
            return
        try:
            termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
        except Exception:
            pass

    def check_key(self, timeout: float = 0.0) -> str | None:
        """Check if a keypress or line is ready on stdin without blocking.

        Returns:
            The key character if pressed, or None.
        """
        if not self._is_tty:
            return None
        try:
            r, _, _ = select.select([sys.stdin], [], [], timeout)
            if not r:
                return None
            if self._in_cbreak:
                try:
                    import os
                    raw = os.read(sys.stdin.fileno(), 1)
                    return raw.decode("utf-8", errors="ignore")
                except Exception:
                    ch = sys.stdin.read(1)
                    return ch
            line = sys.stdin.readline()
            return line.strip()[:1] if line else None
        except Exception:
            return None

    def prompt_takeover(self, console: Console, worker_id: int) -> str | None:
        """Present the takeover modal in the terminal and wait for user to resume.

        Temporarily restores normal canonical terminal mode so the user can
        type characters and instructions cleanly.
        """
        was_cbreak = self._in_cbreak
        if was_cbreak:
            self.stop()

        # Flush any stale keystrokes or newlines typed before the prompt appeared
        if self._is_tty and _HAS_TERMIOS:
            try:
                termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
            except Exception:
                pass

        console.print()
        console.rule("[bold yellow]⏸  PAUSED: Human Takeover Mode[/bold yellow]")
        console.print(
            "\n  [bold]Chrome browser is focused and ready for you.[/bold]\n"
            "  Switch to the browser window to fill fields, solve CAPTCHAs, or log in.\n\n"
            "  [bold cyan]When you are ready to let the agent resume:[/bold cyan]\n"
            "    • Press [bold green][Enter][/bold green] or [bold green][p][/bold green] to continue form filling\n"
            "    • Or type instructions (e.g. [dim]'logged in, on review page'[/dim]) and press [bold green][Enter][/bold green]\n"
        )
        console.rule()

        try:
            user_input = console.input("  [bold green]Resume agent > [/bold green]")
        except (EOFError, KeyboardInterrupt):
            user_input = ""

        clean = user_input.strip()
        instructions = None
        if clean and clean.lower() not in ("p", "play", "resume", "continue"):
            instructions = clean

        console.print("[green]✔ Resuming agent... Chrome control handed back.[/green]\n")

        # Flush again before re-enabling cbreak mode so trailing newlines don't trigger pause
        if self._is_tty and _HAS_TERMIOS:
            try:
                termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
            except Exception:
                pass

        if was_cbreak:
            self.start()

        return instructions

    def prompt_review_ready(self, console: Console, job: dict, worker_id: int = 0) -> str:
        """Prompt user when the application form is completely filled and awaiting submission.

        Returns:
            "applied" if user pressed Enter / confirmed submission.
            "skip" if user typed 's' or 'skip'.
            Or user instruction string to relaunch agent.
        """
        was_cbreak = self._in_cbreak
        if was_cbreak:
            self.stop()

        if self._is_tty and _HAS_TERMIOS:
            try:
                termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
            except Exception:
                pass

        title = job.get("title") or "Job Application"
        company = job.get("site") or job.get("company") or "Unknown"
        app_url = job.get("application_url") or job.get("url") or ""

        console.print()
        console.rule("[bold green]✔ APPLICATION FORM FULLY FILLED — READY FOR SUBMISSION[/bold green]")
        console.print(
            f"\n  [bold cyan]Job:[/bold cyan]     {title}\n"
            f"  [bold cyan]Company:[/bold cyan] {company}\n"
            f"  [bold cyan]URL:[/bold cyan]     {app_url}\n\n"
            "  [bold]The agent has completed filling out the entire application form:[/bold]\n"
            "    • Personal & contact details entered\n"
            "    • Work authorization details provided\n"
            "    • Tailored resume & documents uploaded\n"
            "    • Screening questions answered & required checkboxes checked\n"
            "    • Navigated to the final review/submit step\n\n"
            "  [bold yellow]👉 Chrome is open and focused on the final review/submit page.[/bold yellow]\n"
            "  [bold yellow]👉 Please review the filled form in Chrome and take the final step to submit.[/bold yellow]\n\n"
            "  [bold]Options:[/bold]\n"
            "    • Press [bold green][Enter][/bold green] after you submit in Chrome (records as applied)\n"
            "    • Type [bold red]'skip'[/bold red] or [bold red]'s'[/bold red] to skip without marking as applied\n"
            "    • Or type instructions (e.g. [dim]'change salary to 60000'[/dim]) and press [bold green][Enter][/bold green]\n"
        )
        console.rule()

        try:
            user_input = console.input("  [bold green]Final step > [/bold green]")
        except (EOFError, KeyboardInterrupt):
            user_input = ""

        clean = user_input.strip()
        result = "applied"
        if clean.lower() in ("s", "skip", "cancel", "abort"):
            result = "skip"
        elif clean and clean.lower() not in ("applied", "done", "submit", "submitted", "yes", "y"):
            result = clean

        if self._is_tty and _HAS_TERMIOS:
            try:
                termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
            except Exception:
                pass

        if was_cbreak:
            self.start()

        return result
