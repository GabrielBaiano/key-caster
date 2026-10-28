# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
