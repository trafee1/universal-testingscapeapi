import concurrent.futures
from datetime import datetime, timezone
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

# ---------------------------------------------------------
# Environment Parsers & Utilities (Case-Insensitive)
# ---------------------------------------------------------
ENV_MAP = {k.upper(): v for k, v in os.environ.items()}

def get_env(key: str, default: str = "") -> str:
    return ENV_MAP.get(key.upper(), default).strip()

def parse_num(val_str: str, default: float) -> float:
    try:
        return float(val_str.strip())
    except (ValueError, TypeError):
        return default

def parse_range(var_name: str, default_min: float, default_max: float):
    raw_val = get_env(var_name)
    if not raw_val:
        return default_min, default_max
    try:
        parts = [p.strip() for p in raw_val.split(",") if p.strip()]
        if len(parts) >= 2:
            return parse_num(parts[0], default_min), parse_num(parts[1], default_max)
        elif len(parts) == 1:
            val = parse_num(parts[0], default_min)
            return val, val
    except Exception:
        print(f"[WARN] Invalid range in '{var_name}' ('{raw_val}'). Using defaults ({default_min}, {default_max}).")
    return default_min, default_max

def parse_bool(var_name: str, default: bool = False) -> bool:
    val = get_env(var_name)
    if not val:
        return default
    return val.lower() in ("true", "1", "yes", "on", "enable")

def parse_list(var_name: str, defaults: list) -> list:
    raw_val = get_env(var_name)
    if not raw_val and not var_name.endswith("S"):
        raw_val = get_env(f"{var_name}S")
    elif not raw_val and var_name.endswith("S"):
        raw_val = get_env(var_name[:-1])

    if not raw_val:
        return defaults
    items = [item.strip() for item in raw_val.split(",") if item.strip()]
    return items if items else defaults

def truncate_url(url: str, head_len: int = 18, tail_len: int = 14) -> str:
    if len(url) <= (head_len + tail_len + 5):
        return url
    return f"{url[:head_len]}...{url[-tail_len:]}"

def parse_native_ratio(var_name: str, default_pct: float = 80.0) -> float:
    raw = get_env(var_name)
    if not raw:
        return default_pct / 100.0
    try:
        if "," in raw:
            val = float(raw.split(",")[0].strip())
        else:
            val = float(raw.strip())
        if val > 1.0:
            return min(1.0, max(0.0, val / 100.0))
        return min(1.0, max(0.0, val))
    except Exception:
        return default_pct / 100.0


# =========================================================
# MANUAL USER AGENT POOLS (AUTHENTIC TOKENS LINE BY LINE)
# =========================================================

# --- WINDOWS CHROME (Native to Windows/PC) ---
WIN_CHROME_HIGH = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
]
WIN_CHROME_MID = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
]
WIN_CHROME_LOW = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

# --- WINDOWS EDGE (Microsoft Native) ---
WIN_EDGE_HIGH = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36 Edg/153.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36 Edg/152.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
]
WIN_EDGE_MID = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
]
WIN_EDGE_LOW = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
]

# --- WINDOWS FIREFOX ---
WIN_FF_HIGH = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:152.0) Gecko/20100101 Firefox/152.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0",
]
WIN_FF_MID = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
]
WIN_FF_LOW = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

# --- WINDOWS OPERA ---
WIN_OPERA_HIGH = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 OPR/117.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 OPR/115.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 OPR/112.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 OPR/110.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 OPR/106.0.0.0",
]
WIN_OPERA_MID = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 OPR/104.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 OPR/102.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/101.0.0.0",
]
WIN_OPERA_LOW = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 OPR/98.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 OPR/94.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 OPR/91.0.0.0",
]

# --- MACOS SAFARI (Apple Native) ---
MAC_SAFARI_HIGH = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]
MAC_SAFARI_MID = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]
MAC_SAFARI_LOW = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Safari/605.1.15",
]

# --- MACOS CHROME ---
MAC_CHROME_HIGH = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
]
MAC_CHROME_MID = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
]
MAC_CHROME_LOW = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]

# --- MACOS FIREFOX ---
MAC_FF_HIGH = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:152.0) Gecko/20100101 Firefox/152.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:149.0) Gecko/20100101 Firefox/149.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:146.0) Gecko/20100101 Firefox/146.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:143.0) Gecko/20100101 Firefox/143.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:140.0) Gecko/20100101 Firefox/140.0",
]
MAC_FF_MID = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:138.0) Gecko/20100101 Firefox/138.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:136.0) Gecko/20100101 Firefox/136.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0",
]
MAC_FF_LOW = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
]

# --- MACOS OPERA ---
MAC_OPERA_ALL = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 OPR/116.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 OPR/113.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 OPR/110.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 OPR/106.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 OPR/102.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 OPR/98.0.0.0",
]

# --- LINUX CHROME / FIREFOX ---
LINUX_CHROME_HIGH = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
]
LINUX_CHROME_MID = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
]
LINUX_CHROME_LOW = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]
LINUX_FF_HIGH = [
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:149.0) Gecko/20100101 Firefox/149.0",
    "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
]
LINUX_FF_MID = [
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:138.0) Gecko/20100101 Firefox/138.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0",
]
LINUX_FF_LOW = [
    "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]
LINUX_OPERA_ALL = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 OPR/114.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 OPR/110.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 OPR/106.0.0.0",
]

# --- IOS SAFARI (Apple Mobile Native) ---
IOS_SAFARI_HIGH = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.7 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
]
IOS_SAFARI_MID = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]
IOS_SAFARI_LOW = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
]

# --- IOS SECONDARY (CriOS, FxiOS, OPT) ---
IOS_CHROME_HIGH = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/152.0.0.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/150.0.0.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/148.0.0.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/145.0.0.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/142.0.0.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/140.0.0.0 Mobile/15E148 Safari/604.1",
]
IOS_CHROME_MID = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/139.0.0.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/137.0.0.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/135.0.0.0 Mobile/15E148 Safari/604.1",
]
IOS_CHROME_LOW = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/132.0.0.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/128.0.0.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/125.0.0.0 Mobile/15E148 Safari/604.1",
]
IOS_FF_ALL = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/150.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/146.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/142.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/138.0 Mobile/15E148 Safari/604.1",
]
IOS_OPERA_ALL = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) OPT/5.2.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) OPT/5.0.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) OPT/4.8.0 Mobile/15E148 Safari/604.1",
]

