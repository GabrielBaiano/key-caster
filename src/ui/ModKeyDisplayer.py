from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel


class ModKeyDisplayer(QFrame):
    modifier_icons = {
        "shift": "⇧",
        "ctrl": "⌃",
        "alt": "⌥",
        "windows": "⌘",
    }

    def __init__(self, parent=None, theme=None):
        super().__init__(parent)
        self.setObjectName("ModBar")
        self.setFixedHeight(32)
        self.theme = theme
        self._active_mods = set()

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
            self.modifiers[key] = lbl
            self.layout.addWidget(lbl)

        self._update_styles()

    def _get_colors(self):
        border = getattr(self.theme, "border_color", "#1f1f22") if self.theme else "#1f1f22"
        active = getattr(self.theme, "mod_active_color", "#ffffff") if self.theme else "#ffffff"
        inactive = getattr(self.theme, "mod_inactive_color", "#555555") if self.theme else "#555555"
        font = (
            getattr(self.theme, "font_family", None)
            or '-apple-system, BlinkMacSystemFont, "DejaVu Sans", "Noto Sans", "Segoe UI", sans-serif'
        )
        return border, active, inactive, font

    def _update_styles(self):
        border, active, inactive, font = self._get_colors()
        self.setStyleSheet(f"""
            QFrame#ModBar {{
                border-top: 1px solid {border};
                background: transparent;
            }}
        """)
        keys = list(self.modifier_icons.keys())
        for i, key in enumerate(keys):
            lbl = self.modifiers[key]
            border_right = f"border-right: 1px solid {border};" if i < len(keys) - 1 else ""
            lbl.setStyleSheet(f"""
                font-size: 17px;
                font-family: {font};
                background: transparent;
                {border_right}
            """)
        self._render_icons()

    def _render_icons(self):
        _, active, inactive, _ = self._get_colors()
        for key, icon in self.modifier_icons.items():
            color = active if key in self._active_mods else inactive
            self.modifiers[key].setText(f'<font color="{color}">{icon}</font>')

    def apply_theme(self, theme):
        self.theme = theme
        self._update_styles()

    @staticmethod
    def normalize_modifier(mod: str):
        if not mod:
            return None
        m = str(mod).lower().strip()
        if "ctrl" in m or "control" in m:
            return "ctrl"
        if "shift" in m:
            return "shift"
        if "alt" in m:
            return "alt"
        if "win" in m or "super" in m or "meta" in m:
            return "windows"
        return None

    def set_modifiers(self, modifiers):
        self._active_mods = set()
        for mod in modifiers:
            norm = self.normalize_modifier(mod)
            if norm:
                self._active_mods.add(norm)
        self._render_icons()

    def reset_modifiers(self, reset_modifiers):
        for mod in reset_modifiers:
            norm = self.normalize_modifier(mod)
            if norm:
                self._active_mods.discard(norm)
        self._render_icons()

    def reset_all(self):
        self._active_mods.clear()
        self._render_icons()


