import os
import sys
import tempfile
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from src.config import (
    DEFAULT_CONFIG,
    dump_toml,
    get_default_config_path,
    load_config,
    save_config,
)


def test_default_config_path(monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/custom_config")
    path = get_default_config_path()
    assert path == "/tmp/custom_config/key-caster/config.toml"


def test_load_nonexistent_returns_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = os.path.join(tmpdir, "nonexistent.toml")
        cfg = load_config(fake_path)
        assert cfg == DEFAULT_CONFIG
        assert cfg["position"] == "bottom-right"
        assert cfg["layout"] == "auto"
        assert cfg["timeout"] == 2.0


def test_save_and_load_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = os.path.join(tmpdir, "key-caster", "config.toml")
        data = {
            "position": "custom",
            "custom_x": 1280,
            "custom_y": 720,
            "layout": "us-intl",
            "timeout": 1.5,
            "opacity": 0.85,
            "font_size": 28,
            "max_keys": 7,
            "privacy": True,
            "paused": False,
        }
        saved = save_config(data, cfg_path)
        assert saved is True
        assert os.path.isfile(cfg_path)

        loaded = load_config(cfg_path)
        assert loaded["position"] == "custom"
        assert loaded["custom_x"] == 1280
        assert loaded["custom_y"] == 720
        assert loaded["layout"] == "us-intl"
        assert loaded["timeout"] == 1.5
        assert loaded["opacity"] == 0.85
        assert loaded["font_size"] == 28
        assert loaded["max_keys"] == 7
        assert loaded["privacy"] is True
        assert loaded["paused"] is False


def test_load_corrupted_file_returns_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = os.path.join(tmpdir, "bad.toml")
        with open(cfg_path, "w", encoding="utf-8") as f:
            f.write("this is completely invalid toml [[[ == !!\n")

        cfg = load_config(cfg_path)
        assert cfg["position"] == "bottom-right"
        assert cfg["layout"] == "auto"


def test_load_validates_range_and_values():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = os.path.join(tmpdir, "invalid_values.toml")
        with open(cfg_path, "w", encoding="utf-8") as f:
            f.write(
                """
                position = "invalid-position"
                layout = "unknown-layout"
                opacity = 999.0
                timeout = -10.0
                font_size = 500
                max_keys = -5
                """
            )

        cfg = load_config(cfg_path)
        # Invalid values should have been ignored and kept as defaults
        assert cfg["position"] == "bottom-right"
        assert cfg["layout"] == "auto"
        assert cfg["opacity"] == 0.92
        assert cfg["timeout"] == 2.0
        assert cfg["font_size"] == 32
        assert cfg["max_keys"] == 5


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_main_window_saves_state(qapp):
    from src.__main__ import MainWindow

    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = os.path.join(tmpdir, "config.toml")
        win = MainWindow(
            config_path=cfg_path,
            save_state_enabled=True,
            start_worker=False,
        )

        # Setting preset saves config
        win.location_on_the_screen("top-left")
        cfg = load_config(cfg_path)
        assert cfg["position"] == "top-left"
        assert cfg["custom_x"] is None

        # Changing opacity saves config
        win.set_opacity(0.75)
        cfg = load_config(cfg_path)
        assert cfg["opacity"] == 0.75

        # Changing layout saves config
        win.set_keyboard_layout("us-intl")
        cfg = load_config(cfg_path)
        assert cfg["layout"] == "us-intl"

        # Simulating mouse drag release
        win.move(350, 450)
        win.is_custom_pos = True
        win.save_state()
        cfg = load_config(cfg_path)
        assert cfg["position"] == "custom"
        assert cfg["custom_x"] == 350
        assert cfg["custom_y"] == 450


def test_main_window_restore_position_and_fallback(qapp):
    from src.__main__ import MainWindow

    win = MainWindow(start_worker=False)

    # Valid coordinates on screen
    primary_geo = qapp.primaryScreen().geometry()
    target_x = primary_geo.x() + 100
    target_y = primary_geo.y() + 100
    win.restore_position("custom", target_x, target_y)
    assert win.is_custom_pos is True
    assert win.x() == target_x
    assert win.y() == target_y

    # Offscreen coordinates (e.g. disconnected monitor at x=99999, y=99999)
    # should fallback to safe preset
    win.restore_position("custom", 99999, 99999)
    assert win.is_custom_pos is False
    assert win.current_position == "bottom-right"
    assert win.x() < 99999