# --- ANDROID CHROME (Google Android Native) ---
ANDROID_CHROME_HIGH = [
    "Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 15; SM-S938B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; CPH2573) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-A556B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36",
]
ANDROID_CHROME_MID = [
    "Mozilla/5.0 (Linux; Android 13; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; 2210132G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36",
]
ANDROID_CHROME_LOW = [
    "Mozilla/5.0 (Linux; Android 12; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36",
]

# --- ANDROID SAMSUNG INTERNET ---
ANDROID_SAMSUNG_HIGH = [
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/26.0 Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S921B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/25.0 Chrome/121.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-A556B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/25.0 Chrome/121.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/24.0 Chrome/117.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/24.0 Chrome/117.0.0.0 Mobile Safari/537.36",
]
ANDROID_SAMSUNG_MID = [
    "Mozilla/5.0 (Linux; Android 13; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/23.0 Chrome/115.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/22.0 Chrome/111.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/21.0 Chrome/110.0.0.0 Mobile Safari/537.36",
]
ANDROID_SAMSUNG_LOW = [
    "Mozilla/5.0 (Linux; Android 11; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/20.0 Chrome/106.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; SM-A515F) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/19.0 Chrome/102.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/18.0 Chrome/99.0.0.0 Mobile Safari/537.36",
]

# --- ANDROID FIREFOX (Strict Handheld Mobile Token) ---
ANDROID_FF_ALL = [
    "Mozilla/5.0 (Android 15; Mobile; rv:152.0) Gecko/152.0 Firefox/152.0",
    "Mozilla/5.0 (Android 15; Mobile; rv:150.0) Gecko/150.0 Firefox/150.0",
    "Mozilla/5.0 (Android 14; Mobile; rv:148.0) Gecko/148.0 Firefox/148.0",
    "Mozilla/5.0 (Android 14; Mobile; rv:146.0) Gecko/146.0 Firefox/146.0",
    "Mozilla/5.0 (Android 14; Mobile; rv:144.0) Gecko/144.0 Firefox/144.0",
    "Mozilla/5.0 (Android 14; Mobile; rv:142.0) Gecko/142.0 Firefox/142.0",
    "Mozilla/5.0 (Android 13; Mobile; rv:140.0) Gecko/140.0 Firefox/140.0",
    "Mozilla/5.0 (Android 13; Mobile; rv:138.0) Gecko/138.0 Firefox/138.0",
    "Mozilla/5.0 (Android 13; Mobile; rv:136.0) Gecko/136.0 Firefox/136.0",
    "Mozilla/5.0 (Android 12; Mobile; rv:134.0) Gecko/134.0 Firefox/134.0",
    "Mozilla/5.0 (Android 12; Mobile; rv:130.0) Gecko/130.0 Firefox/130.0",
    "Mozilla/5.0 (Android 11; Mobile; rv:128.0) Gecko/128.0 Firefox/128.0",
]

# --- ANDROID OPERA (Strict Handheld Mobile Token) ---
ANDROID_OPERA_ALL = [
    "Mozilla/5.0 (Linux; Android 15; SM-S938B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Mobile Safari/537.36 OPR/88.0.0.0",
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36 OPR/86.0.0.0",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36 OPR/84.0.0.0",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36 OPR/82.0.0.0",
    "Mozilla/5.0 (Linux; Android 13; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Mobile Safari/537.36 OPR/79.0.0.0",
    "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36 OPR/75.0.0.0",
]


# ---------------------------------------------------------
# Dynamic Sampling (65% High, 25% Mid, 10% Low)
# ---------------------------------------------------------
def sample_weighted_browser(high_list, mid_list, low_list):
    roll = random.random()
    if roll < 0.65 and high_list:
        return random.choice(high_list)
    elif roll < 0.90 and mid_list:
        return random.choice(mid_list)
    elif low_list:
        return random.choice(low_list)
    combined = high_list + mid_list + low_list
    return random.choice(combined) if combined else ""


# ---------------------------------------------------------
# Deterministic AST Parser for DEVICE_TYPE Hierarchy
# ---------------------------------------------------------
def tokenize_balanced_blocks(s: str) -> list:
    tokens = []
    depth = 0
    buf = []
    for ch in s:
        if ch == '{':
            depth += 1
            buf.append(ch)
        elif ch == '}':
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch == ',' and depth == 0:
            token = "".join(buf).strip()
            if token:
                tokens.append(token)
            buf = []
        else:
            buf.append(ch)
    last = "".join(buf).strip()
    if last:
        tokens.append(last)
    return tokens

def parse_nested_device_spec(spec_str: str) -> dict:
    spec_str = spec_str.strip()
    if not spec_str:
        return {
            "mobile": {"android": ["chrome", "samsung", "firefox", "opera"], "ios": ["safari", "chrome", "firefox", "opera"]},
            "desktop": {"windows": ["chrome", "edge", "firefox", "opera"], "mac": ["safari", "chrome", "firefox", "opera"], "linux": ["chrome", "firefox", "opera"]}
        }

    tree = {}
    cat_blocks = tokenize_balanced_blocks(spec_str)

    for block in cat_blocks:
        match = re.match(r"^([a-zA-Z]+)(?:\{(.*)\})?$", block, re.DOTALL)
        if not match:
            continue
        cat = match.group(1).lower().strip()
        body = match.group(2)

        if cat not in ("mobile", "desktop"):
            continue

        tree[cat] = {}

        if not body:
            if cat == "mobile":
                tree[cat] = {"android": ["chrome", "samsung", "firefox", "opera"], "ios": ["safari", "chrome", "firefox", "opera"]}
            else:
                tree[cat] = {"windows": ["chrome", "edge", "firefox", "opera"], "mac": ["safari", "chrome", "firefox", "opera"], "linux": ["chrome", "firefox", "opera"]}
            continue

        os_blocks = tokenize_balanced_blocks(body)
        for os_blk in os_blocks:
            os_match = re.match(r"^([a-zA-Z]+)(?:\{(.*)\})?$", os_blk, re.DOTALL)
            if not os_match:
                continue
            os_name = os_match.group(1).lower().strip()
            b_body = os_match.group(2)

            if b_body:
                browsers = [b.strip().lower() for b in tokenize_balanced_blocks(b_body) if b.strip()]
            else:
                if os_name == "windows":
                    browsers = ["chrome", "edge", "firefox", "opera"]
                elif os_name in ("mac", "macos"):
                    browsers = ["safari", "chrome", "firefox", "opera"]
                elif os_name == "linux":
                    browsers = ["chrome", "firefox", "opera"]
                elif os_name == "ios":
                    browsers = ["safari", "chrome", "firefox", "opera"]
                elif os_name == "android":
                    browsers = ["chrome", "samsung", "firefox", "opera"]
                else:
                    browsers = ["chrome"]

            tree[cat][os_name] = browsers

    if not tree or not any(tree.values()):
        tree = {"mobile": {"android": ["chrome", "firefox"]}}

    return tree

