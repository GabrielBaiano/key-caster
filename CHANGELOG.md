# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.1] - 2026-11-09

### Fix
- **Clean Process Teardown**: Ensured background evdev keyboard worker thread terminates properly on `closeEvent` and hooked `os._exit()` to application teardown, preventing orphaned zombie processes from hanging in `btop` and task managers ([#14](https://github.com/GabrielBaiano/key-caster/issues/14)).

## [1.2.0] - 2026-11-09

### Feat
- **Theming & Color Presets**: Added curated theme presets (`Dark (OLED)`, `Catppuccin Mocha`, `Tokyo Night`, `Nord`, `Dracula`, `Gruvbox Dark`, `Light`) accessible via CLI (`--theme`) or the interactive context menu.
- **Custom Theme Configuration**: Added support for custom colors in `~/.config/key-caster/config.toml` under `[custom_theme]`.
- **Card Background Transparency**: Added independent background alpha transparency (`--bg-alpha`, `bg_alpha`) via `rgba` rendering on `CentralWidget` to maintain crisp font rendering without compositor blur.

### Fix
- **Fixed Card Dimensions**: Enforced fixed `220x100` card size to prevent annoying layout shifting and dynamic window growth during typing.
- **Caps Lock Synchronization**: Integrated XKB `Lock` modifier mask with real-time sysfs hardware LED state detection (`/sys/class/leds/*capslock*/brightness`), ensuring accurate capitalization when typing with Caps Lock active.
- **Instant Modifier Key Tracking**: Rewrote modifier state handling using direct Linux evdev scancodes (`29`/`97` Ctrl, `42`/`54` Shift, `56`/`100` Alt, `125`/`126` Super), eliminating off-by-one delays and ensuring modifier indicators (`⇧`, `⌃`, `⌥`, `⌘`) light up and turn off immediately on keypress.
- **Clean Typography**: Preserved original clean font stack (`font-weight: normal`) without experimental bold weights or blur-inducing DPI scaling flags.

## [1.1.1] - 2026-11-03

### Fix
- **Screen Boundary Clamping**: Restricted overlay movement during mouse dragging so the window stays 100% within visible display boundaries across single and multi-monitor setups.
- **Dock & Sticky Atoms**: Added `_NET_WM_WINDOW_TYPE_DOCK`, `_NET_WM_STATE_STICKY`, and all-workspaces atom flags (`_NET_WM_DESKTOP=4294967295`) to prevent tiling window managers and compositors (such as COSMIC auto-tiling) from capturing the overlay as a split tile.
- **Platform Selection Precedence**: Prioritized `xcb` backend whenever `DISPLAY` is detected under Xwayland environments, guaranteeing precise coordinate placement and window layering.

## [1.1.0] - 2026-10-27

### Feat
- **Wayland & Tiling Support**: Added dynamic platform routing (`--platform {auto,xcb,wayland}`), application identity (`app_id="key-caster"`), and unmanaged popup semantics (`Qt.ToolTip`) preventing screen-splitting in Hyprland, Sway, and River ([#2](https://github.com/GabrielBaiano/key-caster/issues/2)).
- **Configuration Persistence**: Added user settings persistence in `~/.config/key-caster/config.toml` (XDG Base Directory compliant) with atomic writing, coordinate restoration, and screen disconnect fallback ([#6](https://github.com/GabrielBaiano/key-caster/issues/6)).
- **Opacity Selector**: Added interactive opacity submenu in the context menu (100%, 90%, 80%, 70%, 50%) with automatic state saving.
- **Privacy & Sensitive Input Masking**: Added global pause shortcuts (`Super+Shift+P` / `Alt+Shift+P`) with `⏸ PAUSED` indicator and privacy masking (`Super+Shift+S` / `Alt+Shift+S`) rendering typed characters as `•` bullets ([#1](https://github.com/GabrielBaiano/key-caster/issues/1)).

### Fix
- **Dynamic Card Resizing**: Replaced fixed width with dynamic width calculation (`fontMetrics().horizontalAdvance + 48`) clamped between 220px and 600px with screen anchoring compensation to prevent long shortcut truncation ([#7](https://github.com/GabrielBaiano/key-caster/issues/7)).
- **USB Keyboard Classification**: Refined keyboard classifier in `xkb_resolver.py` to prevent generic USB devices from being misidentified as US-International, preserving Brazilian ABNT2 dead keys and `ç` ([#4](https://github.com/GabrielBaiano/key-caster/issues/4)).

### Build / Packaging
- **Desktop Entry**: Added FreeDesktop `assets/key-caster.desktop` specification file.
- **Icon Assets**: Created scalable SVG keycap icon (`assets/key-caster.svg`) and 256x256 PNG raster asset (`assets/key-caster.png`).
- **Arch Linux PKGBUILD**: Provided `packaging/arch/PKGBUILD` for AUR packaging (`key-caster-git`) ([#3](https://github.com/GabrielBaiano/key-caster/issues/3)).
- **Package Data**: Registered desktop file and icons under `tool.setuptools.data-files` in `pyproject.toml`.

### Docs
- Documented configuration file structure and CLI arguments (`--config`, `--no-config`, `--platform`).
- Added ready-to-use window rules for Hyprland (`windowrulev2 = float, class:^(key-caster)$`) and Sway (`for_window [app_id="key-caster"] floating enable`).
- Added project roadmap and backlog tracking in `TODO.md`.

## [1.0.0] - 2026-09-30

- Initial release: lightweight on-screen keystroke displayer with non-root evdev input, Mac typography keycaps, and ABNT2/US-Intl shift mappings.
