from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel


class ModKeyDisplayer(QFrame):
    modifier_icons = {
        "shift": "󰘶",
        "ctrl": "󰘴",
        "alt": "⌥",
        "windows": "⌘",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ModBar")
        self.setFixedHeight(32)
        self.setStyleSheet("""
            QFrame#ModBar {
                border-top: 1px solid #1f1f22;
                background: transparent;
            }
        """)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

        self.modifiers = {}
        keys = list(self.modifier_icons.keys())
        for i, key in enumerate(keys):
            icon = self.modifier_icons[key]
            lbl = QLabel(text=f'<font color="#555555">{icon}</font>')
            lbl.setAlignment(Qt.AlignCenter)
            border_right = "border-right: 1px solid #1f1f22;" if i < len(keys) - 1 else ""
            lbl.setStyleSheet(f"""
                font-size: 17px;
                background: transparent;
                {border_right}
            """)
            self.modifiers[key] = lbl
            self.layout.addWidget(lbl)

    def set_modifiers(self, modifiers):
        for key, icon in self.modifier_icons.items():
            self.modifiers[key].setText(f'<font color="#555555">{icon}</font>')
        for mod in modifiers:
            if mod in self.modifiers:
                self.modifiers[mod].setText(
                    f'<font color="#ffffff">{self.modifier_icons[mod]}</font>'
                )

    def reset_modifiers(self, reset_modifiers):
        for mod in reset_modifiers:
            if mod in self.modifiers:
                self.modifiers[mod].setText(
                    f'<font color="#555555">{self.modifier_icons[mod]}</font>'
                )

    def reset_all(self):
        for key, icon in self.modifier_icons.items():
            self.modifiers[key].setText(f'<font color="#555555">{icon}</font>')