RAW_DEVICE_SPEC = get_env("DEVICE_TYPE", "desktop,mobile")
DEVICE_TREE = parse_nested_device_spec(RAW_DEVICE_SPEC)
NATIVE_RATIO = parse_native_ratio("BROWSER_NATIVE_RATIO", default_pct=80.0)


# ---------------------------------------------------------
# Custom User-Agent Validator
# ---------------------------------------------------------
def validate_ua_entries(uas: list, expected_scope: str):
    desktop_signatures = ["windows nt", "macintosh", "x11; linux x86_64", "fedora", "ubuntu"]
    mobile_signatures = ["mobile", "android", "iphone", "ipad", "crios", "fxios"]

    for idx, ua in enumerate(uas, start=1):
        ua_clean = ua.lower()
        if expected_scope == "mobile":
            has_desktop = any(d in ua_clean for d in desktop_signatures)
            is_mobile = any(m in ua_clean for m in mobile_signatures)
            if has_desktop and not is_mobile:
                print("\n" + "#" * 70)
                print(" [PINNED CRITICAL ERROR] INVALID USER-AGENT CONFLICT!")
                print(f" Item #{idx} in MOBILE_USER_AGENTS has DESKTOP signatures:")
                print(f" String: {ua}")
                print(" Execution terminated to prevent platform header corruption.")
                print("#" * 70 + "\n")
                sys.exit(1)

        elif expected_scope == "desktop":
            is_mobile = any(m in ua_clean for m in mobile_signatures)
            if is_mobile and "ipad" not in ua_clean:
                print("\n" + "#" * 70)
                print(" [PINNED CRITICAL ERROR] INVALID USER-AGENT CONFLICT!")
                print(f" Item #{idx} in DESKTOP_USER_AGENTS has MOBILE signatures:")
                print(f" String: {ua}")
                print(" Execution terminated to prevent platform header corruption.")
                print("#" * 70 + "\n")
                sys.exit(1)

CUSTOM_DESKTOP_UAS = parse_list("DESKTOP_USER_AGENTS", [])
CUSTOM_MOBILE_UAS = parse_list("MOBILE_USER_AGENTS", [])

if CUSTOM_DESKTOP_UAS:
    validate_ua_entries(CUSTOM_DESKTOP_UAS, "desktop")
if CUSTOM_MOBILE_UAS:
    validate_ua_entries(CUSTOM_MOBILE_UAS, "mobile")


# ---------------------------------------------------------
# Native Browser Weighted Resolver
# ---------------------------------------------------------
NATIVE_BROWSER_MAP = {
    "ios": "safari",
    "android": "chrome",
    "windows": "chrome",
    "mac": "safari",
    "macos": "safari",
    "linux": "chrome"
}

def pick_browser_for_os(os_name: str, allowed_browsers: list, native_pct: float) -> str:
    if len(allowed_browsers) == 1:
        return allowed_browsers[0]

    native_name = NATIVE_BROWSER_MAP.get(os_name, "")
    if native_name and native_name in allowed_browsers:
        other_browsers = [b for b in allowed_browsers if b != native_name]
        if other_browsers and random.random() < native_pct:
            return native_name
        elif other_browsers:
            return random.choice(other_browsers)
        return native_name

    return random.choice(allowed_browsers)


