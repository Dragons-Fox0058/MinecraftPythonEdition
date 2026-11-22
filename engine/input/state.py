"""Backend-independent keyboard and mouse state tracking."""
from __future__ import annotations


class InputState:
    """Tracks held and edge-triggered input without depending on a window library."""

    def __init__(self):
        self._keys: set[int | str] = set()
        self._buttons: set[int] = set()
        self._pressed_keys: set[int | str] = set()
        self._released_keys: set[int | str] = set()
        self._pressed_buttons: set[int] = set()
        self._released_buttons: set[int] = set()
        self.mouse_x = 0.0
        self.mouse_y = 0.0
        self.mouse_dx = 0.0
        self.mouse_dy = 0.0
        self.scroll_x = 0.0
        self.scroll_y = 0.0
        self.focused = True

    def begin_frame(self) -> None:
        self._pressed_keys.clear()
        self._released_keys.clear()
        self._pressed_buttons.clear()
        self._released_buttons.clear()
        self.mouse_dx = self.mouse_dy = 0.0
        self.scroll_x = self.scroll_y = 0.0

    def key_down(self, key: int | str) -> None:
        if key not in self._keys:
            self._pressed_keys.add(key)
        self._keys.add(key)

    def key_up(self, key: int | str) -> None:
        if key in self._keys:
            self._keys.remove(key)
            self._released_keys.add(key)

    def button_down(self, button: int) -> None:
        if isinstance(button, bool) or not isinstance(button, int) or button < 0:
            raise ValueError("mouse button must be a non-negative integer")
        if button not in self._buttons:
            self._pressed_buttons.add(button)
        self._buttons.add(button)

    def button_up(self, button: int) -> None:
        if button in self._buttons:
            self._buttons.remove(button)
            self._released_buttons.add(button)

    def mouse_move(self, x: float, y: float) -> None:
        x, y = float(x), float(y)
        self.mouse_dx += x - self.mouse_x
        self.mouse_dy += y - self.mouse_y
        self.mouse_x, self.mouse_y = x, y

    def mouse_scroll(self, x: float, y: float) -> None:
        self.scroll_x += float(x)
        self.scroll_y += float(y)

    def set_focus(self, focused: bool) -> None:
        if not isinstance(focused, bool):
            raise TypeError("focused must be bool")
        self.focused = focused
        if not focused:
            self._keys.clear()
            self._buttons.clear()

    def is_key_down(self, key) -> bool:
        return key in self._keys

    def was_key_pressed(self, key) -> bool:
        return key in self._pressed_keys

    def was_key_released(self, key) -> bool:
        return key in self._released_keys

    def is_button_down(self, button: int) -> bool:
        return button in self._buttons

    def was_button_pressed(self, button: int) -> bool:
        return button in self._pressed_buttons

    def was_button_released(self, button: int) -> bool:
        return button in self._released_buttons


__all__ = ["InputState"]
