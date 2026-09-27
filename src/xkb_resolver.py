"""
XKB Key Resolver for Linux / Wayland / COSMIC desktop.
Translates Linux evdev scancodes into accurate characters and symbols
based on the active system keyboard layout (RMLVO).
"""

import ctypes
import os
import re
import subprocess
from typing import Any, Dict, Optional


def get_system_rmlvo(user_layout: str = "auto") -> Dict[str, Optional[bytes]]:
    """
    Detects the active system keyboard configuration (RMLVO).
    Checks COSMIC Desktop config, active Xwayland/setxkbmap layout, and localectl.
    """
    rmlvo: Dict[str, Optional[str]] = {
        "rules": None,
        "model": None,
        "layout": "us",
        "variant": "alt-intl",
        "options": None,
    }

    # 1. Parse COSMIC layout/variant configured pairs
    cosmic_file = os.path.expanduser(
        "~/.config/cosmic/com.system76.CosmicComp/v1/xkb_config"
    )
    cosmic_pairs = []
    cosmic_options = None
    if os.path.isfile(cosmic_file):
        try:
            with open(cosmic_file, "r", encoding="utf-8") as f:
                content = f.read()
            lm = re.search(r'layout:\s*"([^"]*)"', content)
            vm = re.search(r'variant:\s*"([^"]*)"', content)
            om = re.search(r'options:\s*Some\("([^"]*)"\)', content)
            if om and om.group(1):
                cosmic_options = om.group(1)
            layouts = [x.strip() for x in lm.group(1).split(",")] if lm else []
            variants = [x.strip() for x in vm.group(1).split(",")] if vm else []
            while len(variants) < len(layouts):
                variants.append("")
            cosmic_pairs = list(zip(layouts, variants))
        except Exception:
            pass

    # 2. Query active layout from setxkbmap (active under Xwayland / desktop)
    active_layout = None
    try:
        out = subprocess.check_output(
            ["setxkbmap", "-query"],
            universal_newlines=True,
            stderr=subprocess.DEVNULL,
        )
        for line in out.splitlines():
            if line.startswith("layout:"):
                active_layout = line.split(":", 1)[1].strip()
                break
    except Exception:
        pass

    # Match active layout with COSMIC configured pairs
    matched = False
    if active_layout and cosmic_pairs:
        for l, v in cosmic_pairs:
            if l == active_layout:
                rmlvo["layout"] = l
                rmlvo["variant"] = v
                rmlvo["options"] = cosmic_options
                matched = True
                break

    if not matched:
        if cosmic_pairs:
            rmlvo["layout"] = cosmic_pairs[0][0]
            rmlvo["variant"] = cosmic_pairs[0][1]
            rmlvo["options"] = cosmic_options
        else:
            try:
                out = subprocess.check_output(
                    ["localectl", "status"],
                    universal_newlines=True,
                    stderr=subprocess.DEVNULL,
                )
                for line in out.splitlines():
                    line = line.strip()
                    if line.startswith("X11 Layout:"):
                        rmlvo["layout"] = line.split(":", 1)[1].strip().split(",")[0]
                    elif line.startswith("X11 Variant:"):
                        rmlvo["variant"] = line.split(":", 1)[1].strip().split(",")[0]
                    elif line.startswith("X11 Options:"):
                        rmlvo["options"] = line.split(":", 1)[1].strip()
            except Exception:
                pass

    # Apply explicit user layout override if specified
    if user_layout and user_layout != "auto":
        clean_l = user_layout.lower().strip()
        if clean_l in ("abnt2", "br"):
            rmlvo["layout"] = "br"
            rmlvo["variant"] = "thinkpad" if any("thinkpad" in v for _, v in cosmic_pairs) else "abnt2"
        elif clean_l in ("us-intl", "intl", "alt-intl"):
            rmlvo["layout"] = "us"
            rmlvo["variant"] = "alt-intl"
        elif clean_l == "us":
            rmlvo["layout"] = "us"
            rmlvo["variant"] = ""
        else:
            rmlvo["layout"] = clean_l

    return {
        k: (v.encode("utf-8") if isinstance(v, str) and v else None)
        for k, v in rmlvo.items()
    }