# ---------------------------------------------------------
# Isolated UA Resolver (Strict Category Guarantees)
# ---------------------------------------------------------
def get_ua_for_selection(category: str, os_name: str, browser: str) -> tuple:
    if category == "mobile" and CUSTOM_MOBILE_UAS:
        return random.choice(CUSTOM_MOBILE_UAS), "Custom:Mobile"
    if category == "desktop" and CUSTOM_DESKTOP_UAS:
        return random.choice(CUSTOM_DESKTOP_UAS), "Custom:Desktop"

    # Strict Mobile Routing
    if category == "mobile":
        if os_name == "android":
            if browser == "firefox":
                return random.choice(ANDROID_FF_ALL), "Android:Firefox"
            elif browser == "samsung":
                return sample_weighted_browser(ANDROID_SAMSUNG_HIGH, ANDROID_SAMSUNG_MID, ANDROID_SAMSUNG_LOW), "Android:Samsung"
            elif browser == "opera":
                return random.choice(ANDROID_OPERA_ALL), "Android:Opera"
            elif browser == "chrome":
                return sample_weighted_browser(ANDROID_CHROME_HIGH, ANDROID_CHROME_MID, ANDROID_CHROME_LOW), "Android:Chrome"
            return random.choice(ANDROID_FF_ALL), "Android:Firefox"

        elif os_name == "ios":
            if browser == "firefox":
                return random.choice(IOS_FF_ALL), "iOS:Firefox"
            elif browser == "chrome":
                return sample_weighted_browser(IOS_CHROME_HIGH, IOS_CHROME_MID, IOS_CHROME_LOW), "iOS:Chrome"
            elif browser == "opera":
                return random.choice(IOS_OPERA_ALL), "iOS:Opera"
            elif browser == "safari":
                return sample_weighted_browser(IOS_SAFARI_HIGH, IOS_SAFARI_MID, IOS_SAFARI_LOW), "iOS:Safari"
            return sample_weighted_browser(IOS_SAFARI_HIGH, IOS_SAFARI_MID, IOS_SAFARI_LOW), "iOS:Safari"

        return random.choice(ANDROID_FF_ALL), "Android:Firefox"

    # Strict Desktop Routing
    if category == "desktop":
        if os_name == "windows":
            if browser == "firefox":
                return sample_weighted_browser(WIN_FF_HIGH, WIN_FF_MID, WIN_FF_LOW), "Win:Firefox"
            elif browser == "edge":
                return sample_weighted_browser(WIN_EDGE_HIGH, WIN_EDGE_MID, WIN_EDGE_LOW), "Win:Edge"
            elif browser == "opera":
                return sample_weighted_browser(WIN_OPERA_HIGH, WIN_OPERA_MID, WIN_OPERA_LOW), "Win:Opera"
            elif browser == "chrome":
                return sample_weighted_browser(WIN_CHROME_HIGH, WIN_CHROME_MID, WIN_CHROME_LOW), "Win:Chrome"
            return sample_weighted_browser(WIN_CHROME_HIGH, WIN_CHROME_MID, WIN_CHROME_LOW), "Win:Chrome"

        elif os_name in ("mac", "macos"):
            if browser == "safari":
                return sample_weighted_browser(MAC_SAFARI_HIGH, MAC_SAFARI_MID, MAC_SAFARI_LOW), "Mac:Safari"
            elif browser == "chrome":
                return sample_weighted_browser(MAC_CHROME_HIGH, MAC_CHROME_MID, MAC_CHROME_LOW), "Mac:Chrome"
            elif browser == "firefox":
                return sample_weighted_browser(MAC_FF_HIGH, MAC_FF_MID, MAC_FF_LOW), "Mac:Firefox"
            elif browser == "opera":
                return random.choice(MAC_OPERA_ALL), "Mac:Opera"
            return sample_weighted_browser(MAC_SAFARI_HIGH, MAC_SAFARI_MID, MAC_SAFARI_LOW), "Mac:Safari"

        elif os_name == "linux":
            if browser == "firefox":
                return sample_weighted_browser(LINUX_FF_HIGH, LINUX_FF_MID, LINUX_FF_LOW), "Linux:Firefox"
            elif browser == "opera":
                return random.choice(LINUX_OPERA_ALL), "Linux:Opera"
            return sample_weighted_browser(LINUX_CHROME_HIGH, LINUX_CHROME_MID, LINUX_CHROME_LOW), "Linux:Chrome"

        return sample_weighted_browser(WIN_CHROME_HIGH, WIN_CHROME_MID, WIN_CHROME_LOW), "Win:Chrome"

    return sample_weighted_browser(WIN_CHROME_HIGH, WIN_CHROME_MID, WIN_CHROME_LOW), "Win:Chrome"


def resolve_cycle_ua(used_uas_in_cycle: set) -> tuple:
    cats = list(DEVICE_TREE.keys())
    cat = random.choice(cats) if cats else "mobile"

    sub_os_dict = DEVICE_TREE.get(cat, {})
    if not sub_os_dict:
        sub_os_dict = {"android": ["chrome"]} if cat == "mobile" else {"windows": ["chrome"]}

    chosen_os = random.choice(list(sub_os_dict.keys()))
    allowed_browsers = sub_os_dict.get(chosen_os, ["chrome"])
    
    # Select browser according to 80% native vs other rule
    chosen_browser = pick_browser_for_os(chosen_os, allowed_browsers, NATIVE_RATIO)

    ua, label = "", ""
    for _ in range(15):
        ua, label = get_ua_for_selection(cat, chosen_os, chosen_browser)
        if ua not in used_uas_in_cycle:
            break

    used_uas_in_cycle.add(ua)
    return cat, ua, label


# =========================================================
# OFFICIAL SCRAPERAPI STANDARD MASTER GEOS & TIER DEFAULTS
# =========================================================
# The official standard geotargeting countries supported on all basic/standard keys
OFFICIAL_STANDARD_SCRAPERAPI = {
    "ar": "Argentina",
    "au": "Australia",
    "at": "Austria",
    "be": "Belgium",
    "br": "Brazil",
    "bg": "Bulgaria",
    "ca": "Canada",
    "cl": "Chile",
    "co": "Colombia",
    "hr": "Croatia",
    "cz": "Czech Republic",
    "dk": "Denmark",
    "fi": "Finland",
    "fr": "France",
    "de": "Germany",
    "gr": "Greece",
    "hk": "Hong Kong",
    "hu": "Hungary",
    "in": "India",
    "id": "Indonesia",
    "ie": "Ireland",
    "il": "Israel",
    "it": "Italy",
    "jp": "Japan",
    "my": "Malaysia",
    "mx": "Mexico",
    "nl": "Netherlands",
    "nz": "New Zealand",
    "no": "Norway",
    "ph": "Philippines",
    "pl": "Poland",
    "pt": "Portugal",
    "ro": "Romania",
    "sa": "Saudi Arabia",
    "sg": "Singapore",
    "sk": "Slovakia",
    "za": "South Africa",
    "kr": "South Korea",
    "es": "Spain",
    "se": "Sweden",
    "ch": "Switzerland",
    "tw": "Taiwan",
    "th": "Thailand",
    "tr": "Turkey",
    "ua": "Ukraine",
    "ae": "United Arab Emirates",
    "gb": "United Kingdom",
    "uk": "United Kingdom",
    "us": "United States",
    "vn": "Vietnam"
}

