from __future__ import annotations

import asyncio
import traceback

from PySide6.QtCore import Qt, QThread, QObject, Signal, Slot
from PySide6.QtGui import QAction, QFont, QKeyEvent, QTextCharFormat, QTextCursor, QColor, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPlainTextEdit,
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
        header.addWidget(self.title, 1)
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
            on_listen=lambda: fire("listen"),
        )
        if ok:
            self._append_styled(
                "[HOTKEYS] Ctrl+Shift+S screen · Ctrl+Shift+M meeting · Ctrl+Shift+V listen",
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
        self._start_async_command(line)

    def _print_banner(self) -> None:
        self._append_styled("ai-assistant  ·  free Groq or your own API key", "system")
        self._append_styled(
            "apikey free | apikey set <key> | provider list | ask \"…\" | help",
            "muted",
        )
        try:
            self._append_styled(self.session.get_model_info(), "muted")
        except Exception:  # noqa: BLE001
            pass
        self._append_styled("", "info")

    def _refresh_status(self) -> None:
        flags = self.session.status_flags()
        if self._busy and flags["AI"] == "READY":
            flags["AI"] = "BUSY"
        self.status.setText(
            f"MIC: {flags['MIC']}   AUDIO: {flags['AUDIO']}   "
            f"SCREEN: {flags['SCREEN']}   AI: {flags['AI']}   MODE: {flags['MODE']}"
        )
        label = flags["AI"]
        self.ready.setText(f"● {label}")
        if label in ("BUSY", "LISTENING"):
            self.ready.setStyleSheet("color: #f0c674;")
        else:
            self.ready.setStyleSheet("color: #00ff9c;")

    def _color_for(self, style: str) -> QColor:
        return {
            "info": QColor("#d4d4d4"),
            "system": QColor("#7ec8e3"),
            "muted": QColor("#7a7a7a"),
            "error": QColor("#ff6b6b"),
            "warn": QColor("#f0c674"),
            "answer": QColor("#00ff9c"),
            "prompt": QColor("#c5c8c6"),
        }.get(style, QColor("#d4d4d4"))

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
            "stop",
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

        self._start_async_command(line)

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
