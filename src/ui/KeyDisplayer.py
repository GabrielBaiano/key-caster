from collections import deque
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel


class KeyDisplayer(QLabel):
    def __init__(self, parent=None, max_keys=5, font_size=32, theme=None):
        super().__init__(parent)
        self.max_keys = max_keys
        self.font_size = font_size
        self.theme = theme
        self._keys = deque(maxlen=max_keys)
        self._is_paused = False
        self.setAlignment(Qt.AlignCenter)

        f = self.font()
        f.setPixelSize(self.font_size)
        self.setFont(f)

        self._apply_normal_style()

    def content_width(self) -> int:
        text = self.text()
        if not text:
            return 0
        return self.fontMetrics().horizontalAdvance(text)

    def apply_theme(self, theme):
        self.theme = theme
        if self._is_paused:
            self._apply_paused_style()
        else:
            self._apply_normal_style()

    def _apply_normal_style(self):
        f = self.font()
        f.setPixelSize(self.font_size)
        self.setFont(f)
        text_color = getattr(self.theme, "text_color", "#ffffff") if self.theme else "#ffffff"
        font_family = (
            getattr(self.theme, "font_family", None)
            or "-apple-system, BlinkMacSystemFont, 'DejaVu Sans', 'FiraCode Nerd Font', 'Segoe UI', Roboto, sans-serif"
        )
        self.setStyleSheet(
            f"color: {text_color}; font-size: {self.font_size}px; font-weight: normal; "
            f"font-family: {font_family}; "
            "background: transparent;"
        )

    def _apply_paused_style(self):
        paused_font_size = max(14, int(self.font_size * 0.55))
        pause_color = getattr(self.theme, "pause_color", "#f59e0b") if self.theme else "#f59e0b"
        font_family = (
            getattr(self.theme, "font_family", None)
            or "-apple-system, BlinkMacSystemFont, 'DejaVu Sans', 'FiraCode Nerd Font', 'Segoe UI', Roboto, sans-serif"
        )
        self.setStyleSheet(
            f"color: {pause_color}; font-size: {paused_font_size}px; font-weight: bold; "
            "letter-spacing: 2px; "
            f"font-family: {font_family}; "
            "background: transparent;"
        )

    def set_paused(self, paused: bool):
        self._is_paused = paused
        self._keys.clear()
        if paused:
            self._apply_paused_style()
            self.setText("⏸ PAUSED")
        else:
            self._apply_normal_style()
            self.setText("")

    def add_key(self, key):
        if self._is_paused:
            return
        self._keys.append(key)
        self.setText("".join(self._keys))

    def clear_keys(self):
        self._keys.clear()
        if not self._is_paused:
            self.setText("")