# Default T1 / T2 / T3 structure preserved when no manual COUNTRY variable is set
DEFAULT_TIER_TABLE = {
    "T1": [
        ("FR", "fr", "France"), ("DE", "de", "Germany"), ("NL", "nl", "Netherlands"),
        ("ES", "es", "Spain"), ("IT", "it", "Italy"), ("PL", "pl", "Poland"),
        ("SE", "se", "Sweden"), ("BR", "br", "Brazil"), ("KR", "kr", "South Korea"),
        ("TR", "tr", "Turkey"), ("VN", "vn", "Vietnam"), ("ID", "id", "Indonesia"),
        ("CA", "ca", "Canada"), ("JP", "jp", "Japan"), ("SG", "sg", "Singapore")
    ],
    "T2": [
        ("US", "us", "United States"), ("GB", "gb", "United Kingdom"),
        ("CZ", "cz", "Czech Republic"), ("RO", "ro", "Romania"),
        ("AE", "ae", "United Arab Emirates"), ("MX", "mx", "Mexico"),
        ("TH", "th", "Thailand"), ("PH", "ph", "Philippines")
    ],
    "T3": [
        ("IN", "in", "India"), ("SA", "sa", "Saudi Arabia"),
        ("HK", "hk", "Hong Kong"), ("TW", "tw", "Taiwan")
    ]
}


# =========================================================
# DYNAMIC COUNTRY PARSER, PINNED AUDIT & RED WARNING ALERT
# =========================================================
def parse_and_validate_country_config(raw_cfg: str):
    inc_raw = set()
    exc_raw = set()
    is_custom_configured = bool(raw_cfg.strip())

    if is_custom_configured:
        tokens = [t.strip() for t in re.split(r",(?![^{]*\})", raw_cfg) if t.strip()]
        for token in tokens:
            match = re.match(r"^(include|exclude)\{([^\}]+)\}$", token, re.IGNORECASE)
            if match:
                mode = match.group(1).lower()
                codes = [c.strip().lower() for c in match.group(2).split(",") if c.strip()]
                if mode == "include":
                    inc_raw.update(codes)
                else:
                    exc_raw.update(codes)
            else:
                codes = [c.strip().lower() for c in token.split(",") if c.strip()]
                inc_raw.update(codes)

    # Detect unsupported or non-standard country inputs
    all_specified = inc_raw.union(exc_raw)
    unsupported_codes = [c for c in all_specified if c not in OFFICIAL_STANDARD_SCRAPERAPI]

    # Red warning alert pinned in stdout
    if unsupported_codes:
        red_start = "\033[91m\033[1m"
        red_end = "\033[0m"
        print(f"\n{red_start}######################################################################{red_end}")
        print(f"{red_start} [PINNED CRITICAL ALERT] NON-STANDARD COUNTRY CODE(S) DETECTED!{red_end}")
        print(f"{red_start}  The following entries are NOT officially standard supported: {unsupported_codes}{red_end}")
        print(f"{red_start}  ScraperAPI standard keys receive HTTP 403 or silently fall back to US.{red_end}")
        print(f"{red_start}  Action: Stripping invalid entries to maintain API key longevity.{red_end}")
        print(f"{red_start}######################################################################{red_end}\n")
        inc_raw.difference_update(unsupported_codes)
        exc_raw.difference_update(unsupported_codes)

    # Contradiction resolution: include wins over exclude
    contradictions = inc_raw.intersection(exc_raw)
    if contradictions:
        print("\n" + "=" * 70)
        print(" [PINNED AUDIT ALERT] COUNTRY CONTRADICTION DETECTED!")
        print(f" Overlapping countries in both include and exclude: {sorted(list(contradictions))}")
        print(" Resolution: Explicitly included countries take precedence.")
        print("=" * 70 + "\n")
        exc_raw.difference_update(contradictions)

    # Build active candidate pool
    filtered_tiers = {"T1": [], "T2": [], "T3": []}
    custom_flat_pool = []

    if not is_custom_configured:
        # Default behavior: T1 (50%), T2 (35%), T3 (15%)
        for tier, pairs in DEFAULT_TIER_TABLE.items():
            for code_upper, code_lower, c_name in pairs:
                filtered_tiers[tier].append((tier, code_upper, code_lower, c_name))
    else:
        # Manual variable configuration: Allow all official Standard ScraperAPI locations
        for code, name in OFFICIAL_STANDARD_SCRAPERAPI.items():
            if exc_raw and code in exc_raw:
                continue
            if inc_raw and code not in inc_raw:
                continue
            custom_flat_pool.append(("STD", code.upper(), code, name))

        if not custom_flat_pool:
            print("\n" + "!" * 70)
            print(" [WARN] No valid countries remaining after filter. Defaulting to US (us).")
            print("!" * 70 + "\n")
            custom_flat_pool = [("STD", "US", "us", "United States")]

    return inc_raw, exc_raw, unsupported_codes, is_custom_configured, filtered_tiers, custom_flat_pool

RAW_COUNTRY_CONF = get_env("COUNTRY", get_env("COUNTRIES", ""))
INC_COUNTRIES, EXC_COUNTRIES, INVALID_INPUT_COUNTRIES, IS_CUSTOM_CONFIGURED, FILTERED_TIERS, CUSTOM_FLAT_POOL = parse_and_validate_country_config(RAW_COUNTRY_CONF)

