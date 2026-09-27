#!/usr/bin/python3

import argparse
import os
import signal
import sys
from collections import deque

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

    def __init__(self, layout: str = "auto"):
        super().__init__()
        self._running = True
        self.is_auto = (layout == "auto")
        self.layout = layout
        self.active_auto_layout = "abnt2"

        # Piscina de resolvers em cache para trocar de layout na velocidade da luz
        self.resolvers = {
            "abnt2": XkbResolver(layout="abnt2"),
            "us-intl": XkbResolver(layout="us-intl"),
            "us": XkbResolver(layout="us"),
        }
        if layout not in self.resolvers and layout != "auto":
            self.resolvers[layout] = XkbResolver(layout=layout)
        self.device_layout_cache = {}

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

            # Atalho de troca de layout do desktop (Super+Space ou Alt+Shift)
            if is_key_down and not is_holding and self.is_auto:
                if ("windows" in e.modifiers or "alt" in e.modifiers) and e.scan_code == 57:
                    new_layout = "us-intl" if self.active_auto_layout == "abnt2" else "abnt2"
                    self.active_auto_layout = new_layout
                    for d, l in list(self.device_layout_cache.items()):
                        if l in ("abnt2", "us-intl"):
                            # Atualiza layout de dispositivos desconhecidos
                            pass
                    self.layout_switched.emit(new_layout)

            resolver = self.get_resolver(e)
            resolved = resolver.resolve(e.scan_code, is_shift=is_shift)

            if resolved:
                if resolved["type"] == "modifier":
                    is_modifier = True
                elif is_key_down and not is_holding:
                    if resolved["type"] == "space":
                        self.space_pressed.emit()
                    else:
                        self.key_pressed.emit(resolved["name"])
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
    ):
        super().__init__()

        self.timeout = timeout
        self.max_keys = max_keys
        self.layout = layout
        self._drag_pos = QPoint()

        self.setWindowTitle("Key-caster")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_X11DoNotAcceptFocus, True)
        self.setWindowOpacity(opacity)

        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.WindowDoesNotAcceptFocus
            | Qt.X11BypassWindowManagerHint
            | Qt.Tool,
        )

        self.setStyleSheet("QMainWindow { background: transparent; border: none; }")

        self.key_dis = KeyDisplayer(self, max_keys=max_keys, font_size=font_size)
        self.mod_dis = ModKeyDisplayer(self)
        self.central_widget = CentralWidget(self, self.key_dis, self.mod_dis)
        self.setCentralWidget(self.central_widget)

        self.setFixedSize(220, 100)

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
        self.worker = Worker(layout=layout)
        self.worker.key_pressed.connect(self.on_key_pressed)
        self.worker.space_pressed.connect(self.on_space_pressed)
        self.worker.modifiers_updated.connect(self.on_modifiers_updated)
        self.worker.modifiers_reset.connect(self.on_modifiers_reset)
        self.worker.layout_switched.connect(self.on_layout_switched)
        self.worker.error_occurred.connect(self.on_worker_error)

        if start_worker:
            self.worker.start()

    @pyqtSlot(str)
    def on_layout_switched(self, layout: str):
        if hasattr(self, "worker") and not self.worker.is_auto:
            self.layout = layout

    def location_on_the_screen(self, position: str = "bottom-right", margin_x: int = 40, margin_y: int = 60):
        screen = QApplication.primaryScreen()
        if screen:
            ag = screen.availableGeometry()
        else:
            ag = QDesktopWidget().availableGeometry()

        pos = position.lower()
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

    @pyqtSlot(str)
    def on_key_pressed(self, key_label: str):
        self.key_dis.add_key(key_label)
        if not self.isVisible():
            self.show()
        if self.timeout > 0:
            self.inactivity_timer.start(int(self.timeout * 1000))

    @pyqtSlot(list)
    def on_modifiers_updated(self, modifiers: list):
        self.mod_dis.set_modifiers(modifiers)
        if self.timeout > 0:
            self.inactivity_timer.start(int(self.timeout * 1000))

    @pyqtSlot(tuple)
    def on_modifiers_reset(self, modifiers: tuple):
        self.mod_dis.reset_modifiers(modifiers)

    @pyqtSlot()
    def on_space_pressed(self):
        self.clear_display()

    @pyqtSlot()
    def on_inactivity_timeout(self):
        self.key_dis.clear_keys()
        self.mod_dis.reset_all()

    @pyqtSlot(str)
    def on_worker_error(self, message: str):
        print(f"\n[Key-Caster Warning] {message}\n", file=sys.stderr)

    def clear_display(self):
        self.key_dis.clear_keys()
        self.mod_dis.reset_all()

    def toggle_auto_hide(self):
        if self.timeout > 0:
            self.timeout = 0
            self.inactivity_timer.stop()
        else:
            self.timeout = 2.0

    def set_keyboard_layout(self, layout: str):
        self.layout = layout
        if hasattr(self, "worker") and self.worker:
            self.worker.set_layout(layout)

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
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

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

        menu.addSeparator()
        exit_act = menu.addAction("Exit Key-caster")

        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action == exit_act:
            self.close()
        elif action == clear_act:
            self.clear_display()
        elif action == toggle_act:
            self.toggle_auto_hide()
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

    def closeEvent(self, event):
        if hasattr(self, "worker") and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(500)
        event.accept()


def main():
    if "QT_QPA_PLATFORM" not in os.environ and os.environ.get("DISPLAY"):
        os.environ["QT_QPA_PLATFORM"] = "xcb"

    parser = argparse.ArgumentParser(
        description="Key-caster: Lightweight on-screen keystroke displayer for Linux."
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=float,
        default=2.0,
        help="Inactivity timeout in seconds before clearing keystrokes (default: 2.0, 0 to disable)",
    )
    parser.add_argument(
        "-m",
        "--max-keys",
        type=int,
        default=5,
        help="Maximum number of simultaneous keys displayed (default: 5)",
    )
    parser.add_argument(
        "-s",
        "--font-size",
        type=int,
        default=32,
        help="Font size for keys in pixels (default: 32)",
    )
    parser.add_argument(
        "-o",
        "--opacity",
        type=float,
        default=0.92,
        help="Overlay opacity between 0.1 and 1.0 (default: 0.92)",
    )
    parser.add_argument(
        "-p",
        "--position",
        type=str,
        default="bottom-right",
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
        default="auto",
        choices=["auto", "abnt2", "br", "us-intl", "us"],
        help="Keyboard layout for shift mappings (default: auto)",
    )

    args = parser.parse_args()

    app = QApplication(sys.argv)

    # Enable clean Ctrl+C handling in Qt event loop
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    sigint_timer = QTimer()
    sigint_timer.start(250)
    sigint_timer.timeout.connect(lambda: None)

    window = MainWindow(
        timeout=args.timeout,
        max_keys=args.max_keys,
        font_size=args.font_size,
        opacity=args.opacity,
        layout=args.layout,
    )
    window.location_on_the_screen(position=args.position)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

