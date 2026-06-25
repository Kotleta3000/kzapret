"""Управление zapret: запуск winws с захватом логов, game filter, ipset, тесты."""
from __future__ import annotations

import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Callable, List, Optional

from . import paths
from .process import ManagedProcess, run_capture

_NO_WINDOW = 0x08000000


def winws_running() -> bool:
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq winws.exe", "/NH"],
            capture_output=True, text=True, errors="replace", creationflags=_NO_WINDOW,
        ).stdout
        return "winws.exe" in out.lower()
    except Exception:  # noqa: BLE001
        return False


def kill_winws(wait: float = 5.0) -> None:
    """Снести любые winws.exe и дождаться, пока реально умрут (иначе новый не стартует)."""
    if not winws_running():
        return
    subprocess.run(["taskkill", "/F", "/IM", "winws.exe", "/T"],
                   capture_output=True, creationflags=_NO_WINDOW)
    deadline = time.time() + wait
    while time.time() < deadline:
        if not winws_running():
            return
        time.sleep(0.2)

# Текст запуска winws во всех general*.bat: start "zapret: %~n0" /min "%BIN%winws.exe" ...
_START_RE = re.compile(
    r'start\s+"[^"]*"\s+/min\s+("%BIN%winws\.exe")', re.IGNORECASE
)
_RUN_BAT = paths.ZAPRET_DIR / ".kzapret_run.bat"
_DUMMY_IP = "203.0.113.113/32"


def installed() -> bool:
    return paths.ZAPRET_SERVICE.exists() and paths.ZAPRET_BIN.exists()


def _natural_key(name: str) -> str:
    return re.sub(r"\d+", lambda m: m.group(0).zfill(8), name)


def list_configs() -> List[str]:
    """Все general*.bat (исключая service*.bat), в том же порядке, что и сам zapret."""
    if not paths.ZAPRET_DIR.exists():
        return []
    bats = [
        p.name
        for p in paths.ZAPRET_DIR.glob("*.bat")
        if not p.name.lower().startswith("service")
        and not p.name.startswith(".kzapret")
    ]
    return sorted(bats, key=_natural_key)


def version() -> Optional[str]:
    try:
        return paths.ZAPRET_VERSION_FILE.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


# ---------- game filter (файл utils/game_filter.enabled) ----------

def get_gamefilter() -> str:
    if not paths.GAME_FILTER_FLAG.exists():
        return "off"
    try:
        first = paths.GAME_FILTER_FLAG.read_text(encoding="utf-8", errors="replace").splitlines()
        val = (first[0].strip().lower() if first else "")
        return val if val in ("all", "tcp", "udp") else "off"
    except OSError:
        return "off"


def set_gamefilter(mode: str) -> None:
    mode = mode.lower()
    if mode in ("off", "none", "disable", "disabled", ""):
        if paths.GAME_FILTER_FLAG.exists():
            paths.GAME_FILTER_FLAG.unlink()
        return
    if mode not in ("all", "tcp", "udp"):
        raise ValueError("gamefilter: ожидается off|tcp|udp|all")
    paths.ZAPRET_UTILS.mkdir(parents=True, exist_ok=True)
    paths.GAME_FILTER_FLAG.write_text(mode + "\n", encoding="ascii")


# ---------- ipset (lists/ipset-all.txt) ----------

def get_ipset_status() -> str:
    """none | loaded | any — по тому же признаку, что и service.bat."""
    if not paths.IPSET_FILE.exists():
        return "none"
    try:
        text = paths.IPSET_FILE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "none"
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) == 0:
        return "any"
    if any(_DUMMY_IP in ln for ln in lines):
        return "none"
    return "loaded"


