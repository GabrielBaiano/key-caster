from collections import deque
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel


class KeyDisplayer(QLabel):
    def __init__(self, parent=None, max_keys=5, font_size=32):
        super().__init__(parent)
        self.max_keys = max_keys
        self._keys = deque(maxlen=max_keys)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            f"color: #ffffff; font-size: {font_size}px; font-weight: normal; "
            "font-family: -apple-system, BlinkMacSystemFont, 'DejaVu Sans', 'FiraCode Nerd Font', 'Segoe UI', Roboto, sans-serif; "
            "background: transparent;"
        )

    def add_key(self, key):
        self._keys.append(key)
        self.setText("".join(self._keys))

    def clear_keys(self):
        self._keys.clear()
        self.setText("")


