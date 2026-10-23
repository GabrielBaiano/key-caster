import os
import sys
from typing import Any, Dict, Optional

try:
    import tomllib
except ImportError:
    tomllib = None  # Fallback for Python < 3.11


DEFAULT_CONFIG: Dict[str, Any] = {
    "position": "bottom-right",
    "custom_x": None,
    "custom_y": None,
    "layout": "auto",
    "timeout": 2.0,
    "opacity": 0.92,
    "font_size": 32,
    "max_keys": 5,
    "privacy": False,
    "paused": False,
}

VALID_POSITIONS = {
    "bottom-right",
    "bottom-left",
    "bottom-center",
    "top-right",
    "top-left",
    "top-center",
    "center",
    "custom",
}

VALID_LAYOUTS = {"auto", "abnt2", "br", "us-intl", "intl", "alt-intl", "us"}


def get_default_config_path() -> str:
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        base_dir = os.path.abspath(xdg_config)
    else:
        base_dir = os.path.expanduser("~/.config")
    return os.path.join(base_dir, "key-caster", "config.toml")


def _parse_toml_fallback(content: str) -> Dict[str, Any]:
    """Simple parser for flat key = value TOML files."""
    result: Dict[str, Any] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()

        # Strip inline comments
        if " #" in val:
            val = val.split(" #", 1)[0].strip()

        # Booleans
        if val.lower() == "true":
            result[key] = True
        elif val.lower() == "false":
            result[key] = False
        # Strings
        elif (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            result[key] = val[1:-1]
        # Numbers
        else:
            try:
                if "." in val:
                    result[key] = float(val)
                else:
                    result[key] = int(val)
            except ValueError:
                result[key] = val
    return result


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Loads configuration from file, falling back to DEFAULT_CONFIG on error or absence."""
    target_path = path or get_default_config_path()
    config = dict(DEFAULT_CONFIG)

    if not os.path.isfile(target_path):
        return config

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()

        if tomllib is not None:
            raw = tomllib.loads(content)
        else:
            raw = _parse_toml_fallback(content)

        if not isinstance(raw, dict):
            return config

        # Validate and merge keys
        if "position" in raw and raw["position"] in VALID_POSITIONS:
            config["position"] = str(raw["position"])

        if "custom_x" in raw:
            try:
                config["custom_x"] = int(raw["custom_x"]) if raw["custom_x"] is not None else None
            except (ValueError, TypeError):
                pass

        if "custom_y" in raw:
            try:
                config["custom_y"] = int(raw["custom_y"]) if raw["custom_y"] is not None else None
            except (ValueError, TypeError):
                pass

        if "layout" in raw and str(raw["layout"]).lower() in VALID_LAYOUTS:
            config["layout"] = str(raw["layout"]).lower()

        if "timeout" in raw:
            try:
                t = float(raw["timeout"])
                if t >= 0:
                    config["timeout"] = t
            except (ValueError, TypeError):
                pass

        if "opacity" in raw:
            try:
                o = float(raw["opacity"])
                if 0.1 <= o <= 1.0:
                    config["opacity"] = o
            except (ValueError, TypeError):
                pass

        if "font_size" in raw:
            try:
                fs = int(raw["font_size"])
                if 8 <= fs <= 128:
                    config["font_size"] = fs
            except (ValueError, TypeError):
                pass

        if "max_keys" in raw:
            try:
                mk = int(raw["max_keys"])
                if 1 <= mk <= 30:
                    config["max_keys"] = mk
            except (ValueError, TypeError):
                pass

        if "privacy" in raw:
            config["privacy"] = bool(raw["privacy"])

        if "paused" in raw:
            config["paused"] = bool(raw["paused"])

    except Exception as e:
        print(f"[Key-Caster Warning] Failed to load config from {target_path}: {e}", file=sys.stderr)

    return config


def dump_toml(data: Dict[str, Any]) -> str:
    """Formats configuration dictionary into a clean TOML string."""
    lines = [
        "# Key-caster User Configuration",
        "# Automatically updated on UI movement, layout selection, and opacity changes.",
        "",
    ]
    for key in sorted(data.keys()):
        val = data[key]
        if val is None:
            continue
        if isinstance(val, bool):
            lines.append(f"{key} = {'true' if val else 'false'}")
        elif isinstance(val, float):
            lines.append(f"{key} = {round(val, 2)}")
        elif isinstance(val, int):
            lines.append(f"{key} = {val}")
        elif isinstance(val, str):
            lines.append(f'{key} = "{val}"')
    lines.append("")
    return "\n".join(lines)


def save_config(data: Dict[str, Any], path: Optional[str] = None) -> bool:
    """Saves configuration dictionary to file atomically."""
    target_path = path or get_default_config_path()
    try:
        parent_dir = os.path.dirname(os.path.abspath(target_path))
        os.makedirs(parent_dir, exist_ok=True)

        payload = dump_toml(data)
        temp_path = f"{target_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())

        os.replace(temp_path, target_path)
        return True
    except Exception as e:
        print(f"[Key-Caster Warning] Failed to save config to {target_path}: {e}", file=sys.stderr)
        return False