def set_ipset(enabled: bool, log: Optional[Callable[[str], None]] = None) -> str:
    """on -> полный список (loaded, при необходимости качаем); off -> заглушка (none)."""
    def _say(m: str):
        if log:
            log(m)
    paths.ZAPRET_LISTS.mkdir(parents=True, exist_ok=True)
    if enabled:
        if get_ipset_status() == "loaded":
            return "loaded"
        _say("Скачиваю актуальный ipset-список...")
        try:
            req = urllib.request.Request(
                paths.IPSET_SERVICE_URL, headers={"Cache-Control": "no-cache", "User-Agent": "kzapret"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            paths.IPSET_FILE.write_bytes(data)
            _say("ipset-список обновлён (loaded).")
        except Exception as exc:  # noqa: BLE001
            _say(f"Не удалось скачать список: {exc}. ipset оставлен как есть.")
        return get_ipset_status()
    else:
        # backup текущего (если loaded) и ставим заглушку
        if get_ipset_status() == "loaded" and not paths.IPSET_BACKUP.exists():
            try:
                paths.IPSET_BACKUP.write_bytes(paths.IPSET_FILE.read_bytes())
            except OSError:
                pass
        paths.IPSET_FILE.write_text(_DUMMY_IP + "\n", encoding="ascii")
        return "none"


# ---------- запуск winws с захватом логов ----------

def _build_run_bat(config_name: str) -> None:
    """Берём оригинальный general*.bat и убираем `start /min`, чтобы winws шёл в foreground."""
    src = paths.ZAPRET_DIR / config_name
    text = src.read_text(encoding="utf-8", errors="replace")
    if not _START_RE.search(text):
        raise RuntimeError(
            f"Не нашёл запуск winws в {config_name} — формат конфига изменился."
        )
    patched = _START_RE.sub(r"\1", text)
    _RUN_BAT.write_text(patched, encoding="utf-8")


class ZapretRuntime:
    def __init__(self):
        self.proc = ManagedProcess("zapret")
        self.current_config: Optional[str] = None

    @property
    def running(self) -> bool:
        return self.proc.running

    async def start(self, config_name: str, on_line: Callable[[str], None],
                    on_exit: Optional[Callable[[Optional[int]], None]] = None) -> None:
        await self.stop()
        # winws отказывается стартовать, если уже есть копия с тем же фильтром —
        # сносим любые висящие winws (от старого запуска / прошлой сессии) и ждём смерти.
        kill_winws()
        _build_run_bat(config_name)
        env = os.environ.copy()
        env["NO_UPDATE_CHECK"] = "1"  # глушим автопроверку обновлений внутри bat
        self.current_config = config_name
        await self.proc.start(
            ["cmd", "/c", str(_RUN_BAT)],
            cwd=str(paths.ZAPRET_DIR),
            on_line=on_line,
            on_exit=on_exit,
            env=env,
            kill_names=["winws.exe"],
        )

    async def stop(self) -> None:
        await self.proc.stop()


# ---------- тесты (как service.bat -> 11 -> 1 -> 1) ----------

_BEST_RE = re.compile(r"Best strategy:\s*(.+?)\s*$")


def _prepare_test_script() -> Path:
    """Копия test zapret.ps1 в той же папке utils (чтобы $PSScriptRoot был верным),
    с шим-ом Read-Host (автоответы) и заглушённым финальным ReadKey."""
    original = paths.TEST_SCRIPT.read_text(encoding="utf-8", errors="replace")
    modified = (
        original
        .replace("[void][System.Console]::ReadKey($true)", "$null")
        .replace("[System.Console]::ReadKey($true)", "$null")
    )
    out = paths.ZAPRET_UTILS / ".kzapret_test_run.ps1"
    out.write_text(_TEST_PREFIX + "\n" + modified, encoding="utf-8")
    return out


async def run_tests(on_line: Callable[[str], None],
                    test_type: str = "1", mode: str = "1") -> Optional[str]:
    """Гоняет utils/test zapret.ps1 (standard/all по умолчанию). Возвращает лучший конфиг.

    test_type: 1=standard, 2=dpi; mode: 1=all, 2=selected (в авто не используем).
    Ответы передаём через переменные окружения KZ_TEST_TYPE/KZ_TEST_MODE.
    """
    if not paths.TEST_SCRIPT.exists():
        on_line("[kzapret] Не найден тестовый скрипт zapret.")
        return None

    runner = _prepare_test_script()
    env = os.environ.copy()
    env["KZ_TEST_TYPE"] = test_type
    env["KZ_TEST_MODE"] = mode
    env["NO_UPDATE_CHECK"] = "1"

    await run_capture(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(runner)],
        cwd=str(paths.ZAPRET_DIR),
        on_line=on_line,
        env=env,
    )
    return latest_best_config()


def latest_best_config() -> Optional[str]:
    """Читает 'Best strategy:' из самого свежего файла результатов."""
    if not paths.TEST_RESULTS_DIR.exists():
        return None
    files = sorted(
        paths.TEST_RESULTS_DIR.glob("test_results_*.txt"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in reversed(text.splitlines()):
            m = _BEST_RE.search(line)
            if m and m.group(1) and m.group(1).lower() != "null":
                return m.group(1).strip()
    return None


# Префикс к копии оригинального теста: автоответы на Read-Host (тип теста / режим).
_TEST_PREFIX = r"""
$global:KzAnswers = @()
if ($env:KZ_TEST_TYPE) { $global:KzAnswers += $env:KZ_TEST_TYPE } else { $global:KzAnswers += '1' }
if ($env:KZ_TEST_MODE) { $global:KzAnswers += $env:KZ_TEST_MODE } else { $global:KzAnswers += '1' }
$global:KzIdx = 0
function global:Read-Host {
    param([string]$Prompt, [switch]$AsSecureString)
    if ($global:KzIdx -lt $global:KzAnswers.Count) {
        $a = $global:KzAnswers[$global:KzIdx]
        $global:KzIdx++
        Write-Host ("{0}: {1}" -f $Prompt, $a)
        return $a
    }
    return '1'
}
"""
