import pytest
from src.theme import BUILTIN_THEMES, Theme, resolve_theme
from src.config import DEFAULT_CONFIG, load_config, dump_toml, _parse_toml_fallback, VALID_THEMES
from src.ui.CentralWidget import CentralWidget
from src.ui.KeyDisplayer import KeyDisplayer
from src.ui.ModKeyDisplayer import ModKeyDisplayer


def test_builtin_themes_presence():
    expected = {
        "dark",
        "catppuccin-mocha",
        "tokyo-night",
        "nord",
        "dracula",
        "gruvbox-dark",
        "light",
    }
    assert expected.issubset(set(BUILTIN_THEMES.keys()))
    for key, theme in BUILTIN_THEMES.items():
        assert isinstance(theme, Theme)
        assert theme.name == key
        assert theme.bg_color.startswith("#")
        assert theme.border_color.startswith("#")
        assert theme.text_color.startswith("#")
        assert theme.mod_active_color.startswith("#")
        assert theme.mod_inactive_color.startswith("#")
        assert theme.pause_color.startswith("#")
        assert theme.border_radius > 0


def test_resolve_theme_case_and_fallback():
    # Valid lookups
    nord = resolve_theme("Nord")
    assert nord.name == "nord"

    mocha = resolve_theme("  catppuccin-mocha  ")
    assert mocha.name == "catppuccin-mocha"

    # Fallback to dark
    fallback = resolve_theme("non_existent_theme_xyz")
    assert fallback.name == "dark"


def test_resolve_theme_custom():
    custom_dict = {
        "bg_color": "#112233",
        "border_color": "#445566",
        "text_color": "#ffffff",
        "mod_active_color": "#00ff00",
        "mod_inactive_color": "#777777",
        "pause_color": "#ffaa00",
        "border_radius": 20,
    }
    custom = resolve_theme("custom", custom_dict=custom_dict)
    assert custom.name == "custom"
    assert custom.bg_color == "#112233"
    assert custom.border_color == "#445566"
    assert custom.border_radius == 20


def test_theme_get_effective_bg():
    dark = BUILTIN_THEMES["dark"]
    # 1.0 or None returns standard hex
    assert dark.get_effective_bg(None) == "#000000"
    assert dark.get_effective_bg(1.0) == "#000000"

    # Alpha 0.8 formatted to rgba
    rgba_bg = dark.get_effective_bg(0.8)
    assert rgba_bg == "rgba(0, 0, 0, 0.80)"

    mocha = BUILTIN_THEMES["catppuccin-mocha"]  # #1e1e2e -> r=30, g=30, b=46
    mocha_bg = mocha.get_effective_bg(0.5)
    assert mocha_bg == "rgba(30, 30, 46, 0.50)"


def test_ui_widgets_apply_theme(qapp):
    theme = BUILTIN_THEMES["catppuccin-mocha"]

    key_dis = KeyDisplayer(max_keys=5, font_size=24, theme=theme)
    assert theme.text_color in key_dis.styleSheet()

    mod_dis = ModKeyDisplayer(theme=theme)
    assert theme.border_color in mod_dis.styleSheet()

    card = CentralWidget(None, key_dis, mod_dis, theme=theme, bg_alpha=0.75)
    assert "rgba(30, 30, 46, 0.75)" in card.styleSheet()
    assert theme.border_color in card.styleSheet()

    # Switch theme dynamically
    tokyo = BUILTIN_THEMES["tokyo-night"]
    card.apply_theme(tokyo, bg_alpha=1.0)
    key_dis.apply_theme(tokyo)
    mod_dis.apply_theme(tokyo)

    assert tokyo.bg_color in card.styleSheet()
    assert tokyo.text_color in key_dis.styleSheet()
    assert tokyo.border_color in mod_dis.styleSheet()


def test_config_theme_persistence(tmp_path):
    config_file = str(tmp_path / "config.toml")
    data = {
        "theme": "nord",
        "bg_alpha": 0.85,
        "opacity": 0.9,
        "custom_theme": {
            "bg_color": "#123456",
            "border_color": "#789abc",
        },
    }
    raw_toml = dump_toml(data)
    assert 'theme = "nord"' in raw_toml
    assert "bg_alpha = 0.85" in raw_toml
    assert "[custom_theme]" in raw_toml
    assert 'bg_color = "#123456"' in raw_toml

    with open(config_file, "w", encoding="utf-8") as f:
        f.write(raw_toml)

    loaded = load_config(config_file)
    assert loaded["theme"] == "nord"
    assert loaded["bg_alpha"] == 0.85
    assert loaded["custom_theme"]["bg_color"] == "#123456"
