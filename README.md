# Key-caster

Lightweight on-screen keystroke displayer for Linux, inspired by KeyCastr for macOS.

Independent project based on the original work by [bm-mit/key-caster](https://github.com/bm-mit/key-caster), modernized and actively maintained for current Linux desktops (Wayland, COSMIC, and X11) with non-root execution, per-device hardware layout routing, and robust device hotplugging.

## Demo

![Key-caster Demo](assets/demo.gif)

## Prerequisites

To capture global keystrokes without `sudo`, add your user to the system `input` group:

```bash
sudo usermod -aG input $USER
```

Log out and log back in (or restart) for the group membership to take effect.

## Installation

### Via pipx (recommended)

```bash
pipx install git+https://github.com/GabrielBaiano/key-caster.git
```

### Homebrew (Linux)

```bash
brew install GabrielBaiano/tap/key-caster
```

### Arch Linux (PKGBUILD)

```bash
git clone https://github.com/GabrielBaiano/key-caster.git
cd key-caster/packaging/arch
makepkg -si
```

### From source

```bash
git clone https://github.com/GabrielBaiano/key-caster.git
cd key-caster
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

To run directly from source without installing:

```bash
python3 key_caster.py
```

### Desktop Launcher Integration

To add Key-caster to your application launcher (Rofi, Wofi, GNOME Dash, KDE Kickoff):

```bash
mkdir -p ~/.local/share/applications ~/.local/share/icons/hicolor/scalable/apps ~/.local/share/icons/hicolor/256x256/apps
cp assets/key-caster.desktop ~/.local/share/applications/
cp assets/key-caster.svg ~/.local/share/icons/hicolor/scalable/apps/
cp assets/key-caster.png ~/.local/share/icons/hicolor/256x256/apps/
```

## Usage

You can launch the overlay using either command alias:

```bash
key-caster
# or
keycaster
```

### Command-line Options

```text
key-caster [options]

  -P, --platform PLATFORM     Qt platform backend: auto, xcb, wayland (default: auto)
  -c, --config PATH           Path to configuration file (default: ~/.config/key-caster/config.toml)
  --no-config                 Disable loading and saving user configuration file
  -t, --timeout TIMEOUT       Inactivity timeout in seconds before clearing (default: 2.0, 0 to disable)
  -m, --max-keys MAX_KEYS     Maximum keys displayed simultaneously (default: 5)
  -s, --font-size SIZE        Font size in pixels (default: 32)
  -o, --opacity OPACITY       Overlay opacity between 0.1 and 1.0 (default: 0.92)
  -p, --position POSITION     Preset position: bottom-right, bottom-center, bottom-left, top-right, top-left, top-center, center
  -l, --layout LAYOUT         Keyboard layout: auto, abnt2, br, us-intl, us (default: auto)
  --theme THEME               Theme preset: dark, catppuccin-mocha, tokyo-night, nord, dracula, gruvbox-dark, light (default: dark)
  --bg-alpha ALPHA            Background card alpha transparency between 0.05 and 1.0 (default: 1.0)
  --paused                    Start application with key capturing paused
  --privacy                   Start application with privacy masking enabled (display bullets)
```

### Configuration & Themes

Key-caster automatically remembers your settings across restarts in `~/.config/key-caster/config.toml`:

- **Themes & Styling**: Switch presets anytime via the right-click **Theme** menu (`Dark (OLED)`, `Catppuccin Mocha`, `Tokyo Night`, `Nord`, `Dracula`, `Gruvbox Dark`, `Light`) or specify a `--theme` at launch. Custom hex colors can be defined under `[custom_theme]`.
- **Transparency**: Control overall window opacity via right-click (100%, 90%, 80%, 70%, 50%) or set card background transparency (`bg_alpha`) to keep keystrokes crisp and solid.
- **Window Position**: Dragging the widget to any screen or selecting a preset preserves your preferred coordinates. If a second monitor is disconnected, Key-caster safely falls back to a visible desktop area.
- **Layout & Timeout**: Saved whenever toggled from the right-click menu.

Explicit CLI flags always override the saved configuration.

### Wayland & Tiling Window Managers

Key-caster identifies itself with `app_id="key-caster"` and `class="key-caster"`.

#### Hyprland (`hyprland.conf`)
```ini
windowrulev2 = float, class:^(key-caster)$
windowrulev2 = pin, class:^(key-caster)$
windowrulev2 = noblur, class:^(key-caster)$
windowrulev2 = noinitialfocus, class:^(key-caster)$
```

#### Sway / i3 (`config`)
```ini
for_window [app_id="key-caster"] floating enable, sticky enable
for_window [class="^key-caster$"] floating enable, sticky enable
```

#### Pure Wayland without Xwayland
If Xwayland is disabled on your system, Key-caster automatically detects pure Wayland and uses native Wayland popups:
```bash
keycaster --platform wayland
```

## Features

- **Non-root execution**: Runs cleanly as a regular user via the Linux `input` group.
- **Wayland & X11 Native Support**: Seamless operation under COSMIC, Hyprland, Sway, GNOME, KDE, and X11 with automatic platform detection and zero screen-tiling interference.
- **Configuration Persistence**: Automatically saves and restores window coordinates, screen position, layout override, and opacity in `~/.config/key-caster/config.toml`.
- **Privacy & Sensitive Input Protection**: Toggle global capture pause (`Super+Shift+P` / `Alt+Shift+P`) or privacy masking mode (`Super+Shift+S` / `Alt+Shift+S`) to protect passwords and credentials during screen recordings and livestreams.
- **Per-Device Layout Routing**: In `auto` mode, keystrokes are automatically mapped based on the physical hardware device. An internal laptop keyboard (ABNT2 / ThinkPad) and an external USB keyboard (US-Intl / ANSI) can be used simultaneously with accurate keycaps and dead keys.
- **Mac Typography**: Renders modifier keys with clean symbols (`⇧`, `⌃`, `⌥`, `⌘`) and action keys (`⌫`, `⌦`, `↩`, `⇥`, `⎋`, `⎙`).
- **Context Menu**: Right-click the overlay to clear keys, toggle auto-hide, pause/resume capturing, toggle privacy masking, change screen position presets, adjust opacity, or override keyboard layouts.
- **Draggable with Screen Clamping**: Left-click and drag the overlay anywhere. Movement is automatically clamped to visible monitor boundaries so the widget never gets lost off-screen across single or multi-display setups.

## License & Credits

Distributed under the GNU General Public License v3.0.
Originally created by [bm-mit](https://github.com/bm-mit/key-caster).
