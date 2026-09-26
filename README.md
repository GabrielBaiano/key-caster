# Key-caster

A lightweight on-screen key stroke displayer for Linux, inspired by KeyCastr for macOS.

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the app preserving your desktop session environment:

```bash
sudo -E $(which python3) key_caster.py
```

> **Note**: Capturing global keystrokes across Linux/Wayland requires reading raw input events via root privileges or membership in the `input` group. Using `sudo -E` ensures your graphical session (`DISPLAY` / `WAYLAND_DISPLAY`) is preserved.

### Options

```bash
python3 key_caster.py --help

  -t, --timeout TIMEOUT     Inactivity timeout in seconds before clearing keys (default: 2.0, 0 to disable)
  -m, --max-keys MAX_KEYS   Maximum number of simultaneous keys displayed (default: 5)
  -s, --font-size SIZE      Font size in pixels (default: 28)
  -o, --opacity OPACITY     Window opacity between 0.1 and 1.0 (default: 0.92)
```

## Controls

- **Reposition**: Click and drag the overlay with the left mouse button to place it anywhere on screen.
- **Context Menu**: Right-click the overlay to clear keys, toggle auto-hide, or exit.
- **Stop**: Press `Ctrl+C` in the terminal or select **Exit** in the right-click menu.

## Screenshots

![image](https://github.com/MIT4893-Projects/key-caster/assets/116936560/654498a7-a2ee-4c7e-8e2e-521db0449a4a)
![image](https://github.com/MIT4893-Projects/key-caster/assets/116936560/f7438f85-feca-4941-bc18-47f0a1f4802a)
