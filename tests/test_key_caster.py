import os
import sys
import pytest

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

# Ensure project root and src are in python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ui.KeyDisplayer import KeyDisplayer
from ui.ModKeyDisplayer import ModKeyDisplayer
from src.__main__ import MainWindow, Worker


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_key_displayer_queue(qapp):
    displayer = KeyDisplayer(max_keys=3)
    displayer.add_key("A")
    assert displayer.text() == "A"

    displayer.add_key("B")
    assert displayer.text() == "AB"

    displayer.add_key("C")
    assert displayer.text() == "ABC"

    # Beyond max_keys: FIFO eviction
    displayer.add_key("D")
    assert displayer.text() == "BCD"

    displayer.clear_keys()
    assert displayer.text() == ""


def test_mod_key_displayer(qapp):
    mod = ModKeyDisplayer(parent=None)
    assert "#555555" in mod.modifiers["ctrl"].text()
    assert "⌃" in mod.modifiers["ctrl"].text()
    assert "⇧" in mod.modifiers["shift"].text()

    mod.set_modifiers(["ctrl", "shift"])
    assert "#ffffff" in mod.modifiers["ctrl"].text()
    assert "#ffffff" in mod.modifiers["shift"].text()
    assert "#555555" in mod.modifiers["alt"].text()

    mod.reset_modifiers(["ctrl"])
    assert "#555555" in mod.modifiers["ctrl"].text()
    assert "#ffffff" in mod.modifiers["shift"].text()

    mod.reset_all()
    assert "#555555" in mod.modifiers["shift"].text()


def test_worker_mac_symbols():
    assert Worker.map_keys["backspace"] == "⌫"
    assert Worker.map_keys["delete"] == "⌦"
    assert Worker.map_keys["enter"] == "↩"
    assert Worker.map_keys["tab"] == "⇥"
    assert Worker.map_keys["esc"] == "⎋"
    assert Worker.map_keys["up"] == "↑"
    assert Worker.map_keys["down"] == "↓"
    assert Worker.map_keys["left"] == "←"
    assert Worker.map_keys["right"] == "→"


def test_worker_shift_mappings():
    assert Worker.shift_maps["abnt2"]["~"] == "^"
    assert Worker.shift_maps["abnt2"]["´"] == "`"
    assert Worker.shift_maps["abnt2"]["'"] == '"'
    assert Worker.shift_maps["us-intl"]["~"] == "^"


def test_space_clears_display(qapp):
    win = MainWindow(start_worker=False)
    win.on_key_pressed("hello")
    assert win.key_dis.text() == "hello"

    win.on_space_pressed()
    assert win.key_dis.text() == ""


def test_main_window_events(qapp):
    win = MainWindow(timeout=1.0, max_keys=3, start_worker=False)
    assert win.timeout == 1.0

    win.on_key_pressed("X")
    assert win.key_dis.text() == "X"
    assert win.inactivity_timer.isActive()

    win.on_modifiers_updated(["ctrl"])
    assert "#ffffff" in win.mod_dis.modifiers["ctrl"].text()

    # Trigger inactivity timeout manually
    win.on_inactivity_timeout()
    assert win.key_dis.text() == ""
    assert "#555555" in win.mod_dis.modifiers["ctrl"].text()

    # Toggle auto-hide
    win.toggle_auto_hide()
    assert win.timeout == 0
    assert not win.inactivity_timer.isActive()

    win.toggle_auto_hide()
    assert win.timeout == 2.0


def test_main_window_custom_config(qapp):
    win = MainWindow(timeout=0, max_keys=10, font_size=36, opacity=0.8, start_worker=False)
    assert win.timeout == 0
    assert win.max_keys == 10
    assert win.windowOpacity() == 0.8
    assert win.key_dis.max_keys == 10


def test_mouse_drag_movement(qapp):
    from PyQt5.QtCore import QPoint
    from PyQt5.QtGui import QMouseEvent
    from PyQt5.QtCore import QEvent

    win = MainWindow(start_worker=False)
    win.show()
    start_pos = win.pos()

    # Simulate mouse press
    press_event = QMouseEvent(QEvent.MouseButtonPress, QPoint(10, 10), QPoint(100, 100), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    win.mousePressEvent(press_event)
    assert hasattr(win, "_drag_pos")

    # Simulate mouse move
    move_event = QMouseEvent(QEvent.MouseMove, QPoint(20, 20), QPoint(120, 120), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    win.mouseMoveEvent(move_event)
    assert win.pos() != start_pos


def test_xkb_resolver_active_detection():
    from xkb_resolver import XkbResolver
    resolver = XkbResolver(layout="auto")
    assert resolver.available

    # Active system desktop layout (US alt-intl):
    # Scancode 41 (key under ESC) produces ` and ~
    res_41 = resolver.resolve(41, is_shift=False)
    assert res_41 == {"type": "char", "name": "`"}
    res_41_s = resolver.resolve(41, is_shift=True)
    assert res_41_s == {"type": "char", "name": "~"}

    # Scancode 39 (key next to L) produces ; and : (NOT ç)
    res_39 = resolver.resolve(39, is_shift=False)
    assert res_39 == {"type": "char", "name": ";"}
    res_39_s = resolver.resolve(39, is_shift=True)
    assert res_39_s == {"type": "char", "name": ":"}

    # Space & Action keys
    assert resolver.resolve(57, is_shift=False) == {"type": "space", "name": "space"}
    assert resolver.resolve(14, is_shift=False) == {"type": "action", "name": "⌫"}
    assert resolver.resolve(28, is_shift=False) == {"type": "action", "name": "↩"}


def test_xkb_resolver_abnt2_override():
    from xkb_resolver import XkbResolver
    resolver = XkbResolver(layout="abnt2")
    assert resolver.available

    # Brazilian ThinkPad / ABNT2 layout:
    # Scancode 41 (key under ESC) should be apostrophe and quotedbl
    res_41 = resolver.resolve(41, is_shift=False)
    assert res_41 == {"type": "char", "name": "'"}
    res_41_s = resolver.resolve(41, is_shift=True)
    assert res_41_s == {"type": "char", "name": '"'}

    # Scancode 39 (ç / Ç)
    res_39 = resolver.resolve(39, is_shift=False)
    assert res_39 == {"type": "char", "name": "ç"}
    res_39_s = resolver.resolve(39, is_shift=True)
    assert res_39_s == {"type": "char", "name": "Ç"}


def test_xkb_resolver_us_override():
    from xkb_resolver import XkbResolver
    resolver = XkbResolver(layout="us")
    assert resolver.available

    # US layout: scancode 41 is ` and ~
    res_41 = resolver.resolve(41, is_shift=False)
    assert res_41 == {"type": "char", "name": "`"}
    res_41_s = resolver.resolve(41, is_shift=True)
    assert res_41_s == {"type": "char", "name": "~"}


def test_main_window_switch_layout(qapp):
    win = MainWindow(start_worker=False)
    win.set_keyboard_layout("us-intl")
    assert win.layout == "us-intl"
    assert win.worker.layout == "us-intl"

    win.set_keyboard_layout("abnt2")
    assert win.layout == "abnt2"
    assert win.worker.layout == "abnt2"