def print_pinned_country_diagnostic():
    print("=" * 85)
    print("           PINNED SCRAPERAPI STANDARD GEOTARGETING AUDIT")
    print("=" * 85)
    
    # Sort helper to sort tuples by full country name alphabetically
    def sort_by_name(items):
        return sorted(items, key=lambda x: x[1].lower())

    if IS_CUSTOM_CONFIGURED:
        # Get sorted list by country full name
        inc_sorted = sorted([c for c in INC_COUNTRIES if c in OFFICIAL_STANDARD_SCRAPERAPI], 
                            key=lambda c: OFFICIAL_STANDARD_SCRAPERAPI[c].lower())
        exc_sorted = sorted([c for c in EXC_COUNTRIES if c in OFFICIAL_STANDARD_SCRAPERAPI], 
                            key=lambda c: OFFICIAL_STANDARD_SCRAPERAPI[c].lower())
        
        inc_disp = ", ".join([f"{c} ({OFFICIAL_STANDARD_SCRAPERAPI[c]})" for c in inc_sorted]) if inc_sorted else "ALL STANDARD"
        exc_disp = ", ".join([f"{c} ({OFFICIAL_STANDARD_SCRAPERAPI[c]})" for c in exc_sorted]) if exc_sorted else "NONE"
        inv_disp = ", ".join(sorted(list(INVALID_INPUT_COUNTRIES))) if INVALID_INPUT_COUNTRIES else "NONE"
        
        print(f"  * Mode                       : CUSTOM OVERRIDE (COUNTRY variable active)")
        print(f"  * Configured Included Filter : {inc_disp}")
        print(f"  * Configured Excluded Filter : {exc_disp}")
        print(f"  * Rejected / Non-Standard    : {inv_disp}")
        print(f"  * Total Active Rotation Pool : {len(CUSTOM_FLAT_POOL)} locations")
        
        # Display active flat pool line by line left to right, sorted by full country name
        active_sorted = sorted(CUSTOM_FLAT_POOL, key=lambda x: x[3].lower())
        active_formatted = [f"{c[2]} {c[3]}" for c in active_sorted]
        print(f"  * Active Rotation Pool       :")
        for i in range(0, len(active_formatted), 2):
            col1 = active_formatted[i]
            col2 = active_formatted[i+1] if i+1 < len(active_formatted) else ""
            if col2:
                print(f"    {col1:<38} |  {col2}")
            else:
                print(f"    {col1}")
    else:
        # Default Presets sorted alphabetically by full country name
        t1_sorted = sorted(DEFAULT_TIER_TABLE["T1"], key=lambda x: x[2].lower())
        t2_sorted = sorted(DEFAULT_TIER_TABLE["T2"], key=lambda x: x[2].lower())
        t3_sorted = sorted(DEFAULT_TIER_TABLE["T3"], key=lambda x: x[2].lower())

        t1_items = [f"{c[1]} {c[2]}" for c in t1_sorted]
        t2_items = [f"{c[1]} {c[2]}" for c in t2_sorted]
        t3_items = [f"{c[1]} {c[2]}" for c in t3_sorted]

        print(f"  * Mode                       : DEFAULT PRESET (T1: 50% | T2: 35% | T3: 15%)")
        print(f"  * Default Tier 1 (50%)       : {', '.join(t1_items)}")
        print(f"  * Default Tier 2 (35%)       : {', '.join(t2_items)}")
        print(f"  * Default Tier 3 (15%)       : {', '.join(t3_items)}")
        print(f"  * Manual Override Variable   : NONE (Supply COUNTRY or COUNTRIES to override)")

    print("-" * 85)
    print("  * Official Standard Supported Catalog (Sorted by Full Country Name):")
    
    # Sort complete standard catalog by country full name
    sorted_catalog = sorted(OFFICIAL_STANDARD_SCRAPERAPI.items(), key=lambda item: item[1].lower())
    formatted_catalog = [f"{code} {name}" for code, name in sorted_catalog]

    # Two columns formatted line-by-line: Column 1 | Column 2 with fixed spacing
    for i in range(0, len(formatted_catalog), 2):
        col1 = formatted_catalog[i]
        col2 = formatted_catalog[i+1] if i+1 < len(formatted_catalog) else ""
        if col2:
            print(f"    {col1:<38} |  {col2}")
        else:
            print(f"    {col1}")

    print("=" * 85 + "\n")

def pick_country():
    if not IS_CUSTOM_CONFIGURED:
        available_tiers = [t for t in ("T1", "T2", "T3") if FILTERED_TIERS[t]]
        if not available_tiers:
            return "T2", "US", "us", "United States"

        roll = random.random()
        if roll < 0.50 and FILTERED_TIERS.get("T1"):
            return random.choice(FILTERED_TIERS["T1"])
        elif roll < 0.85 and FILTERED_TIERS.get("T2"):
            return random.choice(FILTERED_TIERS["T2"])
        elif FILTERED_TIERS.get("T3"):
            return random.choice(FILTERED_TIERS["T3"])
        t = random.choice(available_tiers)
        return random.choice(FILTERED_TIERS[t])
    else:
        return random.choice(CUSTOM_FLAT_POOL)


# ---------------------------------------------------------
# Dynamic Slug & Link Engine (Non-Repeating per Cycle)
# ---------------------------------------------------------
class CycleLinkDispatcher:
    def __init__(self, raw_links: list, short_template: str):
        self.raw_links = raw_links
        self.short_template = short_template
        self.full_links = []
        self.explicit_short_links = []
        self._categorize()

    def _categorize(self):
        for item in self.raw_links:
            item = item.strip()
            if not item:
                continue

            parsed = urllib.parse.urlparse(item)
            is_url = bool(parsed.scheme and parsed.netloc)
            slug = None

            if is_url:
                query = urllib.parse.parse_qs(parsed.query)
                for param in ("via", "ref", "r", "referral", "aff", "code", "id", "tag"):
                    if param in query and query[param]:
                        slug = query[param][0]
                        break
                if not slug:
                    path_parts = [p for p in parsed.path.split("/") if p]
                    if path_parts:
                        slug = path_parts[-1]

                if not parsed.query and slug and self.short_template and self.short_template in item:
                    self.explicit_short_links.append((item, slug))
                else:
                    self.full_links.append((item, slug if slug else "link"))
            else:
                self.full_links.append((item, item))

    def generate_cycle_batch(self, worker_count: int):
        used_slugs = set()
        used_urls = set()
        tasks = []

        pool = []
        for url, sl in self.full_links:
            pool.append(("FULL", url, sl))
        for url, sl in self.explicit_short_links:
            pool.append(("SHORT_CUSTOM", url, sl))

        random.shuffle(pool)

        def make_short_url(slug: str, reference: str) -> str:
            if not reference:
                return ""
            if "{slug}" in reference:
                return reference.replace("{slug}", slug)
            parsed = urllib.parse.urlparse(reference)
            base_domain = f"{parsed.scheme}://{parsed.netloc}"
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) > 1:
                prefix = "/".join(parts[:-1])
                return f"{base_domain}/{prefix}/{slug}"
            return f"{base_domain}/{slug}"

        for kind, raw_target, slug in pool:
            if len(tasks) >= worker_count:
                break

            if len(pool) >= worker_count:
                if slug in used_slugs or raw_target in used_urls:
                    continue

            final_url = raw_target
            ltype = "DIRECT"

            if kind == "SHORT_CUSTOM":
                ltype = "SHORT (OWN)"
            elif self.short_template and slug:
                roll = random.random()
                short_cand = make_short_url(slug, self.short_template)
                if roll >= 0.86 and short_cand:
                    final_url = short_cand
                    ltype = "SHORT (/)"
                else:
                    ltype = "FULL (?)"

            used_slugs.add(slug)
            used_urls.add(final_url)
            tasks.append((final_url, slug, ltype))

        while len(tasks) < worker_count and pool:
            kind, raw_target, slug = random.choice(pool)
            tasks.append((raw_target, slug, kind))

        return tasks


