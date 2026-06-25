"""Проверка/применение обновлений с GitHub Flowseal"""
from __future__ import annotations

import json
import subprocess
import urllib.request
from dataclasses import dataclass
from typing import Optional

from . import paths, zapret_manager, proxy_manager

_NO_WINDOW = 0x08000000


@dataclass
class UpdateInfo:
    name: str
    current: Optional[str]
    latest: Optional[str]
    has_update: bool
    error: Optional[str] = None


def _http_get(url: str, timeout: int = 10) -> Optional[str]:
    try:
        req = urllib.request.Request(
            url, headers={"Cache-Control": "no-cache", "User-Agent": "kzapret"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return None


def check_zapret() -> UpdateInfo:
    cur = zapret_manager.version()
    raw = _http_get(paths.ZAPRET_VERSION_URL)
    latest = raw.strip() if raw else None
    if cur is None or latest is None:
        return UpdateInfo("zapret", cur, latest, False,
                          error="не удалось проверить версию")
    return UpdateInfo("zapret", cur, latest, cur != latest)


def check_proxy() -> UpdateInfo:
    cur = proxy_manager.version()
    latest = None
    raw = _http_get(paths.PROXY_LATEST_API)
    if raw:
        try:
            tag = json.loads(raw).get("tag_name") or ""
            latest = tag.lstrip("vV").strip() or None
        except json.JSONDecodeError:
            latest = None
    if cur is None or latest is None:
        return UpdateInfo("tg-ws-proxy", cur, latest, False,
                          error="не удалось проверить версию")
    return UpdateInfo("tg-ws-proxy", cur, latest, cur != latest)


def _git(args, cwd) -> tuple[int, str]:
    try:
        p = subprocess.run(
            ["git", *args], cwd=str(cwd),
            capture_output=True, text=True, errors="replace", creationflags=_NO_WINDOW,
        )
        return p.returncode, (p.stdout + p.stderr).strip()
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)


def clone(repo_url: str, dest, on_line=None) -> bool:
    if on_line:
        on_line(f"git clone {repo_url} -> {dest.name} ...")
    rc, out = _git(["clone", "--depth", "1", repo_url, str(dest)], cwd=dest.parent)
    if on_line and out:
        on_line(out)
    return rc == 0


def update_repo(repo_dir, on_line=None) -> bool:
    if on_line:
        on_line(f"git pull в {repo_dir.name} ...")
    # на случай локальных правок (мы пишем .kzapret_* и ipset backup) — не мешаем pull
    rc, out = _git(["pull", "--ff-only"], cwd=repo_dir)
    if rc != 0:
        # запасной путь: жёстко подтянуть main
        _git(["fetch", "--all"], cwd=repo_dir)
        rc, out = _git(["reset", "--hard", "origin/main"], cwd=repo_dir)
    if on_line and out:
        on_line(out)
    return rc == 0


def update_zapret(on_line=None) -> bool:
    return update_repo(paths.ZAPRET_DIR, on_line)


def update_proxy(on_line=None) -> bool:
    return update_repo(paths.PROXY_DIR, on_line)
