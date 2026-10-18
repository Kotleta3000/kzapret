"""Все пути kzapret завязаны на корневую папку установки (там же лежит launcher)."""
from __future__ import annotations

import sys
from pathlib import Path

# .../kzapret/kzapret/paths.py -> ROOT = .../kzapret
ROOT = Path(__file__).resolve().parent.parent

ZAPRET_DIR = ROOT / "zapret"
PROXY_DIR = ROOT / "tg-ws-proxy"

VENV_DIR = ROOT / ".venv"
VENV_PY = VENV_DIR / "Scripts" / "python.exe"

CONFIG_FILE = ROOT / "kzapret.json"
LOG_DIR = ROOT / "logs"

# Репозитории Flowseal
ZAPRET_REPO = "https://github.com/Flowseal/zapret-discord-youtube"
PROXY_REPO = "https://github.com/Flowseal/tg-ws-proxy"

# --- zapret внутренние пути ---
ZAPRET_BIN = ZAPRET_DIR / "bin"
ZAPRET_LISTS = ZAPRET_DIR / "lists"
ZAPRET_UTILS = ZAPRET_DIR / "utils"
ZAPRET_SERVICE = ZAPRET_DIR / "service.bat"
GAME_FILTER_FLAG = ZAPRET_UTILS / "game_filter.enabled"
IPSET_FILE = ZAPRET_LISTS / "ipset-all.txt"
DOMAINS_FILE = ZAPRET_LISTS / "list-general.txt"
IPSET_BACKUP = ZAPRET_LISTS / "ipset-all.txt.backup"
TEST_SCRIPT = ZAPRET_UTILS / "test zapret.ps1"
TARGETS_FILE = ZAPRET_UTILS / "targets.txt"
TEST_RESULTS_DIR = ZAPRET_UTILS / "test results"
ZAPRET_VERSION_FILE = ZAPRET_DIR / ".service" / "version.txt"

# Списки IP zapret обновляются с этого URL (см. service.bat :ipset_update)
IPSET_SERVICE_URL = (
    "https://raw.githubusercontent.com/Flowseal/zapret-discord-youtube"
    "/refs/heads/main/.service/ipset-service.txt"
)
ZAPRET_VERSION_URL = (
    "https://raw.githubusercontent.com/Flowseal/zapret-discord-youtube"
    "/main/.service/version.txt"
)

# --- tg-ws-proxy внутренние пути ---
PROXY_ENTRY = PROXY_DIR / "proxy" / "tg_ws_proxy.py"
PROXY_VERSION_FILE = PROXY_DIR / "proxy" / "__init__.py"
PROXY_LATEST_API = "https://api.github.com/repos/Flowseal/tg-ws-proxy/releases/latest"


def python_for_proxy() -> str:
    """Питон, которым запускаем headless-прокси: venv (там есть cryptography) или текущий."""
    if VENV_PY.exists():
        return str(VENV_PY)
    return sys.executable