# ---------------------------------------------------------
# Managed Key Pool
# ---------------------------------------------------------
class ManagedKey:
    def __init__(self, name: str, token: str):
        self.name = name.strip()
        self.token = token.strip()
        self.masked = f"{self.token[:4]}...{self.token[-4:]}" if len(self.token) >= 8 else self.token
        self.tag = f"{self.name} [{self.masked}]"

class KeyPoolManager:
    def __init__(self, raw_str: str):
        self.active_keys = []
        self.dead_keys = []
        self.index = 0

        entries = [k.strip() for k in raw_str.split(",") if k.strip()]
        for idx, entry in enumerate(entries, start=1):
            if ":" in entry:
                name, token = entry.split(":", 1)
                self.active_keys.append(ManagedKey(name, token))
            else:
                self.active_keys.append(ManagedKey(f"Key#{idx}", entry))

    def get_key(self) -> ManagedKey:
        if not self.active_keys:
            return None
        key = self.active_keys[self.index % len(self.active_keys)]
        self.index = (self.index + 1) % len(self.active_keys)
        return key

    def mark_dead(self, key_obj: ManagedKey, reason: str):
        if key_obj in self.active_keys:
            self.active_keys.remove(key_obj)
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            self.dead_keys.append((key_obj, reason, ts))

            print("\n" + "#" * 70)
            print(f" [PINNED ALERT] API KEY DIED / EXHAUSTED CREDITS")
            print(f"  Key Identifier : {key_obj.tag}")
            print(f"  Death Time     : {ts}")
            print(f"  Confirmed Cause: {reason}")
            print(f"  Active Remaining: {len(self.active_keys)} key(s)")
            print("#" * 70 + "\n")

    def print_pinned_status(self):
        if not self.dead_keys:
            return
        print("-" * 70)
        print(" [PINNED AUDIT] PERMANENTLY DEAD KEYS:")
        for k_obj, reason, ts in self.dead_keys:
            print(f"  -> {k_obj.tag} | Died: {ts} | Reason: {reason}")
        print("-" * 70)


# ---------------------------------------------------------
# Global Parameters & Dispatcher Initialization
# ---------------------------------------------------------
RAW_KEYS = get_env("API_KEYS", get_env("SCRAPERAPI_KEYS", ""))
pool = KeyPoolManager(RAW_KEYS)

WORKER_MIN, WORKER_MAX = parse_range("WORKER_COUNT_RANGE", 5, 7)
GAP_MIN, GAP_MAX = parse_range("WORKER_GAP_RANGE", 8.0, 12.0)
CYCLE_MIN, CYCLE_MAX = parse_range("CYCLE_INTERVAL_RANGE", 50.0, 70.0)
POST_WAIT_MIN, POST_WAIT_MAX = parse_range("POST_RESPONSE_WAIT_RANGE", 5.0, 15.0)

BROWSER_RENDERING = get_env("BROWSER_RENDERING", "true").lower()
RESIDENTIAL = parse_bool("RESIDENTIAL", default=False)

DEFAULT_REFERRERS = [
    "none",
    "https://www.google.com/",
    "https://www.youtube.com/",
    "https://t.co/"
]
RAW_REFERRERS = parse_list("REFERRERS", DEFAULT_REFERRERS)
REFERRERS = RAW_REFERRERS if RAW_REFERRERS else DEFAULT_REFERRERS

INPUT_LINKS = parse_list("LINKS", parse_list("TARGET_URLS", parse_list("TARGET_SLUGS", [])))
SHORT_TEMPLATE = get_env("SHORT_LINK_TEMPLATE")
LINK_DISPATCHER = CycleLinkDispatcher(INPUT_LINKS, SHORT_TEMPLATE)

def calculate_credits(render_flag: str, is_residential: bool) -> int:
    is_render = render_flag == "true"
    if is_residential and is_render:
        return 25
    elif is_residential or is_render:
        return 10
    return 1


