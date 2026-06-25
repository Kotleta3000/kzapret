"""Автозагрузка kzapret при входе в Windows.
"""
from __future__ import annotations

import subprocess

from . import paths

TASK_NAME = "kzapret"
_NO_WINDOW = 0x08000000
_LAUNCHER = paths.ROOT / "kzapret.bat"


def _schtasks(args) -> tuple[int, str]:
    try:
        p = subprocess.run(
            ["schtasks", *args],
            capture_output=True, text=True, errors="replace", creationflags=_NO_WINDOW,
        )
        return p.returncode, (p.stdout + p.stderr).strip()
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)


def is_enabled() -> bool:
    rc, _ = _schtasks(["/Query", "/TN", TASK_NAME])
    return rc == 0


def enable() -> tuple[bool, str]:
    # /TR должен содержать команду запуска лаунчера в авто-режиме
    tr = f'cmd /c ""{_LAUNCHER}" --auto"'
    rc, out = _schtasks([
        "/Create", "/TN", TASK_NAME, "/TR", tr,
        "/SC", "ONLOGON", "/RL", "HIGHEST", "/F",
    ])
    return rc == 0, out


def disable() -> tuple[bool, str]:
    rc, out = _schtasks(["/Delete", "/TN", TASK_NAME, "/F"])
    return rc == 0, out
