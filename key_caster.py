#!/usr/bin/env python3
"""
Key-caster: Lightweight on-screen key stroke displayer for Linux.
"""
import os
import sys

# Auto-detect local virtualenv if current interpreter lacks dependencies (resolving symlinks)
script_dir = os.path.dirname(os.path.realpath(__file__))
venv_dir = os.path.join(script_dir, ".venv")
venv_python = os.path.join(venv_dir, "bin", "python3")

if os.path.exists(venv_python) and sys.prefix != venv_dir:
    try:
        import PyQt5  # noqa: F401
    except ImportError:
        os.execv(venv_python, [venv_python] + sys.argv)

# On Linux desktop sessions with tiling or Wayland (e.g. COSMIC, Sway, Hyprland, i3),
# select the appropriate Qt platform plugin:
if "QT_QPA_PLATFORM" not in os.environ:
    explicit_platform = None
    for i, arg in enumerate(sys.argv):
        if arg in ("--platform", "-P") and i + 1 < len(sys.argv):
            explicit_platform = sys.argv[i + 1]
            break
        elif arg.startswith("--platform="):
            explicit_platform = arg.split("=", 1)[1]
            break

    if explicit_platform:
        if explicit_platform != "auto":
            os.environ["QT_QPA_PLATFORM"] = explicit_platform
    elif os.environ.get("DISPLAY"):
        os.environ["QT_QPA_PLATFORM"] = "xcb"
    elif os.environ.get("WAYLAND_DISPLAY"):
        os.environ["QT_QPA_PLATFORM"] = "wayland"

# Ensure 'src' is available in Python path
sys.path.insert(0, os.path.join(script_dir, "src"))

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
