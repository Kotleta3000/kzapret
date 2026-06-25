"""Управление tg-ws-proxy в headless-режиме (без трея/UI) + построение ссылки."""
from __future__ import annotations

import os
import re
import socket
import subprocess
from typing import Callable, Optional, Tuple

from . import paths
from .process import ManagedProcess

_NO_WINDOW = 0x08000000


def port_free(port: int, host: str = "127.0.0.1") -> bool:
    """True, если порт свободен (без SO_REUSEADDR — как делает сам asyncio на Windows)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def find_free_port(start: int = 1443, host: str = "127.0.0.1") -> Optional[int]:
    for p in range(start, start + 50):
        if port_free(p, host):
            return p
    return None


def free_port(port: int, exclude_pid: Optional[int] = None) -> bool:
    """Если порт держит python/pythonw (зависший старый tg-ws-proxy) — снести его.

    Возвращает True, если порт после этого свободен. Чужие (не-python) процессы не трогаем.
    """
    if port_free(port):
        return True
    owner = port_owner(port)
    if not owner:
        return port_free(port)
    pid, name = owner
    if name.lower() not in ("python.exe", "pythonw.exe"):
        return False  # не наш домен — не убиваем
    if exclude_pid is not None and str(exclude_pid) == str(pid):
        return False
    subprocess.run(["taskkill", "/F", "/PID", str(pid), "/T"],
                   capture_output=True, creationflags=_NO_WINDOW)
    import time
    deadline = time.time() + 4
    while time.time() < deadline:
        if port_free(port):
            return True
        time.sleep(0.2)
    return port_free(port)


def port_owner(port: int) -> Optional[Tuple[str, str]]:
    """Best-effort: (PID, имя процесса), который слушает порт. None если не нашли."""
    try:
        out = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True, text=True, errors="replace",
            creationflags=_NO_WINDOW,
        ).stdout
    except Exception:  # noqa: BLE001
        return None
    pid = None
    for line in out.splitlines():
        u = line.upper()
        if f":{port} " in line and "LISTENING" in u:
            pid = line.split()[-1]
            break
    if not pid:
        return None
    name = ""
    try:
        t = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, errors="replace",
            creationflags=_NO_WINDOW,
        ).stdout
        if t and "," in t:
            name = t.split(",")[0].strip().strip('"')
    except Exception:  # noqa: BLE001
        pass
    return (pid, name)


def installed() -> bool:
    return paths.PROXY_ENTRY.exists()


def version() -> Optional[str]:
    try:
        text = paths.PROXY_VERSION_FILE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
    return m.group(1) if m else None


def proxy_link(secret: str, port: int, host: str = "127.0.0.1",
               fake_tls_domain: str = "") -> str:
    """tg://-ссылка ровно как её формирует сам tg-ws-proxy (dd-секрет, либо ee + fake TLS)."""
    if fake_tls_domain:
        domain_hex = fake_tls_domain.encode("ascii").hex()
        return (f"tg://proxy?server={host}&port={port}"
                f"&secret=ee{secret}{domain_hex}")
    return f"tg://proxy?server={host}&port={port}&secret=dd{secret}"


def proxy_link_https(secret: str, port: int, host: str = "127.0.0.1",
                     fake_tls_domain: str = "") -> str:
    return proxy_link(secret, port, host, fake_tls_domain).replace(
        "tg://proxy?", "https://t.me/proxy?"
    )


class ProxyRuntime:
    def __init__(self):
        self.proc = ManagedProcess("tg-ws-proxy")
        self.secret: Optional[str] = None
        self.port: int = 1443
        self.fake_tls_domain: str = ""

    @property
    def running(self) -> bool:
        return self.proc.running

    def link(self) -> Optional[str]:
        if not self.secret:
            return None
        return proxy_link(self.secret, self.port, "127.0.0.1", self.fake_tls_domain)

    async def start(self, secret: str, port: int, on_line: Callable[[str], None],
                    fake_tls_domain: str = "",
                    on_exit: Optional[Callable[[Optional[int]], None]] = None) -> None:
        await self.stop()
        self.secret = secret
        self.port = port
        self.fake_tls_domain = fake_tls_domain
        cmd = [
            paths.python_for_proxy(),
            str(paths.PROXY_ENTRY),
            "--host", "127.0.0.1",
            "--port", str(port),
            "--secret", secret,
        ]
        if fake_tls_domain:
            cmd += ["--fake-tls-domain", fake_tls_domain]
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        await self.proc.start(
            cmd,
            cwd=str(paths.PROXY_DIR),
            on_line=on_line,
            on_exit=on_exit,
            env=env,
        )

    async def stop(self) -> None:
        await self.proc.stop()
