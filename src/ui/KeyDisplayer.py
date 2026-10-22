from collections import deque
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel


class KeyDisplayer(QLabel):
    def __init__(self, parent=None, max_keys=5, font_size=32):
        super().__init__(parent)
        self.max_keys = max_keys
        self.font_size = font_size
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

    def _apply_normal_style(self):
        f = self.font()
        f.setPixelSize(self.font_size)
        self.setFont(f)
        self.setStyleSheet(
            f"color: #ffffff; font-size: {self.font_size}px; font-weight: normal; "
            "font-family: -apple-system, BlinkMacSystemFont, 'DejaVu Sans', 'FiraCode Nerd Font', 'Segoe UI', Roboto, sans-serif; "
            "background: transparent;"
        )

    def _apply_paused_style(self):
        paused_font_size = max(14, int(self.font_size * 0.55))
        self.setStyleSheet(
            f"color: #f59e0b; font-size: {paused_font_size}px; font-weight: bold; "
            "letter-spacing: 2px; "
            "font-family: -apple-system, BlinkMacSystemFont, 'DejaVu Sans', 'FiraCode Nerd Font', 'Segoe UI', Roboto, sans-serif; "
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


