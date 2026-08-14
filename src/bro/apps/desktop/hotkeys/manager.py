from __future__ import annotations

from collections.abc import Callable
from typing import Any


class HotkeyManager:
    """
    Optional global hotkeys via pynput.
    Gracefully no-ops if pynput/evdev unavailable.
    """

    def __init__(self) -> None:
        self._listener: Any = None
        self._enabled = False
        self._error: str | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def error(self) -> str | None:
        return self._error

    def start(
        self,
        on_screen: Callable[[], None] | None = None,
        on_meeting_toggle: Callable[[], None] | None = None,
        on_listen: Callable[[], None] | None = None,
    ) -> bool:
        try:
            from pynput import keyboard
        except Exception as exc:  # noqa: BLE001
            self._error = f"pynput unavailable: {exc}"
            self._enabled = False
            return False

        combos = {
            frozenset({keyboard.Key.ctrl, keyboard.Key.shift, keyboard.KeyCode.from_char("s")}): on_screen,
            frozenset({keyboard.Key.ctrl, keyboard.Key.shift, keyboard.KeyCode.from_char("m")}): on_meeting_toggle,
            frozenset({keyboard.Key.ctrl, keyboard.Key.shift, keyboard.KeyCode.from_char("v")}): on_listen,
        }
        current: set = set()

        def normalize(k):  # noqa: ANN001
            if hasattr(k, "char") and k.char:
                return keyboard.KeyCode.from_char(k.char.lower())
            return k

        def on_press(key):  # noqa: ANN001
            current.add(normalize(key))
            for combo, cb in combos.items():
                if cb and combo.issubset(current):
                    try:
                        cb()
                    except Exception:  # noqa: BLE001
                        pass

        def on_release(key):  # noqa: ANN001
            current.discard(normalize(key))

        try:
            self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self._listener.daemon = True
            self._listener.start()
            self._enabled = True
            self._error = None
            return True
        except Exception as exc:  # noqa: BLE001
            self._error = str(exc)
            self._enabled = False
            return False

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:  # noqa: BLE001
                pass
            self._listener = None
        self._enabled = False
