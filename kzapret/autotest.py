"""Автотест при старте системы: проверка, что через ТЕКУЩИЙ конфиг доступны ВСЕ цели.

Цели берутся из zapret/utils/targets.txt (тот же список, что у `test zapret.ps1`).
Строка вида  Name = "https://host"  - HTTPS-проверка,  Name = "PING:1.1.1.1"  - ping.
Цель считается доступной, если сервер ответил (любой HTTP-код) или пришёл ответ на ping.
"""
from __future__ import annotations

import re
import socket
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import List, NamedTuple, Optional, Tuple

from . import paths

_NO_WINDOW = 0x08000000
_LINE_RE = re.compile(r'^\s*([A-Za-z0-9_\-. ]+?)\s*=\s*"([^"]+)"')

HTTP_TIMEOUT = 6.0
HTTP_ATTEMPTS = 2


class Target(NamedTuple):
    name: str
    value: str

    @property
    def is_ping(self) -> bool:
        return self.value.upper().startswith("PING:")


# запасной набор, если utils/targets.txt не найден
_FALLBACK = [
    Target("DiscordMain", "https://discord.com"),
    Target("DiscordGateway", "https://gateway.discord.gg"),
    Target("YouTubeWeb", "https://www.youtube.com"),
    Target("GoogleVideo", "https://redirector.googlevideo.com"),
    Target("CloudflareDNS", "PING:1.1.1.1"),
    Target("GoogleDNS", "PING:8.8.8.8"),
]


def load_targets() -> List[Target]:
    targets_file = paths.ZAPRET_UTILS / "targets.txt"
    out: List[Target] = []
    try:
        for line in targets_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lstrip().startswith("#"):
                continue
            m = _LINE_RE.match(line)
            if m:
                out.append(Target(m.group(1).strip(), m.group(2).strip()))
    except OSError:
        pass
    return out or list(_FALLBACK)


def _check_http(url: str) -> bool:
    ctx = ssl.create_default_context()
    # без системного прокси: проверяем именно путь через zapret
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ctx)
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 kzapret"})
    for _ in range(HTTP_ATTEMPTS):
        try:
            with opener.open(req, timeout=HTTP_TIMEOUT):
                return True
        except urllib.error.HTTPError:
            return True  # сервер ответил -> TLS и маршрут работают
        except Exception:  # noqa: BLE001
            continue
    return False


def _check_ping(host: str) -> bool:
    try:
        p = subprocess.run(
            ["ping", "-n", "2", "-w", "2000", host],
            capture_output=True, text=True, errors="replace",
            creationflags=_NO_WINDOW, timeout=20,
        )
    except Exception:  # noqa: BLE001
        return False
    return "TTL=" in p.stdout.upper()


def _check(target: Target) -> bool:
    if target.is_ping:
        return _check_ping(target.value[5:].strip())
    return _check_http(target.value)


def check_targets(targets: Optional[List[Target]] = None) -> Tuple[bool, List[Tuple[str, bool]]]:
    """Возвращает (все_ок, [(имя, ок), ...]). Блокирующая - вызывать из потока."""
    targets = targets or load_targets()
    with ThreadPoolExecutor(max_workers=8) as pool:
        flags = list(pool.map(_check, targets))
    results = [(tg.name, ok) for tg, ok in zip(targets, flags)]
    return all(flags), results


def wait_for_network(timeout: float = 90.0) -> bool:
    """Ждём базовую сеть (после входа в Windows она поднимается не сразу), иначе тест
    ложно решит, что конфиг не работает."""
    probes = [("1.1.1.1", 443), ("8.8.8.8", 443), ("ya.ru", 443)]
    deadline = time.time() + timeout
    while True:
        for host, port in probes:
            try:
                with socket.create_connection((host, port), timeout=3):
                    return True
            except OSError:
                pass
        if time.time() >= deadline:
            return False
        time.sleep(3)
