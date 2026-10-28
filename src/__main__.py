#!/usr/bin/python3

import argparse
import os
import signal
import subprocess
import sys
from collections import deque
from typing import Optional


def make_window_sticky_and_top(win_id: int):
    """Configures EWMH atoms to ensure the window floats above all tiles, workspaces, and full-screen windows."""
    try:
        hex_id = hex(win_id)
        subprocess.run(
            ["xprop", "-id", hex_id, "-f", "_NET_WM_DESKTOP", "32c", "-set", "_NET_WM_DESKTOP", "4294967295"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        subprocess.run(
            ["xprop", "-id", hex_id, "-f", "_NET_WM_STATE", "32a", "-set", "_NET_WM_STATE", "_NET_WM_STATE_ABOVE,_NET_WM_STATE_STAYS_ON_TOP,_NET_WM_STATE_STICKY"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        pass

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QPoint, Qt, QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication, QDesktopWidget, QMainWindow, QMenu

try:
    from ui.CentralWidget import CentralWidget
    from ui.KeyDisplayer import KeyDisplayer
    from ui.ModKeyDisplayer import ModKeyDisplayer
except ImportError:
    from src.ui.CentralWidget import CentralWidget
    from src.ui.KeyDisplayer import KeyDisplayer
    from src.ui.ModKeyDisplayer import ModKeyDisplayer

try:
    from xkb_resolver import XkbResolver, classify_keyboard_device
except ImportError:
    from src.xkb_resolver import XkbResolver, classify_keyboard_device

try:
    from config import (
        DEFAULT_CONFIG,
        VALID_LAYOUTS,
        VALID_POSITIONS,
        get_default_config_path,
        load_config,
        save_config,
    )
except ImportError:
    from src.config import (
        DEFAULT_CONFIG,
        VALID_LAYOUTS,
        VALID_POSITIONS,
        get_default_config_path,
        load_config,
        save_config,
    )


def patch_keyboard_linux():
    """
    Patches keyboard library internals on Linux:
    1. Bypasses root checks for users in the 'input' group.
    2. Gracefully handles stale or disconnected USB devices without exit() or unhandled tracebacks.
    3. Handles dumpkeys console failures cleanly when unprivileged.
    """
    try:
        import queue
        import threading
        import keyboard._nixcommon as nc
        import keyboard._nixkeyboard as nk

        nc.ensure_root = lambda: None
        nk.ensure_root = lambda: None

        orig_event_device = nc.EventDevice

        class RobustEventDevice(orig_event_device):
            @property
            def input_file(self):
                if self._input_file is None:
                    try:
                        self._input_file = open(self.path, "rb")
                    except (IOError, OSError):
                        return None
                return self._input_file

        class RobustAggregatedEventDevice(object):
            def __init__(self, devices, output=None):
                self.event_queue = queue.Queue()
                self.devices = [d for d in devices if d.input_file is not None]
                self.output = output or (self.devices[0] if self.devices else None)

                def start_reading(device):
                    while True:
                        try:
                            event = device.read_event()
                            self.event_queue.put(event)
                        except (OSError, IOError):
                            # USB device disconnected or removed, exit reader thread cleanly
                            break

                for device in self.devices:
                    thread = threading.Thread(target=start_reading, args=[device])
                    thread.daemon = True
                    thread.start()

            def read_event(self):
                return self.event_queue.get(block=True)

        nc.EventDevice = RobustEventDevice
        nc.AggregatedEventDevice = RobustAggregatedEventDevice

        orig_build_tables = nk.build_tables

        def safe_build_tables():
            try:
                orig_build_tables()
            except Exception:
                mods = {
                    42: "shift",
                    54: "shift",
                    29: "ctrl",
                    97: "ctrl",
                    56: "alt",
                    100: "alt gr",
                    125: "windows",
                    126: "windows",
                    58: "caps lock",
                }
                for sc, name in mods.items():
                    nk.register_key((sc, ()), name)

        nk.build_tables = safe_build_tables
    except Exception:
        pass


patch_keyboard_linux()


def detect_system_layout() -> str:
    import subprocess
    try:
        out = subprocess.check_output(
            ["setxkbmap", "-query"], universal_newlines=True, stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            if line.startswith("layout:"):
                layout = line.split(":", 1)[1].strip()
                if "br" in layout:
                    return "abnt2"
                elif "intl" in layout or "alt-intl" in layout:
                    return "us-intl"
    except Exception:
        pass

    try:
        out = subprocess.check_output(
            ["localectl", "status"], universal_newlines=True, stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            if "X11 Layout:" in line:
                layout = line.split(":", 1)[1].strip()
                if "br" in layout:
                    return "abnt2"
                elif "intl" in layout or "alt-intl" in layout:
                    return "us-intl"
    except Exception:
        pass

    return "abnt2"


class Worker(QThread):
    key_pressed = pyqtSignal(str)
    space_pressed = pyqtSignal()
    modifiers_updated = pyqtSignal(list)
    modifiers_reset = pyqtSignal(tuple)
    layout_switched = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    pause_toggled = pyqtSignal(bool)
    privacy_toggled = pyqtSignal(bool)

    map_keys = {
        "backspace": "⌫",
        "delete": "⌦",
        "enter": "↩",
        "tab": "⇥",
        "esc": "⎋",
        "escape": "⎋",
        "caps lock": "⇪",
        "up": "↑",
        "down": "↓",
        "left": "←",
        "right": "→",
    }

    shift_maps = {
        "abnt2": {
            "~": "^",
            "´": "`",
            "'": '"',
            ";": ":",
            "/": "?",
            ",": "<",
            ".": ">",
            "\\": "|",
            "]": "}",
            "[": "{",
            "=": "+",
            "-": "_",
            "1": "!",
            "2": "@",
            "3": "#",
            "4": "$",
            "5": "%",
            "6": "¨",
            "7": "&",
            "8": "*",
            "9": "(",
            "0": ")",
            "ç": "Ç",
        },
        "us-intl": {
            "~": "^",
            "`": "~",
            "'": '"',
            ";": ":",
            "/": "?",
            ",": "<",
            ".": ">",
            "\\": "|",
            "]": "}",
            "[": "{",
            "=": "+",
            "-": "_",
            "1": "!",
            "2": "@",
            "3": "#",
            "4": "$",
            "5": "%",
            "6": "^",
            "7": "&",
            "8": "*",
            "9": "(",
            "0": ")",
        },
        "us": {
            "`": "~",
            "1": "!",
            "2": "@",
            "3": "#",
            "4": "$",
            "5": "%",
            "6": "^",
            "7": "&",
            "8": "*",
            "9": "(",
            "0": ")",
            "-": "_",
            "=": "+",
            "[": "{",
            "]": "}",
            "\\": "|",
            ";": ":",
            "'": '"',
            ",": "<",
            ".": ">",
            "/": "?",
        },
    }
    shift_maps["br"] = shift_maps["abnt2"]

    def __init__(self, layout: str = "auto", paused: bool = False, privacy: bool = False):
        super().__init__()
        self._running = True
        self.is_auto = (layout == "auto")
        self.layout = layout
        self.active_auto_layout = detect_system_layout()
        self.is_paused = paused
        self.is_privacy = privacy

        # Piscina de resolvers em cache para trocar de layout na velocidade da luz
        self.resolvers = {
            "abnt2": XkbResolver(layout="abnt2"),
            "us-intl": XkbResolver(layout="us-intl"),
            "us": XkbResolver(layout="us"),
        }
        if self.active_auto_layout not in self.resolvers:
            self.resolvers[self.active_auto_layout] = XkbResolver(layout=self.active_auto_layout)
        if layout not in self.resolvers and layout != "auto":
            self.resolvers[layout] = XkbResolver(layout=layout)
        self.device_layout_cache = {}

    def set_paused(self, paused: bool):
        if self.is_paused != paused:
            self.is_paused = paused
            self.pause_toggled.emit(self.is_paused)

    def toggle_pause(self):
        self.set_paused(not self.is_paused)

    def set_privacy(self, privacy: bool):
        if self.is_privacy != privacy:
            self.is_privacy = privacy
            self.privacy_toggled.emit(self.is_privacy)

    def toggle_privacy(self):
        self.set_privacy(not self.is_privacy)

    @property
    def xkb_resolver(self):
        if not self.is_auto:
            return self.resolvers.get(self.layout, self.resolvers["abnt2"])
        return self.resolvers.get(self.active_auto_layout, self.resolvers["abnt2"])

    @xkb_resolver.setter
    def xkb_resolver(self, val):
        self.resolvers[self.layout] = val

    def stop(self):
        self._running = False

    def set_layout(self, layout: str):
        self.is_auto = (layout == "auto")
        self.layout = layout
        if layout not in self.resolvers and layout != "auto":
            self.resolvers[layout] = XkbResolver(layout=layout)
        self.device_layout_cache.clear()
        self.layout_switched.emit(layout)

    def refresh_auto_layout(self):
        # Compatibilidade com timer/modifiers sem resetar resolvers desnecessariamente
        pass

    def get_resolver(self, event) -> XkbResolver:
        """
        Determina dinamicamente o resolver correto para o evento:
        - Se o usuário fixou o layout manualmente (ex: 'us-intl' ou 'abnt2'), respeita o override.
        - Se está em 'auto', detecta o hardware do teclado que gerou o clique (Laptop vs Akko/USB).
        """
        if not self.is_auto:
            return self.resolvers.get(self.layout, self.resolvers["abnt2"])

        dev_path = getattr(event, "device", None)
        if not dev_path:
            return self.resolvers.get(self.active_auto_layout, self.resolvers["abnt2"])

        if dev_path not in self.device_layout_cache:
            detected = classify_keyboard_device(dev_path)
            self.device_layout_cache[dev_path] = (
                detected if detected != "auto" else self.active_auto_layout
            )

        target = self.device_layout_cache[dev_path]
        return self.resolvers.get(target, self.resolvers["abnt2"])

    def run(self):
        patch_keyboard_linux()
        try:
            import keyboard
        except ImportError as exc:
            self.error_occurred.emit(
                f"Failed to import 'keyboard': {exc}\n"
                "Install requirements: pip install -r requirements.txt"
            )
            return

        try:
            last = keyboard.KeyboardEvent(event_type=keyboard.KEY_UP, scan_code=0)
        except Exception as exc:
            self.error_occurred.emit(
                f"Keyboard access error: {exc}\n"
                "To run without sudo, add your user to the input group:\n"
                "  sudo usermod -aG input $USER\n"
                "(then log out and log back in)"
            )
            return

        while self._running:
            try:
                e = keyboard.read_event()
            except Exception as exc:
                self.error_occurred.emit(
                    f"Error reading keyboard event: {exc}\n"
                    "Tip: Run with: sudo -E $(which python3) key_caster.py"
                )
                break

            is_modifier = e.name in keyboard.all_modifiers
            is_key_down = e.event_type == keyboard.KEY_DOWN
            is_holding = (
                is_key_down
                and last.event_type == keyboard.KEY_DOWN
                and last.scan_code == e.scan_code
            )
            is_shift = "shift" in e.modifiers
            has_super_or_alt = ("windows" in e.modifiers or "alt" in e.modifiers)

            # Atalho de troca de layout do desktop (Super+Space ou Alt+Shift)
            if is_key_down and not is_holding and self.is_auto:
                if has_super_or_alt and e.scan_code == 57:
                    new_layout = "us-intl" if self.active_auto_layout == "abnt2" else "abnt2"
                    self.active_auto_layout = new_layout
                    for d, l in list(self.device_layout_cache.items()):
                        if l in ("abnt2", "us-intl"):
                            # Atualiza layout de dispositivos desconhecidos
                            pass
                    self.layout_switched.emit(new_layout)

            # Atalho de Pause / Resume: Super+Shift+P ou Alt+Shift+P (scancode 25)
            if is_key_down and not is_holding and has_super_or_alt and is_shift and (e.scan_code == 25 or e.name == "p"):
                self.is_paused = not self.is_paused
                self.pause_toggled.emit(self.is_paused)
                last = e
                continue

            # Atalho de Privacidade / Mascaramento: Super+Shift+S ou Alt+Shift+S (scancode 31)
            if is_key_down and not is_holding and has_super_or_alt and is_shift and (e.scan_code == 31 or e.name == "s"):
                self.is_privacy = not self.is_privacy
                self.privacy_toggled.emit(self.is_privacy)
                last = e
                continue

            # Se estiver pausado, silencia a captura
            if self.is_paused:
                last = e
                continue

            resolver = self.get_resolver(e)
            resolved = resolver.resolve(e.scan_code, is_shift=is_shift)

            if resolved:
                if resolved["type"] == "modifier":
                    is_modifier = True
                elif is_key_down and not is_holding:
                    if resolved["type"] == "space":
                        self.space_pressed.emit()
                    else:
                        label = "•" if (self.is_privacy and resolved["type"] == "char") else resolved["name"]
                        self.key_pressed.emit(label)
                    self.modifiers_updated.emit(list(e.modifiers))
            else:
                if not is_modifier and is_key_down and not is_holding:
                    raw_name = e.name
                    # Se o dumpkeys cuspir 'unknown', joga fora
                    if raw_name != "unknown":
                        if is_shift:
                            active_table = self.shift_maps.get(
                                self.layout, self.shift_maps.get("abnt2", {})
                            )
                            if raw_name in active_table:
                                raw_name = active_table[raw_name]
                            elif len(raw_name) == 1 and raw_name.isalpha():
                                raw_name = raw_name.upper()

                        if raw_name == "space":
                            self.space_pressed.emit()
                        else:
                            key_label = self.map_keys.get(raw_name, raw_name)
                            if self.is_privacy and key_label not in self.map_keys.values():
                                key_label = "•"
                            self.key_pressed.emit(key_label)
                    self.modifiers_updated.emit(list(e.modifiers))

            if is_modifier and is_key_down:
                self.modifiers_updated.emit(list(e.modifiers))
            elif is_modifier and not is_key_down:
                self.modifiers_reset.emit((e.name,))

            last = e


class MainWindow(QMainWindow):
    def __init__(
        self,
        timeout: float = 2.0,
        max_keys: int = 5,
        font_size: int = 32,
        opacity: float = 0.92,
        layout: str = "auto",
        start_worker: bool = True,
        paused: bool = False,
        privacy: bool = False,
        config_path: str = None,
        save_state_enabled: bool = False,
    ):
        super().__init__()

        self.timeout = timeout
        self.max_keys = max_keys
        self.font_size = font_size
        self.opacity_val = max(0.1, min(1.0, float(opacity)))
        self.layout = layout
        self.is_paused = paused
        self.is_privacy = privacy
        self.config_path = config_path
        self.save_state_enabled = save_state_enabled
        self._drag_pos = QPoint()
        self._setting_preset = False
        self._adjusting_width = False

        self.setWindowTitle("Key-caster")
        self.setObjectName("key-caster")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_X11DoNotAcceptFocus, True)
        self.setAttribute(Qt.WA_X11NetWmWindowTypeDock, True)
        self.setWindowOpacity(self.opacity_val)

        # Ensure window stays on top and bypasses window managers so it cannot be tiled
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.WindowDoesNotAcceptFocus
            | Qt.X11BypassWindowManagerHint
            | Qt.BypassWindowManagerHint
            | Qt.Tool,
        )

        self.setStyleSheet("QMainWindow { background: transparent; border: none; }")

        self.key_dis = KeyDisplayer(self, max_keys=max_keys, font_size=font_size)
        self.mod_dis = ModKeyDisplayer(self)
        self.central_widget = CentralWidget(self, self.key_dis, self.mod_dis)
        self.setCentralWidget(self.central_widget)

        self.current_position = "bottom-right"
        self.is_custom_pos = False

        self.setFixedHeight(100)
        self.setMinimumWidth(220)
        self.resize(220, 100)

        # Inactivity auto-clear / auto-hide timer
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.setSingleShot(True)
        self.inactivity_timer.timeout.connect(self.on_inactivity_timeout)

        # Periodic check for layout changes in active desktop session
        self.layout_timer = QTimer(self)
        self.layout_timer.setInterval(1500)
        self.layout_timer.timeout.connect(self.on_check_layout_change)
        self.layout_timer.start()

        # Background worker for keyboard events
        self.worker = Worker(layout=layout, paused=paused, privacy=privacy)
        self.worker.key_pressed.connect(self.on_key_pressed)
        self.worker.space_pressed.connect(self.on_space_pressed)
        self.worker.modifiers_updated.connect(self.on_modifiers_updated)
        self.worker.modifiers_reset.connect(self.on_modifiers_reset)
        self.worker.layout_switched.connect(self.on_layout_switched)
        self.worker.error_occurred.connect(self.on_worker_error)
        self.worker.pause_toggled.connect(self.on_pause_toggled)
        self.worker.privacy_toggled.connect(self.on_privacy_toggled)

        if self.is_paused:
            self.key_dis.set_paused(True)

        if start_worker:
            self.worker.start()

    @pyqtSlot(str)
    def on_layout_switched(self, layout: str):
        if hasattr(self, "worker") and not self.worker.is_auto:
            self.layout = layout

    def set_opacity(self, opacity: float):
        self.opacity_val = max(0.1, min(1.0, float(opacity)))
        self.setWindowOpacity(self.opacity_val)
        self.save_state()

    def save_state(self):
        if not self.save_state_enabled:
            return

        current_layout = "auto" if (hasattr(self, "worker") and self.worker.is_auto) else self.layout
        pos = "custom" if self.is_custom_pos else self.current_position
        data = {
            "position": pos,
            "custom_x": self.x() if self.is_custom_pos else None,
            "custom_y": self.y() if self.is_custom_pos else None,
            "layout": current_layout,
            "timeout": self.timeout,
            "opacity": self.opacity_val,
            "font_size": self.font_size,
            "max_keys": self.max_keys,
            "privacy": self.is_privacy,
            "paused": self.is_paused,
        }
        save_config(data, self.config_path)

    def restore_position(
        self,
        position: str = "bottom-right",
        custom_x: Optional[int] = None,
        custom_y: Optional[int] = None,
    ):
        self._setting_preset = True
        try:
            if position == "custom" and custom_x is not None and custom_y is not None:
                # Check if coordinates intersect with or are contained by any connected screen
                valid = False
                screens = QApplication.screens()
                for screen in screens:
                    geo = screen.geometry()
                    target_rect = QtCore.QRect(custom_x, custom_y, self.width(), self.height())
                    if geo.intersects(target_rect) or geo.contains(QPoint(custom_x, custom_y)):
                        valid = True
                        break

                if valid:
                    self.is_custom_pos = True
                    self.current_position = "custom"
                    self.move(custom_x, custom_y)
                    return

            preset = position if position in VALID_POSITIONS and position != "custom" else "bottom-right"
            self.location_on_the_screen(preset)
        finally:
            self._setting_preset = False

    def location_on_the_screen(self, position: str = "bottom-right", margin_x: int = 40, margin_y: int = 60):
        self._setting_preset = True
        try:
            self.current_position = position.lower()
            self.is_custom_pos = False

            screen = QApplication.primaryScreen()
            if screen:
                ag = screen.availableGeometry()
            else:
                ag = QDesktopWidget().availableGeometry()

            pos = self.current_position
            if pos == "bottom-left":
                x = ag.x() + margin_x
                y = ag.y() + ag.height() - self.height() - margin_y
            elif pos == "bottom-center":
                x = ag.x() + (ag.width() - self.width()) // 2
                y = ag.y() + ag.height() - self.height() - margin_y
            elif pos == "top-right":
                x = ag.x() + ag.width() - self.width() - margin_x
                y = ag.y() + margin_y
            elif pos == "top-left":
                x = ag.x() + margin_x
                y = ag.y() + margin_y
            elif pos == "top-center":
                x = ag.x() + (ag.width() - self.width()) // 2
                y = ag.y() + margin_y
            elif pos == "center":
                x = ag.x() + (ag.width() - self.width()) // 2
                y = ag.y() + (ag.height() - self.height()) // 2
            else:  # bottom-right
                x = ag.x() + ag.width() - self.width() - margin_x
                y = ag.y() + ag.height() - self.height() - margin_y

            self.move(x, y)
            self.save_state()
        finally:
            self._setting_preset = False

    def update_card_width(self):
        content_w = self.key_dis.content_width() if hasattr(self.key_dis, "content_width") else 0
        if content_w > 0:
            target_w = max(220, min(600, content_w + 48))
        else:
            target_w = 220

        old_w = self.width()
        if target_w != old_w:
            screen = QApplication.primaryScreen()
            if screen:
                ag = screen.availableGeometry()
            else:
                ag = QDesktopWidget().availableGeometry()

            curr_x = self.x()
            curr_y = self.y()

            self._adjusting_width = True
            try:
                if self.current_position in ("bottom-right", "top-right") or (
                    self.is_custom_pos and curr_x > ag.x() + ag.width() // 2
                ):
                    delta = target_w - old_w
                    new_x = max(ag.x(), curr_x - delta)
                    self.move(new_x, curr_y)
                elif self.current_position in ("bottom-center", "top-center", "center"):
                    delta = target_w - old_w
                    new_x = max(ag.x(), curr_x - (delta // 2))
                    self.move(new_x, curr_y)
            finally:
                self._adjusting_width = False

            self.setFixedWidth(target_w)
            if hasattr(self, "central_widget") and self.central_widget:
                self.central_widget.setFixedWidth(target_w)

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()
        qpa = QApplication.platformName() if QApplication.instance() else ""
        if qpa == "xcb":
            try:
                make_window_sticky_and_top(int(self.winId()))
            except Exception:
                pass

    @pyqtSlot(str)
    def on_key_pressed(self, key_label: str):
        if self.is_paused:
            return
        self.key_dis.add_key(key_label)
        self.update_card_width()
        if not self.isVisible():
            self.show()
        self.raise_()
        if self.timeout > 0:
            self.inactivity_timer.start(int(self.timeout * 1000))

    @pyqtSlot(list)
    def on_modifiers_updated(self, modifiers: list):
        if self.is_paused:
            return
        self.mod_dis.set_modifiers(modifiers)
        if not self.isVisible():
            self.show()
        self.raise_()
        if self.timeout > 0:
            self.inactivity_timer.start(int(self.timeout * 1000))

    @pyqtSlot(tuple)
    def on_modifiers_reset(self, modifiers: tuple):
        if self.is_paused:
            return
        self.mod_dis.reset_modifiers(modifiers)

    @pyqtSlot()
    def on_space_pressed(self):
        if self.is_paused:
            return
        self.clear_display()

    @pyqtSlot(bool)
    def on_pause_toggled(self, is_paused: bool):
        self.is_paused = is_paused
        self.clear_display()
        self.key_dis.set_paused(is_paused)
        self.update_card_width()

    @pyqtSlot(bool)
    def on_privacy_toggled(self, is_privacy: bool):
        self.is_privacy = is_privacy

    def toggle_pause(self):
        if hasattr(self, "worker") and self.worker:
            self.worker.toggle_pause()
        else:
            self.on_pause_toggled(not self.is_paused)

    def toggle_privacy(self):
        if hasattr(self, "worker") and self.worker:
            self.worker.toggle_privacy()
        else:
            self.on_privacy_toggled(not self.is_privacy)

    @pyqtSlot()
    def on_inactivity_timeout(self):
        self.key_dis.clear_keys()
        self.mod_dis.reset_all()
        self.update_card_width()

    @pyqtSlot(str)
    def on_worker_error(self, message: str):
        print(f"\n[Key-Caster Warning] {message}\n", file=sys.stderr)

    def clear_display(self):
        self.key_dis.clear_keys()
        self.mod_dis.reset_all()
        self.update_card_width()

    def toggle_auto_hide(self):
        if self.timeout > 0:
            self.timeout = 0
            self.inactivity_timer.stop()
        else:
            self.timeout = 2.0
        self.save_state()

    def set_keyboard_layout(self, layout: str):
        self.layout = layout
        if hasattr(self, "worker") and self.worker:
            self.worker.set_layout(layout)
        self.save_state()

    @pyqtSlot()
    def on_check_layout_change(self):
        if hasattr(self, "worker") and self.worker:
            self.worker.refresh_auto_layout()

    # Mouse drag-and-drop to position the overlay anywhere
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Under Wayland (COSMIC), native compositor dragging via startSystemMove is required
            handle = self.windowHandle()
            if handle and hasattr(handle, "startSystemMove") and handle.startSystemMove():
                event.accept()
                return

            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.is_custom_pos = True
            self.current_position = "custom"
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_custom_pos:
            self.save_state()
            event.accept()

    def moveEvent(self, event):
        super().moveEvent(event)
        if not getattr(self, "_setting_preset", False) and not getattr(self, "_adjusting_width", False):
            self.is_custom_pos = True
            self.current_position = "custom"

    # Context menu for quick actions
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #27272a;
                color: #fafafa;
                border: 1px solid #3f3f46;
                padding: 4px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: #3b82f6;
            }
        """)

        clear_act = menu.addAction("Clear Keys")
        auto_hide_text = "Disable Auto-Hide" if self.timeout > 0 else "Enable Auto-Hide"
        toggle_act = menu.addAction(auto_hide_text)

        pause_text = "Resume Capturing (Super+Shift+P)" if self.is_paused else "Pause Capturing (Super+Shift+P)"
        pause_act = menu.addAction(pause_text)

        privacy_text = "Disable Privacy Masking (Super+Shift+S)" if self.is_privacy else "Enable Privacy Masking (Super+Shift+S)"
        privacy_act = menu.addAction(privacy_text)

        layout_menu = menu.addMenu("Keyboard Layout")
        layout_menu.setStyleSheet(menu.styleSheet())
        l_group = QtWidgets.QActionGroup(self)
        l_auto = layout_menu.addAction("Auto (Per-Device: Notebook=BR, External=US)")
        l_us_intl = layout_menu.addAction("US International (alt-intl)")
        l_abnt2 = layout_menu.addAction("BR ABNT2 (ThinkPad)")
        l_us = layout_menu.addAction("US Standard")

        for act in (l_auto, l_us_intl, l_abnt2, l_us):
            act.setCheckable(True)
            l_group.addAction(act)

        current = "auto" if (hasattr(self, "worker") and self.worker.is_auto) else self.layout
        if current == "auto":
            l_auto.setChecked(True)
        elif current in ("us-intl", "intl", "alt-intl"):
            l_us_intl.setChecked(True)
        elif current in ("abnt2", "br"):
            l_abnt2.setChecked(True)
        elif current == "us":
            l_us.setChecked(True)

        pos_menu = menu.addMenu("Position")
        pos_menu.setStyleSheet(menu.styleSheet())
        p_br = pos_menu.addAction("Bottom Right")
        p_bc = pos_menu.addAction("Bottom Center")
        p_bl = pos_menu.addAction("Bottom Left")
        p_tr = pos_menu.addAction("Top Right")
        p_tc = pos_menu.addAction("Top Center")
        p_tl = pos_menu.addAction("Top Left")
        p_c = pos_menu.addAction("Center")

        opacity_menu = menu.addMenu("Opacity")
        opacity_menu.setStyleSheet(menu.styleSheet())
        o_group = QtWidgets.QActionGroup(self)
        o_100 = opacity_menu.addAction("100%")
        o_90 = opacity_menu.addAction("90%")
        o_80 = opacity_menu.addAction("80%")
        o_70 = opacity_menu.addAction("70%")
        o_50 = opacity_menu.addAction("50%")

        op_actions = [
            (o_100, 1.0),
            (o_90, 0.90),
            (o_80, 0.80),
            (o_70, 0.70),
            (o_50, 0.50),
        ]
        closest_act = min(op_actions, key=lambda pair: abs(pair[1] - self.opacity_val))[0]
        for act, _ in op_actions:
            act.setCheckable(True)
            o_group.addAction(act)
        closest_act.setChecked(True)

        menu.addSeparator()
        exit_act = menu.addAction("Exit Key-caster")

        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action == exit_act:
            self.close()
        elif action == clear_act:
            self.clear_display()
        elif action == toggle_act:
            self.toggle_auto_hide()
        elif action == pause_act:
            self.toggle_pause()
        elif action == privacy_act:
            self.toggle_privacy()
        elif action == l_auto:
            self.set_keyboard_layout("auto")
        elif action == l_us_intl:
            self.set_keyboard_layout("us-intl")
        elif action == l_abnt2:
            self.set_keyboard_layout("abnt2")
        elif action == l_us:
            self.set_keyboard_layout("us")
        elif action == p_br:
            self.location_on_the_screen("bottom-right")
        elif action == p_bc:
            self.location_on_the_screen("bottom-center")
        elif action == p_bl:
            self.location_on_the_screen("bottom-left")
        elif action == p_tr:
            self.location_on_the_screen("top-right")
        elif action == p_tc:
            self.location_on_the_screen("top-center")
        elif action == p_tl:
            self.location_on_the_screen("top-left")
        elif action == p_c:
            self.location_on_the_screen("center")
        else:
            for act, val in op_actions:
                if action == act:
                    self.set_opacity(val)
                    break

    def closeEvent(self, event):
        self.save_state()
        if hasattr(self, "worker") and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(500)
        event.accept()


def main():
    parser = argparse.ArgumentParser(
        description="Key-caster: Lightweight on-screen keystroke displayer for Linux."
    )
    parser.add_argument(
        "-P",
        "--platform",
        type=str,
        default="auto",
        choices=["auto", "xcb", "wayland"],
        help="Qt platform plugin backend (default: auto)",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default=None,
        help="Path to configuration file (default: ~/.config/key-caster/config.toml)",
    )
    parser.add_argument(
        "--no-config",
        action="store_true",
        default=False,
        help="Disable loading and saving user configuration file",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=float,
        default=None,
        help="Inactivity timeout in seconds before clearing keystrokes (default: 2.0, 0 to disable)",
    )
    parser.add_argument(
        "-m",
        "--max-keys",
        type=int,
        default=None,
        help="Maximum number of simultaneous keys displayed (default: 5)",
    )
    parser.add_argument(
        "-s",
        "--font-size",
        type=int,
        default=None,
        help="Font size for keys in pixels (default: 32)",
    )
    parser.add_argument(
        "-o",
        "--opacity",
        type=float,
        default=None,
        help="Overlay opacity between 0.1 and 1.0 (default: 0.92)",
    )
    parser.add_argument(
        "-p",
        "--position",
        type=str,
        default=None,
        choices=[
            "bottom-right",
            "bottom-left",
            "bottom-center",
            "top-right",
            "top-left",
            "top-center",
            "center",
        ],
        help="Screen position preset (default: bottom-right)",
    )
    parser.add_argument(
        "-l",
        "--layout",
        type=str,
        default=None,
        choices=["auto", "abnt2", "br", "us-intl", "us"],
        help="Keyboard layout for shift mappings (default: auto)",
    )
    parser.add_argument(
        "--paused",
        action="store_true",
        default=None,
        help="Start application with key capturing paused",
    )
    parser.add_argument(
        "--privacy",
        action="store_true",
        default=None,
        help="Start application with privacy masking enabled (display bullets)",
    )

    args = parser.parse_args()

    # Route Qt platform plugin dynamically (override system defaults like 'wayland;xcb' that break overlays)
    if args.platform == "xcb":
        os.environ["QT_QPA_PLATFORM"] = "xcb"
    elif args.platform == "wayland":
        os.environ["QT_QPA_PLATFORM"] = "wayland"
    else:  # auto
        if os.environ.get("DISPLAY"):
            os.environ["QT_QPA_PLATFORM"] = "xcb"
        elif os.environ.get("WAYLAND_DISPLAY"):
            os.environ["QT_QPA_PLATFORM"] = "wayland"

    if args.no_config:
        cfg = dict(DEFAULT_CONFIG)
        save_state_enabled = False
    else:
        cfg = load_config(args.config)
        save_state_enabled = True

    timeout = args.timeout if args.timeout is not None else cfg.get("timeout", 2.0)
    max_keys = args.max_keys if args.max_keys is not None else cfg.get("max_keys", 5)
    font_size = args.font_size if args.font_size is not None else cfg.get("font_size", 32)
    opacity = args.opacity if args.opacity is not None else cfg.get("opacity", 0.92)
    layout = args.layout if args.layout is not None else cfg.get("layout", "auto")
    paused = args.paused if args.paused is not None else cfg.get("paused", False)
    privacy = args.privacy if args.privacy is not None else cfg.get("privacy", False)

    position = args.position if args.position is not None else cfg.get("position", "bottom-right")
    custom_x = None if args.position is not None else cfg.get("custom_x")
    custom_y = None if args.position is not None else cfg.get("custom_y")

    app = QApplication(sys.argv)
    app.setApplicationName("key-caster")
    app.setOrganizationName("key-caster")
    app.setDesktopFileName("key-caster")

    # Enable clean Ctrl+C handling in Qt event loop
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    sigint_timer = QTimer()
    sigint_timer.start(250)
    sigint_timer.timeout.connect(lambda: None)

    window = MainWindow(
        timeout=timeout,
        max_keys=max_keys,
        font_size=font_size,
        opacity=opacity,
        layout=layout,
        paused=paused,
        privacy=privacy,
        config_path=args.config,
        save_state_enabled=save_state_enabled,
    )
    window.restore_position(position=position, custom_x=custom_x, custom_y=custom_y)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

