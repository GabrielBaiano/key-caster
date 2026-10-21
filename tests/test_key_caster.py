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


def test_classify_keyboard_device(monkeypatch):
    from xkb_resolver import classify_keyboard_device

    device_map = {
        "/dev/input/event2": "AT Translated Set 2 keyboard",
        "/dev/input/event21": "ROYUAN Akko keyboard",
        "/dev/input/event10": "Logitech USB Keyboard",
        "/dev/input/event11": "Dell KB216 Wired Keyboard",
        "/dev/input/event12": "Generic USB Keyboard",
        "/dev/input/event13": "Keychron K2 Pro",
        "/dev/input/event14": "ThinkPad Extra Buttons",
    }

    monkeypatch.setattr(
        "xkb_resolver.get_device_name",
        lambda p: device_map.get(p, ""),
    )

    # Built-in laptop / ThinkPad
    assert classify_keyboard_device("/dev/input/event2") == "abnt2"
    assert classify_keyboard_device("/dev/input/event14") == "abnt2"

    # Explicit ANSI keyboards
    assert classify_keyboard_device("/dev/input/event21") == "us-intl"
    assert classify_keyboard_device("/dev/input/event13") == "us-intl"

    # Generic USB keyboards should NOT be forced to us-intl; they return 'auto'
    assert classify_keyboard_device("/dev/input/event10") == "auto"
    assert classify_keyboard_device("/dev/input/event11") == "auto"
    assert classify_keyboard_device("/dev/input/event12") == "auto"
    assert classify_keyboard_device("/dev/input/unknown") == "auto"
    assert classify_keyboard_device(None) == "auto"


def test_xkb_resolver_dead_keys_us_intl():
    from xkb_resolver import XkbResolver

    resolver = XkbResolver(layout="us-intl")
    assert resolver.available

    # Scancode 40 (apostrophe / quote key next to Enter):
    # Must resolve cleanly to ' and " instead of dead acute / diaeresis
    res_40 = resolver.resolve(40, is_shift=False)
    assert res_40 == {"type": "char", "name": "'"}
    res_40_s = resolver.resolve(40, is_shift=True)
    assert res_40_s == {"type": "char", "name": '"'}

    # Scancode 41 (grave / tilde key under ESC)
    res_41 = resolver.resolve(41, is_shift=False)
    assert res_41 == {"type": "char", "name": "`"}
    res_41_s = resolver.resolve(41, is_shift=True)
    assert res_41_s == {"type": "char", "name": "~"}


def test_xkb_resolver_dead_keys_abnt2():
    from xkb_resolver import XkbResolver

    resolver = XkbResolver(layout="abnt2")
    assert resolver.available

    # Scancode 40 on ABNT2 ThinkPad is the tilde key next to Ç
    res_40 = resolver.resolve(40, is_shift=False)
    assert res_40 == {"type": "char", "name": "~"}
    res_40_s = resolver.resolve(40, is_shift=True)
    assert res_40_s == {"type": "char", "name": "^"}

    # Scancode 26 on ABNT2 ThinkPad is acute / grave next to P
    res_26 = resolver.resolve(26, is_shift=False)
    assert res_26 == {"type": "char", "name": "´"}
    res_26_s = resolver.resolve(26, is_shift=True)
    assert res_26_s == {"type": "char", "name": "`"}


def test_worker_per_device_resolution(monkeypatch):
    from types import SimpleNamespace

    device_map = {
        "/dev/input/event2": "AT Translated Set 2 keyboard",
        "/dev/input/event21": "ROYUAN Akko keyboard",
        "/dev/input/event10": "Logitech USB Keyboard",
    }

    monkeypatch.setattr(
        "xkb_resolver.get_device_name",
        lambda p: device_map.get(p, ""),
    )

    worker = Worker(layout="auto")
    worker.active_auto_layout = "abnt2"

    event_laptop = SimpleNamespace(device="/dev/input/event2", scan_code=40)
    event_akko = SimpleNamespace(device="/dev/input/event21", scan_code=40)
    event_generic = SimpleNamespace(device="/dev/input/event10", scan_code=40)

    res_laptop = worker.get_resolver(event_laptop)
    res_akko = worker.get_resolver(event_akko)
    res_generic = worker.get_resolver(event_generic)

    # Scancode 40 on laptop (ABNT2 ThinkPad) produces ~
    assert res_laptop.resolve(40, is_shift=False) == {"type": "char", "name": "~"}

    # Scancode 40 on Akko (US-Intl ANSI) produces '
    assert res_akko.resolve(40, is_shift=False) == {"type": "char", "name": "'"}

    # Scancode 40 on generic USB keyboard falls back to active_auto_layout (ABNT2 -> ~)
    assert res_generic.resolve(40, is_shift=False) == {"type": "char", "name": "~"}


def test_key_displayer_paused(qapp):
    displayer = KeyDisplayer(max_keys=3)
    displayer.add_key("A")
    assert displayer.text() == "A"

    displayer.set_paused(True)
    assert displayer.text() == "⏸ PAUSED"

    # Keys are ignored while paused
    displayer.add_key("B")
    assert displayer.text() == "⏸ PAUSED"

    displayer.set_paused(False)
    assert displayer.text() == ""
    displayer.add_key("C")
    assert displayer.text() == "C"


def test_worker_pause_and_privacy_controls(qapp):
    worker = Worker(layout="auto", paused=False, privacy=False)
    pause_events = []
    privacy_events = []

    worker.pause_toggled.connect(pause_events.append)
    worker.privacy_toggled.connect(privacy_events.append)

    worker.toggle_pause()
    assert worker.is_paused is True
    assert pause_events == [True]

    worker.toggle_pause()
    assert worker.is_paused is False
    assert pause_events == [True, False]

    worker.toggle_privacy()
    assert worker.is_privacy is True
    assert privacy_events == [True]

    worker.toggle_privacy()
    assert worker.is_privacy is False
    assert privacy_events == [True, False]


def test_main_window_pause_and_privacy_integration(qapp):
    win = MainWindow(start_worker=False, paused=True, privacy=True)
    assert win.is_paused is True
    assert win.is_privacy is True
    assert win.key_dis.text() == "⏸ PAUSED"

    # Key presses are ignored while paused
    win.on_key_pressed("Z")
    assert win.key_dis.text() == "⏸ PAUSED"

    # Unpause
    win.toggle_pause()
    assert win.is_paused is False
    assert win.key_dis.text() == ""

    # Normal key press works after unpausing
    win.on_key_pressed("Z")
    assert win.key_dis.text() == "Z"

    # Pausing again clears and shows paused label
    win.toggle_pause()
    assert win.is_paused is True
    assert win.key_dis.text() == "⏸ PAUSED"


def test_worker_privacy_character_masking():
    worker = Worker(layout="auto", privacy=True)
    resolved_char = {"type": "char", "name": "k"}
    label = "•" if (worker.is_privacy and resolved_char["type"] == "char") else resolved_char["name"]
    assert label == "•"

    resolved_action = {"type": "action", "name": "↩"}
    label_action = "•" if (worker.is_privacy and resolved_action["type"] == "char") else resolved_action["name"]
    assert label_action == "↩"