class XkbResolver:
    DEAD_KEYS: Dict[str, str] = {
        "dead_tilde": "~",
        "dead_circumflex": "^",
        "dead_acute": "´",
        "dead_grave": "`",
        "dead_diaeresis": "¨",
        "dead_cedilla": "¸",
        "dead_macron": "¯",
        "dead_breve": "˘",
        "dead_abovedot": "˙",
        "dead_ogonek": "˛",
        "dead_caron": "ˇ",
        "dead_doubleacute": "˝",
        "dead_perispomeni": "~",
    }

    ACTION_KEYS: Dict[str, str] = {
        "Escape": "⎋",
        "BackSpace": "⌫",
        "Tab": "⇥",
        "ISO_Left_Tab": "⇥",
        "Return": "↩",
        "Delete": "⌦",
        "Caps_Lock": "⇪",
        "Up": "↑",
        "Down": "↓",
        "Left": "←",
        "Right": "→",
        "Home": "↖",
        "End": "↘",
        "Prior": "⇞",
        "Next": "⇟",
        "Print": "⎙",
        "Sys_Req": "⎙",
    }

    MODIFIER_SYMS: Dict[str, str] = {
        "Shift_L": "shift",
        "Shift_R": "shift",
        "Control_L": "ctrl",
        "Control_R": "ctrl",
        "Alt_L": "alt",
        "Alt_R": "alt",
        "Super_L": "windows",
        "Super_R": "windows",
        "Meta_L": "windows",
        "Meta_R": "windows",
        "ISO_Level3_Shift": "alt",
    }

    def __init__(self, layout: str = "auto"):
        self.available = False
        self.xkb = None
        self._init_xkb(layout)

    def _init_xkb(self, layout: str):
        try:
            self.xkb = ctypes.CDLL("libxkbcommon.so.0")
        except Exception:
            return

        class xkb_rule_names(ctypes.Structure):
            _fields_ = [
                ("rules", ctypes.c_char_p),
                ("model", ctypes.c_char_p),
                ("layout", ctypes.c_char_p),
                ("variant", ctypes.c_char_p),
                ("options", ctypes.c_char_p),
            ]

        self.RuleNames = xkb_rule_names
        self.xkb.xkb_context_new.restype = ctypes.c_void_p
        self.xkb.xkb_context_new.argtypes = [ctypes.c_int]

        self.xkb.xkb_keymap_new_from_names.restype = ctypes.c_void_p
        self.xkb.xkb_keymap_new_from_names.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(xkb_rule_names),
            ctypes.c_int,
        ]

        self.xkb.xkb_state_new.restype = ctypes.c_void_p
        self.xkb.xkb_state_new.argtypes = [ctypes.c_void_p]

        self.xkb.xkb_state_update_mask.restype = ctypes.c_int
        self.xkb.xkb_state_update_mask.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
        ]

        self.xkb.xkb_keymap_mod_get_index.restype = ctypes.c_uint32
        self.xkb.xkb_keymap_mod_get_index.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

        self.xkb.xkb_state_key_get_one_sym.restype = ctypes.c_uint32
        self.xkb.xkb_state_key_get_one_sym.argtypes = [ctypes.c_void_p, ctypes.c_uint32]

        self.xkb.xkb_keysym_get_name.restype = ctypes.c_int
        self.xkb.xkb_keysym_get_name.argtypes = [
            ctypes.c_uint32,
            ctypes.c_char_p,
            ctypes.c_size_t,
        ]

        self.xkb.xkb_state_key_get_utf8.restype = ctypes.c_int
        self.xkb.xkb_state_key_get_utf8.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_char_p,
            ctypes.c_size_t,
        ]

        rmlvo = get_system_rmlvo(layout)
        names = self.RuleNames(
            rules=rmlvo.get("rules"),
            model=rmlvo.get("model"),
            layout=rmlvo.get("layout"),
            variant=rmlvo.get("variant"),
            options=rmlvo.get("options"),
        )

        ctx = self.xkb.xkb_context_new(0)
        self.keymap = self.xkb.xkb_keymap_new_from_names(ctx, ctypes.byref(names), 0)
        if not self.keymap:
            return

        self.state = self.xkb.xkb_state_new(self.keymap)
        if not self.state:
            return

        self.shift_idx = self.xkb.xkb_keymap_mod_get_index(self.keymap, b"Shift")
        self.current_rmlvo = rmlvo
        self.available = True

    def resolve(self, scan_code: int, is_shift: bool = False) -> Optional[Dict[str, str]]:
        """
        Resolves an evdev scancode into a structured key descriptor.
        Returns:
            {"type": "modifier"|"space"|"action"|"char", "name": str}
        """
        if not self.available or scan_code <= 0:
            return None

        # +8 no scancode do evdev porque o XKB inventou esse offset nos anos 80
        # e ate hoje a gente tem que carregar esse legado do c#@!
        xkb_code = scan_code + 8
        mod_mask = (1 << self.shift_idx) if is_shift else 0
        self.xkb.xkb_state_update_mask(self.state, mod_mask, 0, 0, 0, 0, 0)

        sym = self.xkb.xkb_state_key_get_one_sym(self.state, xkb_code)
        if not sym:
            return None

        name_buf = ctypes.create_string_buffer(64)
        self.xkb.xkb_keysym_get_name(sym, name_buf, 64)
        sym_name = name_buf.value.decode("utf-8", errors="ignore")

        if sym_name in self.MODIFIER_SYMS:
            return {"type": "modifier", "name": self.MODIFIER_SYMS[sym_name]}

        if sym_name == "space":
            return {"type": "space", "name": "space"}

        if sym_name in self.ACTION_KEYS:
            return {"type": "action", "name": self.ACTION_KEYS[sym_name]}

        # Dead keys nao cospem UTF-8 direto nessa p#@!, xkb_state_key_get_utf8 retorna vazio.
        # Tem que traduzir na marra:
        if sym_name in self.DEAD_KEYS:
            return {"type": "char", "name": self.DEAD_KEYS[sym_name]}

        utf_buf = ctypes.create_string_buffer(64)
        ret = self.xkb.xkb_state_key_get_utf8(self.state, xkb_code, utf_buf, 64)
        if ret > 0:
            val = utf_buf.value.decode("utf-8", errors="ignore")
            if val and val.isprintable() and not val.isspace():
                return {"type": "char", "name": val}

        # Fallback to symbol name if printable and clean
        if sym_name and not sym_name.startswith("dead_") and sym_name != "unknown":
            return {"type": "char", "name": sym_name}

        return None
