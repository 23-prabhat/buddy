from __future__ import annotations

import asyncio
import traceback

from PySide6.QtCore import QObject, QRect, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QIcon,
    QKeyEvent,
    QPainter,
    QPixmap,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QRubberBand,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from bro.apps.desktop.hotkeys import HotkeyManager
from bro.apps.desktop.terminal.session import TerminalSession
from bro.apps.desktop.terminal.styles import TERMINAL_QSS
from bro.core.commands import build_registry
from bro.core.configuration import get_settings


class PromptLine(QLineEdit):
    history_up = Signal()
    history_down = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Up:
            self.history_up.emit()
            return
        if event.key() == Qt.Key.Key_Down:
            self.history_down.emit()
            return
        super().keyPressEvent(event)


class RegionSelector(QWidget):
    """Fullscreen overlay showing a frozen screenshot; user drags a rectangle.

    Emits ``region_selected`` with screen-pixel coords (x, y, w, h) and ``cancelled``.
    """

    region_selected = Signal(int, int, int, int)
    cancelled = Signal()

    def __init__(self, screenshot_png: bytes, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._pixmap = QPixmap()
        self._pixmap.loadFromData(screenshot_png)
        self._origin = None
        self._rubber: QRubberBand | None = None
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self._pixmap)
        # Dim the unselected area with a deep-plum wash so the magenta rubber
        # band stands out against the retro-purple palette instead of dropping
        # to near-black. ~55% translucent plum keeps the screenshot legible.
        painter.fillRect(self.rect(), QColor(15, 10, 30, 140))

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._origin = event.position().toPoint()
        if self._rubber is None:
            self._rubber = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self._rubber.setGeometry(QRect(self._origin, self._origin))
        self._rubber.show()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._origin is None or self._rubber is None:
            return
        self._rubber.setGeometry(QRect(self._origin, event.position().toPoint()).normalized())

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton or self._origin is None:
            return
        rect = QRect(self._origin, event.position().toPoint()).normalized()
        self._origin = None
        if self._rubber:
            self._rubber.hide()
        if rect.width() < 8 or rect.height() < 8:
            self.cancelled.emit()
            self.close()
            return
        # Map widget coords to screen coords (fullscreen on primary screen).
        top_left = self.mapToGlobal(rect.topLeft())
        self.region_selected.emit(top_left.x(), top_left.y(), rect.width(), rect.height())
        self.close()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()
            return
        super().keyPressEvent(event)


class AsyncWorker(QObject):
    line = Signal(str, str)
    stream_start = Signal()
    stream_chunk = Signal(str)
    stream_end = Signal()
    status = Signal()
    finished_ok = Signal()
    failed = Signal(str)

    def __init__(self, session: TerminalSession) -> None:
        super().__init__()
        self._session = session
        self._line: str = ""

    def set_line(self, line: str) -> None:
        self._line = line

    @Slot()
    def run(self) -> None:
        try:
            self._session._on_line = lambda t, s: self.line.emit(t, s)
            self._session._on_stream_start = lambda: self.stream_start.emit()
            self._session._on_stream_chunk = lambda c: self.stream_chunk.emit(c)
            self._session._on_stream_end = lambda: self.stream_end.emit()
            self._session._on_status = lambda: self.status.emit()
            asyncio.run(self._session.handle_line(self._line))
            self.finished_ok.emit()
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"{exc}\n{traceback.format_exc()}")


