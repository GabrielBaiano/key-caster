#!/usr/bin/env python3
"""
Key-caster: Lightweight on-screen key stroke displayer for Linux.
"""
import os
import sys

# Auto-detect local virtualenv if current interpreter lacks dependencies
venv_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv")
venv_python = os.path.join(venv_dir, "bin", "python3")

if os.path.exists(venv_python) and sys.prefix != venv_dir:
    try:
        import PyQt5  # noqa: F401
    except ImportError:
        os.execv(venv_python, [venv_python] + sys.argv)

# On Linux desktop sessions with tiling or Wayland (e.g. COSMIC, Sway, Hyprland, i3),
# the X11 platform plugin (xcb) under Xwayland allows exact (x, y) positioning,
# window manager bypass (override_redirect), and prevents tiling window managers
# from capturing the overlay into a split tile.
if "QT_QPA_PLATFORM" not in os.environ and os.environ.get("DISPLAY"):
    os.environ["QT_QPA_PLATFORM"] = "xcb"

# Ensure 'src' is available in Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

try:
    from src.__main__ import main
except ModuleNotFoundError as exc:
    sys.exit(
        f"\n[Key-Caster Error] Missing dependency: {exc}\n"
        "Make sure to install requirements:\n"
        "  pip install -r requirements.txt\n"
        "Or activate the project venv:\n"
        "  source .venv/bin/activate\n"
    )

if __name__ == "__main__":
    main()
