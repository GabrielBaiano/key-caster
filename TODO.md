# Project Roadmap & Backlog

Tracking improvements, community feedback, and architectural tasks for Key-caster.

---

## High Priority

- [x] **Privacy & Password Masking** ([#1](https://github.com/GabrielBaiano/key-caster/issues/1))
  - [x] Implement global pause/resume toggle shortcut (`Super+Shift+P` / `Alt+Shift+P`).
  - [x] Add pause toggle in overlay context menu.
  - [x] Add visual paused indicator (`⏸ PAUSED` warning label on the card).
  - [x] Add privacy masking mode (`Super+Shift+S` / `Alt+Shift+S`) converting characters to bullets (`•`).
  - [x] Add `--paused` and `--privacy` CLI flags.

- [x] **Fix USB Keyboard Classification Heuristic** ([#4](https://github.com/GabrielBaiano/key-caster/issues/4))
  - [x] Remove broad keywords (`"keyboard"`, `"usb"`) from `classify_keyboard_device` in `src/xkb_resolver.py`.
  - [x] Fall back to system's active RMLVO layout (`get_system_rmlvo`) when device hardware name is ambiguous.
  - [x] Add unit tests verifying external ABNT2 keyboards are not falsely resolved as `us-intl`.

- [x] **Dynamic Card Width & Text Truncation** ([#7](https://github.com/GabrielBaiano/key-caster/issues/7))
  - [x] Replace `setFixedSize(220, 100)` with `setMinimumWidth(220)` in `MainWindow` and `CentralWidget`.
  - [x] Recalculate card width dynamically based on `fontMetrics().horizontalAdvance(text)`.
  - [x] Clamp width between 220px and 600px with screen anchoring compensation.

---

## Medium Priority

- [x] ~~**Spacebar Retention & Configurable Clearing**~~ ([#5](https://github.com/GabrielBaiano/key-caster/issues/5)) — *Closed as by-design (deliberate token flushing delimiter)*

- [x] **Configuration Persistence** ([#6](https://github.com/GabrielBaiano/key-caster/issues/6))
  - [x] Support loading and saving preferences in `~/.config/key-caster/config.toml`.
  - [x] Persist window coordinates `(x, y)` on drag release and screen presets.
  - [x] Persist layout override, timeout duration, opacity, font size, and max keys.
  - [x] Safe off-screen coordinate recovery for multi-monitor disconnects.

- [x] **Native Wayland & Tiling Support** ([#2](https://github.com/GabrielBaiano/key-caster/issues/2))
  - [x] Implement dynamic platform detection (`--platform {auto,xcb,wayland}`) falling back to native Wayland when Xwayland is absent.
  - [x] Register application identity (`app_id="key-caster"`, `WM_CLASS="key-caster"`).
  - [x] Apply unmanaged popup window flags (`Qt.ToolTip`) under pure Wayland to prevent screen tiling.
  - [x] Document out-of-the-box floating rules for Hyprland and Sway.

---

## Packaging & Distribution

- [x] **Desktop Integration & AUR Package** ([#3](https://github.com/GabrielBaiano/key-caster/issues/3))
  - [x] Create `assets/key-caster.desktop` specification file.
  - [x] Provide 256x256 PNG and scalable SVG app icon.
  - [x] Create `PKGBUILD` for Arch Linux (`key-caster-git`).
  - [x] Add desktop launcher integration instructions to README.md.

- [ ] **International Layouts Expansion**
  - [ ] Add fallback tables for German (QWERTZ), French (AZERTY), and Spanish.
  - [ ] Test dead key resolution for European accent combinations in `XkbResolver`.