class MainWindow(QMainWindow):
    hotkey_command = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ai-assistant")
        self.resize(960, 640)
        self.setStyleSheet(TERMINAL_QSS)

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QHBoxLayout()
        self.title = QLabel("AI ASSISTANT")
        self.title.setObjectName("TitleBar")
        self.ready = QLabel("● READY")
        self.ready.setObjectName("TitleBar")
        self.ready.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Mode-switch buttons (Chat / Screen / Meeting).Exclusive QButtonGroup
        # keeps exactly one checked at a time; the active one is highlighted by
        # QSS (#ModeButton:checked) so the user can see which mode is live.
        self.mode_buttons: dict[str, QPushButton] = {}
        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)
        for mode, label in (("general", "Chat"), ("screen", "Screen"), ("meeting", "Meeting")):
            btn = QPushButton(label)
            btn.setObjectName("ModeButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _checked=False, m=mode: self._set_mode_button(m))
            self._mode_group.addButton(btn)
            self.mode_buttons[mode] = btn

        header.addWidget(self.title, 1)
        for mode in ("general", "screen", "meeting"):
            header.addWidget(self.mode_buttons[mode], 0)
        header.addWidget(self.ready, 0)
        header_w = QWidget()
        header_w.setLayout(header)
        header_w.setObjectName("TitleBar")
        layout.addWidget(header_w)

        self.output = QPlainTextEdit()
        self.output.setObjectName("Output")
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(8000)
        mono = QFont("monospace")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        mono.setPointSize(11)
        self.output.setFont(mono)
        layout.addWidget(self.output, 1)

        self.prompt = PromptLine()
        self.prompt.setObjectName("Prompt")
        self.prompt.setFont(mono)
        self.prompt.setPlaceholderText('Type a command or ask "your question"…')
        self.prompt.returnPressed.connect(self._on_submit)
        self.prompt.history_up.connect(lambda: self._history_nav(-1))
        self.prompt.history_down.connect(lambda: self._history_nav(1))
        layout.addWidget(self.prompt)

        self.status = QLabel()
        self.status.setObjectName("StatusBar")
        layout.addWidget(self.status)

        self._cmd_history: list[str] = []
        self._hist_idx = 0
        self._thread: QThread | None = None
        self._worker: AsyncWorker | None = None
        self._busy = False
        self._hotkeys = HotkeyManager()
        self._hiding_for_capture = False
        self._region_selector: RegionSelector | None = None
        self._pending_select_line: str | None = None

        self.session = TerminalSession(
            registry=build_registry(),
            on_line=self._append_styled,
            on_clear=self.output.clear,
            on_exit=self.close,
            on_status=self._refresh_status,
            on_stream_start=self._stream_start,
            on_stream_chunk=self._stream_chunk,
            on_stream_end=self._stream_end,
        )

        self.hotkey_command.connect(self._run_external_command)
        self._setup_tray()
        self._setup_hotkeys()

        self._print_banner()
        self._refresh_status()
        self._sync_mode_buttons(self.session.get_mode())
        self.prompt.setFocus()

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None
            return
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(
            self.windowIcon() if not self.windowIcon().isNull() else QIcon.fromTheme("utilities-terminal")
        )
        menu = QMenu()
        act_show = QAction("Show / Hide", self)
        act_show.triggered.connect(self._toggle_visible)
        act_screen = QAction("Screen analyze", self)
        act_screen.triggered.connect(lambda: self._run_external_command("screen analyze"))
        act_meeting = QAction("Toggle meeting", self)
        act_meeting.triggered.connect(self._toggle_meeting)
        act_quit = QAction("Quit", self)
        act_quit.triggered.connect(QApplication.instance().quit)
        menu.addAction(act_show)
        menu.addAction(act_screen)
        menu.addAction(act_meeting)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.setToolTip("ai-assistant")
        self.tray.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_visible()

    def _toggle_visible(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()
            self.prompt.setFocus()

    def _setup_hotkeys(self) -> None:
        settings = get_settings()
        if not settings.hotkeys_enabled:
            return

        def fire(cmd: str) -> None:
            self.hotkey_command.emit(cmd)

        ok = self._hotkeys.start(
            on_screen=lambda: fire("screen analyze"),
            on_meeting_toggle=lambda: fire("__toggle_meeting__"),
        )
        if ok:
            self._append_styled(
                "[HOTKEYS] Ctrl+Shift+S screen · Ctrl+Shift+M meeting",
                "muted",
            )
        elif self._hotkeys.error:
            self._append_styled(
                f"[HOTKEYS] Disabled ({self._hotkeys.error}). Use terminal commands.",
                "muted",
            )

    def _toggle_meeting(self) -> None:
        if self.session.meeting_on:
            self._run_external_command("meeting stop")
        else:
            self._run_external_command("meeting start")

    def _run_external_command(self, line: str) -> None:
        if line == "__toggle_meeting__":
            self._toggle_meeting()
            return
        if self._busy:
            self._append_styled("[WARN] Busy — hotkey ignored.", "warn")
            return
        self._append_styled(f"$ {line}", "prompt")
        low = line.strip().split()[0].lower() if line.strip() else ""
        if low in {
            "help",
            "settings",
            "model",
            "mode",
            "context",
            "history",
            "clear",
            "apikey",
            "provider",
        }:
            asyncio.run(self.session.handle_line(line))
            self._refresh_status()
            return
        if line.strip().lower() == "meeting stop":
            self._start_async_command(line)
            return
        if low == "meeting" and "start" not in line.lower() and "inject" not in line.lower():
            asyncio.run(self.session.handle_line(line))
            self._refresh_status()
            return
        screen_kind = self._screen_command_kind(line)
        if screen_kind == "select":
            self._begin_screen_select(line)
            return
        if screen_kind == "capture":
            self._begin_hidden_capture(line)
            return
        self._start_async_command(line)

    def _print_banner(self) -> None:
        self._append_styled("Welcome to AI Assistant", "system")
        self._append_styled(
            "Pick a mode above (Chat / Screen / Meeting), then type a question "
            "or 'help' for commands.",
            "muted",
        )
        self._append_styled("", "info")

    def _refresh_status(self) -> None:
        flags = self.session.status_flags()
        if self._busy and flags["AI"] == "READY":
            flags["AI"] = "BUSY"
        self.status.setText(
            f"MEETING: {flags['MEETING']}   "
            f"SCREEN: {flags['SCREEN']}   AI: {flags['AI']}   MODE: {flags['MODE']}"
        )
        label = flags["AI"]
        self.ready.setText(f"● {label}")
        # Overlay-spinner purple when active, calm lavender-magenta when idle,
        # so the LED matches the retro-purple palette instead of leftover warm
        # amber/teal from the cream theme.
        if label in ("BUSY", "LISTENING"):
            self.ready.setStyleSheet("color: #e040fb;")
        else:
            self.ready.setStyleSheet("color: #b388ff;")
        # Keep the active mode button in sync with whatever last touched the
        # session mode (a 'mode <name>' command, a meeting start/stop, hotkey…)
        self._sync_mode_buttons(self.session.get_mode())

    def _sync_mode_buttons(self, mode: str) -> None:
        """Check the header button that matches the live session mode.

        Modes outside the three buttons (coding / study / meeting+screen) are
        projected onto their nearest button so something is always highlighted:
          * meeting+screen -> Meeting (meeting active; screen is contextual)
          * coding / study / general -> Chat
        """
        if mode == "meeting" or mode == "meeting+screen":
            target = "meeting"
        elif mode == "screen":
            target = "screen"
        else:
            target = "general"
        btn = self.mode_buttons.get(target)
        if btn is not None and not btn.isChecked():
            btn.setChecked(True)

    def _set_mode_button(self, mode: str) -> None:
        """Run when the user clicks Chat / Screen / Meeting in the title bar.

        The buttons themselves are checkable, so a click both toggles the visual
        state and lands here. We treat them as one-shot mode switches (not
        toggles for the active mode): meeting button also starts/stops the live
        meeting so the rest of the app (status, auto-answer, transcript) moves
        with it instead of the mode flag drifting away from meeting_on.
        """
        if self._busy:
            self._append_styled(
                "[WARN] Wait for the current command to finish.", "warn"
            )
            # The click already flipped the checked state — restore it.
            self._sync_mode_buttons(self.session.get_mode())
            return

        if mode == "meeting":
            # Idempotent: clicking Meeting always lands in "meeting + live on",
            # regardless of whether the live meeting was already running.
            if not self.session.meeting_on:
                asyncio.run(self.session.run_meeting_start())
            # ``run_meeting_start`` only flips ``general -> meeting`` and keeps
            # the current mode otherwise (so the legacy ``meeting start``
            # command can build a ``meeting+screen`` combo). The header
            # button is a clean three-way switch, so force the visible mode
            # to "meeting" regardless of where we came from.
            if self.session.get_mode() != "meeting":
                self.session.set_mode("meeting")
        else:
            # Chat / Screen: leave any meeting so the status reflects reality
            # before flipping the mode flag.
            if self.session.meeting_on:
                asyncio.run(self.session.run_meeting_stop())
            self.session.set_mode(mode)
            self._append_styled(f"[MODE] {mode}", "system")
        self._refresh_status()

    def _color_for(self, style: str) -> QColor:
        # Retro-purple palette: body on plum, accents in violet/magenta, with a
        # warm amber for warnings so critical messages stay legible on purple.
        return {
            "info": QColor("#e8dfff"),
            "system": QColor("#b9a0ff"),
            "muted": QColor("#a99dc4"),
            "error": QColor("#ff6b9d"),
            "warn": QColor("#ffb74d"),
            "answer": QColor("#9eff8c"),
            "prompt": QColor("#c09bff"),
        }.get(style, QColor("#e8dfff"))

    def _append_styled(self, text: str, style: str = "info") -> None:
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(self._color_for(style))
        cursor.setCharFormat(fmt)
        if text:
            cursor.insertText(text)
        cursor.insertText("\n")
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def _stream_start(self) -> None:
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(self._color_for("answer"))
        cursor.setCharFormat(fmt)
        cursor.insertText("> ")
        self.output.setTextCursor(cursor)

    def _stream_chunk(self, chunk: str) -> None:
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(self._color_for("answer"))
        cursor.setCharFormat(fmt)
        cursor.insertText(chunk)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def _stream_end(self) -> None:
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText("\n")
        self.output.setTextCursor(cursor)

    def _on_submit(self) -> None:
        if self._busy:
            self._append_styled("[WARN] Wait for the current command to finish.", "warn")
            return
        line = self.prompt.text()
        self.prompt.clear()
        text_strip = line.strip()
        if not text_strip:
            return
        self._cmd_history.append(line)
        self._hist_idx = len(self._cmd_history)
        self._append_styled(f"$ {line}", "prompt")

        low = text_strip.lstrip("$").strip().split()[0].lower()
        sync_cmds = {
            "help",
            "?",
            "clear",
            "history",
            "context",
            "settings",
            "model",
            "mode",
            "exit",
            "quit",
            "q",
            "rag",
            "apikey",
            "key",
            "api-key",
            "provider",
            "providers",
        }
        if low == "meeting" and (
            len(text_strip.split()) == 1 or text_strip.split()[1].lower() == "status"
        ):
            asyncio.run(self.session.handle_line(line))
            self._refresh_status()
            return
        if low in sync_cmds and not (
            low == "rag" and len(text_strip.split()) > 1 and text_strip.split()[1].lower() == "add"
        ):
            asyncio.run(self.session.handle_line(line))
            self._refresh_status()
            return

        # Screen commands get Gemini-style capture handling (hide app / region select)
        screen_kind = self._screen_command_kind(text_strip)
        if screen_kind == "select":
            self._begin_screen_select(line)
            return
        if screen_kind == "capture":
            self._begin_hidden_capture(line)
            return

        self._start_async_command(line)

    @staticmethod
    def _screen_command_kind(text: str) -> str | None:
        tokens = text.lstrip("$").strip().split()
        if len(tokens) < 2 or tokens[0].lower() != "screen":
            return None
        sub = tokens[1].lower()
        if sub in ("select", "region", "snip"):
            return "select"
        if sub in ("read", "analyze", "analyse"):
            return "capture"
        return None

    def _begin_hidden_capture(self, line: str) -> None:
        """Hide this window, let the OS repaint, then run the capture command."""
        self._hiding_for_capture = True
        self.hide()
        QTimer.singleShot(350, lambda: self._start_async_command(line))

    def _begin_screen_select(self, line: str) -> None:
        """Capture a full screenshot (app hidden), show a region selector, then run."""
        self._pending_select_line = line
        self.hide()
        QTimer.singleShot(350, self._capture_and_show_region_selector)

    def _capture_and_show_region_selector(self) -> None:
        try:
            monitor = self.session.settings.screen_monitor
            shot = self.session._platform.capture_screen(monitor=monitor)
        except Exception as exc:  # noqa: BLE001
            self.show()
            self._append_styled(f"[ERROR] Screen capture failed: {exc}", "error")
            return
        self._region_selector = RegionSelector(shot.png_bytes)
        self._region_selector.region_selected.connect(self._on_region_selected)
        self._region_selector.cancelled.connect(self._on_region_cancelled)
        # Keep the screenshot for cropping after the user selects.
        self._select_screenshot = shot
        self._region_selector.showFullScreen()

    def _on_region_selected(self, x: int, y: int, w: int, h: int) -> None:
        shot = getattr(self, "_select_screenshot", None)
        self._region_selector = None
        line = self._pending_select_line or "screen select"
        self._pending_select_line = None
        # Stash state for the session to consume (crop from the frozen shot).
        self.session._pending_screenshot = shot
        self.session._pending_region = (x, y, w, h)
        self._hiding_for_capture = True  # stay hidden during analyze
        self._start_async_command(line)

    def _on_region_cancelled(self) -> None:
        self._region_selector = None
        self._pending_select_line = None
        if hasattr(self, "_select_screenshot"):
            del self._select_screenshot
        self.show()
        self._append_styled("[SCREEN] Region selection cancelled.", "muted")

    def _start_async_command(self, line: str) -> None:
        self._busy = True
        self.prompt.setEnabled(False)
        self._refresh_status()

        self._thread = QThread(self)
        self._worker = AsyncWorker(self.session)
        self._worker.set_line(line)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.line.connect(self._append_styled)
        self._worker.stream_start.connect(self._stream_start)
        self._worker.stream_chunk.connect(self._stream_chunk)
        self._worker.stream_end.connect(self._stream_end)
        self._worker.status.connect(self._refresh_status)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.finished_ok.connect(self._on_worker_done)
        self._worker.finished_ok.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_worker)
        self._thread.start()

    def _on_worker_failed(self, msg: str) -> None:
        self._append_styled(f"[ERROR] {msg}", "error")
        self._on_worker_done()

    def _on_worker_done(self) -> None:
        self._busy = False
        self.prompt.setEnabled(True)
        self.prompt.setFocus()
        self._refresh_status()
        if self._hiding_for_capture:
            self._hiding_for_capture = False
            self.show()
            self.raise_()
            self.activateWindow()
            self.prompt.setFocus()

    def _clear_worker(self) -> None:
        self._thread = None
        self._worker = None

    def _history_nav(self, delta: int) -> None:
        if not self._cmd_history:
            return
        self._hist_idx = max(0, min(len(self._cmd_history), self._hist_idx + delta))
        if self._hist_idx == len(self._cmd_history):
            self.prompt.setText("")
        else:
            self.prompt.setText(self._cmd_history[self._hist_idx])

    def closeEvent(self, event) -> None:  # noqa: N802
        self._hotkeys.stop()
        try:
            asyncio.run(self.session._shutdown())
        except Exception:  # noqa: BLE001
            pass
        if self.tray:
            self.tray.hide()
        super().closeEvent(event)