# ---------------------------------------------------------
# Worker Bot Execution
# ---------------------------------------------------------
def execute_bot(bot_id: int, total_bots: int, target_url: str, slug: str, ltype: str, stagger_delay: float, selected_cat: str, selected_ua: str, os_label: str):
    time.sleep(stagger_delay)

    key_obj = pool.get_key()
    if not key_obj:
        return

    tier_label, c_upper, c_code, c_name = pick_country()
    expected_credits = calculate_credits(BROWSER_RENDERING, RESIDENTIAL)
    truncated_target = truncate_url(target_url, head_len=18, tail_len=14)

    rotation_seed = random.randint(1000000, 9999999)

    params = {
        "api_key": key_obj.token,
        "device_type": selected_cat,
        "country_code": c_code,
        "render": BROWSER_RENDERING,
        "keep_headers": "true",
        "session_number": str(rotation_seed),
        "url": target_url
    }
    if RESIDENTIAL:
        params["premium"] = "true"

    url = f"http://api.scraperapi.com?{urllib.parse.urlencode(params)}"

    headers = {
        "User-Agent": selected_ua,
        "Connection": "close"
    }
    if selected_cat == "mobile":
        headers["Sec-CH-UA-Mobile"] = "?1"
        headers["Sec-CH-UA-Platform"] = '"Android"' if "Android" in selected_ua else '"iOS"'
    else:
        headers["Sec-CH-UA-Mobile"] = "?0"

    chosen_referrer = random.choice(REFERRERS)
    if chosen_referrer and chosen_referrer.lower() not in ("none", "direct", "empty"):
        headers["Referer"] = chosen_referrer
        ref_display = chosen_referrer
    else:
        ref_display = "Direct"

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=65) as resp:
            actual_credits = resp.headers.get("sa-credit-cost", str(expected_credits))
            print(
                f"[Bot-{bot_id}/{total_bots}] [{tier_label}-{c_upper} ({c_name})] [{selected_cat.upper()}:{os_label}] "
                f"[{ltype} {slug}] [Target: {truncated_target}] [Ref: {ref_display}] "
                f"[Credits: ~{actual_credits} cost] [{key_obj.tag}] -> HTTP {resp.status} OK"
            )

    except urllib.error.HTTPError as e:
        raw_detail = e.read().decode("utf-8", errors="ignore")[:100].strip()
        # Protect keys from dying if ScraperAPI returns a plan/tier restriction HTTP 403
        if e.code == 403 and "premium tier" in raw_detail.lower():
            print(f"[Bot-{bot_id}] [{key_obj.tag}] [Target: {truncated_target}] [PLAN LIMIT] {c_upper} ({c_name}) requires Business Tier. Key kept active.")
        elif e.code in (401, 403):
            reason_msg = f"HTTP {e.code} Credits Exhausted / Invalid Key ({raw_detail})"
            pool.mark_dead(key_obj, reason_msg)
        elif e.code == 429:
            print(f"[Bot-{bot_id}] [{key_obj.tag}] [Target: {truncated_target}] [Credits: 0] [TRANSIENT] HTTP 429 Rate limit exceeded")
        else:
            print(f"[Bot-{bot_id}] [{key_obj.tag}] [Target: {truncated_target}] [Credits: 0] [WARN] HTTP {e.code}: {raw_detail}")

    except Exception as ex:
        print(f"[Bot-{bot_id}] [{key_obj.tag}] [Target: {truncated_target}] [Credits: 0] [CLIENT ERROR]: {str(ex)}")

    post_wait = random.uniform(POST_WAIT_MIN, POST_WAIT_MAX)
    gap_wait = random.uniform(GAP_MIN, GAP_MAX)
    time.sleep(post_wait + gap_wait)


# ---------------------------------------------------------
# Main Execution Loop
# ---------------------------------------------------------
def main():
    print("==================================================")
    print("      UNIVERSAL SCRAPER ENGINE RUNTIME            ")
    print("==================================================")

    if not INPUT_LINKS:
        print("\n" + "!" * 70)
        print(" [CONFIG ERROR] NO TARGET LINKS DETECTED!")
        print(" Supply target links via LINKS environment variable.")
        print("!" * 70 + "\n")
        sys.exit(1)

    # Print Pinned Standard Geotargeting Diagnostic Banner with names and codes
    print_pinned_country_diagnostic()

    print(f"Total Active Keys       : {len(pool.active_keys)}")
    print(f"Browser Rendering       : {BROWSER_RENDERING}")
    print(f"Residential Proxies     : {'ENABLED (premium=true)' if RESIDENTIAL else 'DISABLED (Standard DataCenter)'}")
    print(f"Est. Credits Per Hit    : ~{calculate_credits(BROWSER_RENDERING, RESIDENTIAL)} credits")
    print(f"Active Device Hierarchy : {DEVICE_TREE}")
    print(f"Native Browser Weight   : {int(NATIVE_RATIO * 100)}% Native / {int((1.0 - NATIVE_RATIO) * 100)}% Others")
    print(f"Post-Response Cooldown  : {POST_WAIT_MIN:.1f}s - {POST_WAIT_MAX:.1f}s")
    print(f"Worker Gap Interval     : {GAP_MIN:.1f}s - {GAP_MAX:.1f}s")
    print(f"Cycle Interval Range    : {CYCLE_MIN:.1f}s - {CYCLE_MAX:.1f}s")
    print("==================================================\n")

    cycle_num = 1

    try:
        while True:
            if not pool.active_keys:
                print("\n" + "!" * 70)
                print(" [SHUTDOWN] ALL CONFIGURED KEYS HAVE EXHAUSTED CREDITS.")
                pool.print_pinned_status()
                print("!" * 70 + "\n")
                sys.exit(0)

            cycle_start = time.time()
            worker_count = random.randint(int(WORKER_MIN), int(WORKER_MAX))
            target_cycle_time = random.uniform(CYCLE_MIN, CYCLE_MAX)

            print(f"\n--- [Cycle #{cycle_num}] Starting {worker_count} bots | Target: {target_cycle_time:.1f}s | Active Keys: {len(pool.active_keys)} ---")

            tasks = LINK_DISPATCHER.generate_cycle_batch(worker_count)

            # Assign unique User-Agents for each worker in this cycle
            used_uas_this_cycle = set()
            bot_ua_assignments = [resolve_cycle_ua(used_uas_this_cycle) for _ in range(worker_count)]

            with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = []
                for idx, (url, slug, ltype) in enumerate(tasks):
                    stagger = idx * random.uniform(GAP_MIN, GAP_MAX)
                    cat, ua_str, ua_label = bot_ua_assignments[idx]
                    futures.append(
                        executor.submit(
                            execute_bot, idx + 1, worker_count, url, slug, ltype, stagger, cat, ua_str, ua_label
                        )
                    )
                concurrent.futures.wait(futures)

            elapsed = time.time() - cycle_start
            wait_time = target_cycle_time - elapsed

            pool.print_pinned_status()

            if wait_time > 0 and pool.active_keys:
                print(f"--- [Cycle #{cycle_num} Complete] Elapsed: {elapsed:.1f}s | Pausing {wait_time:.1f}s before next round ---")
                time.sleep(wait_time)
            elif pool.active_keys:
                print(f"--- [Cycle #{cycle_num} Complete] Elapsed: {elapsed:.1f}s | Starting next round immediately ---")

            cycle_num += 1

    except KeyboardInterrupt:
        print("\nShutdown signal caught. Exiting.")
        sys.exit(0)

if __name__ == "__main__":
    main()
