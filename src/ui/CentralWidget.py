from typing import Optional
from PyQt5.QtWidgets import QFrame, QVBoxLayout


class CentralWidget(QFrame):
    def __init__(self, parent, key_dis, mod_dis, theme=None, bg_alpha: Optional[float] = None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setFixedSize(220, 100)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

        self.layout.addWidget(key_dis, 68)
        self.layout.addWidget(mod_dis, 32)

        if theme:
            self.apply_theme(theme, bg_alpha=bg_alpha)
        else:
            self.setStyleSheet("""
                QFrame#Card {
                    background-color: #000000;
                    border: 1px solid #1f1f22;
                    border-radius: 14px;
                }
            """)

    def apply_theme(self, theme, bg_alpha: Optional[float] = None):
        bg = (
            theme.get_effective_bg(bg_alpha)
            if hasattr(theme, "get_effective_bg")
            else getattr(theme, "bg_color", "#000000")
        )
        border_color = getattr(theme, "border_color", "#1f1f22")
        border_radius = getattr(theme, "border_radius", 14)
        self.setStyleSheet(f"""
            QFrame#Card {{
                background-color: {bg};
                border: 1px solid {border_color};
                border-radius: {border_radius}px;
            }}
        """)


