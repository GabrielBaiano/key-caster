"""
Theme configuration and styling engine for Key-caster.
Provides curated presets (Dark, Catppuccin, Tokyo Night, Nord, Dracula, Gruvbox, Light)
and custom theme color resolution.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Theme:
    name: str
    label: str
    bg_color: str
    border_color: str
    text_color: str
    mod_active_color: str
    mod_inactive_color: str
    pause_color: str
    border_radius: int = 14
    font_family: str = (
        "-apple-system, BlinkMacSystemFont, 'DejaVu Sans', "
        "'FiraCode Nerd Font', 'Segoe UI', Roboto, sans-serif"
    )

    def get_effective_bg(self, bg_alpha: Optional[float] = None) -> str:
        """Returns background color string formatted with transparency if specified."""
        if bg_alpha is None or bg_alpha >= 1.0:
            return self.bg_color

        alpha = max(0.05, min(1.0, float(bg_alpha)))
        color = self.bg_color.strip()
        if color.startswith("#"):
            hex_body = color.lstrip("#")
            if len(hex_body) == 6:
                r = int(hex_body[0:2], 16)
                g = int(hex_body[2:4], 16)
                b = int(hex_body[4:6], 16)
                return f"rgba({r}, {g}, {b}, {alpha:.2f})"
            elif len(hex_body) == 3:
                r = int(hex_body[0] * 2, 16)
                g = int(hex_body[1] * 2, 16)
                b = int(hex_body[2] * 2, 16)
                return f"rgba({r}, {g}, {b}, {alpha:.2f})"
        elif color.startswith("rgb(") and color.endswith(")"):
            inner = color[4:-1]
            return f"rgba({inner}, {alpha:.2f})"
        return color


BUILTIN_THEMES: Dict[str, Theme] = {
    "dark": Theme(
        name="dark",
        label="Dark (OLED)",
        bg_color="#000000",
        border_color="#1f1f22",
        text_color="#ffffff",
        mod_active_color="#ffffff",
        mod_inactive_color="#555555",
        pause_color="#f59e0b",
    ),
    "catppuccin-mocha": Theme(
        name="catppuccin-mocha",
        label="Catppuccin Mocha",
        bg_color="#1e1e2e",
        border_color="#313244",
        text_color="#cdd6f4",
        mod_active_color="#89b4fa",
        mod_inactive_color="#6c7086",
        pause_color="#fab387",
    ),
    "tokyo-night": Theme(
        name="tokyo-night",
        label="Tokyo Night",
        bg_color="#1a1b26",
        border_color="#292e42",
        text_color="#c0caf5",
        mod_active_color="#7aa2f7",
        mod_inactive_color="#565f89",
        pause_color="#e0af68",
    ),
    "nord": Theme(
        name="nord",
        label="Nord",
        bg_color="#2e3440",
        border_color="#3b4252",
        text_color="#eceff4",
        mod_active_color="#88c0d0",
        mod_inactive_color="#4c566a",
        pause_color="#ebcb8b",
    ),
    "dracula": Theme(
        name="dracula",
        label="Dracula",
        bg_color="#282a36",
        border_color="#44475a",
        text_color="#f8f8f2",
        mod_active_color="#50fa7b",
        mod_inactive_color="#6272a4",
        pause_color="#ffb86c",
    ),
    "gruvbox-dark": Theme(
        name="gruvbox-dark",
        label="Gruvbox Dark",
        bg_color="#282828",
        border_color="#3c3836",
        text_color="#ebdbb2",
        mod_active_color="#fabd2f",
        mod_inactive_color="#7c6f64",
        pause_color="#fe8019",
    ),
    "light": Theme(
        name="light",
        label="Light",
        bg_color="#f3f4f6",
        border_color="#d1d5db",
        text_color="#111827",
        mod_active_color="#2563eb",
        mod_inactive_color="#9ca3af",
        pause_color="#d97706",
    ),
}


def resolve_theme(
    theme_name: str = "dark",
    custom_dict: Optional[Dict[str, Any]] = None,
    bg_alpha: Optional[float] = None,
) -> Theme:
    """
    Resolves a Theme instance by name, falling back to 'dark'.
    If theme_name == 'custom' and custom_dict is provided, builds a Theme from overrides.
    """
    key = str(theme_name).lower().strip()

    if key == "custom" and custom_dict:
        base = BUILTIN_THEMES.get("dark")
        return Theme(
            name="custom",
            label="Custom",
            bg_color=str(custom_dict.get("bg_color", base.bg_color)),
            border_color=str(custom_dict.get("border_color", base.border_color)),
            text_color=str(custom_dict.get("text_color", base.text_color)),
            mod_active_color=str(custom_dict.get("mod_active_color", base.mod_active_color)),
            mod_inactive_color=str(
                custom_dict.get("mod_inactive_color", base.mod_inactive_color)
            ),
            pause_color=str(custom_dict.get("pause_color", base.pause_color)),
            border_radius=int(custom_dict.get("border_radius", base.border_radius)),
            font_family=str(custom_dict.get("font_family", base.font_family)),
        )

    resolved = BUILTIN_THEMES.get(key, BUILTIN_THEMES["dark"])
    return resolved
