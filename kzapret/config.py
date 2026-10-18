"""Конфиг kzapret (kzapret.json): что считать «авто»-режимом и настройки утилит."""
from __future__ import annotations

import json
import os
from typing import Any, Dict

from . import paths

DEFAULTS: Dict[str, Any] = {
    "first_run_done": False,
    "lang": "en",        # язык интерфейса: en | ru (по умолчанию английский)
    "autostart": False,  # автозагрузка kzapret при входе в Windows
    "zapret": {
        "auto_config": None,        # имя bat-конфига, который поднимается в авто-режиме
        "gamefilter": "off",        # off | tcp | udp | all
        "ipset": "off",             # on | off
        "autostart": True,          # поднимать zapret при старте kzapret
        "autotest": False,          # при старте системы (--auto) проверить конфиг, при провале - найти лучший
    },
    "proxy": {
        "port": 1443,
        "secret": None,             # 32 hex; генерируется один раз и хранится тут
        "fake_tls_domain": "",      # пусто = обычный dd-секрет
        "autostart": True,          # поднимать прокси при старте kzapret
    },
}


def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


class Config:
    def __init__(self, data: Dict[str, Any]):
        self.data = data

    # удобный доступ
    @property
    def first_run_done(self) -> bool:
        return bool(self.data.get("first_run_done"))

    @property
    def autostart(self) -> bool:
        return bool(self.data.get("autostart"))

    @property
    def lang(self) -> str:
        return str(self.data.get("lang", "en"))

    @property
    def zapret(self) -> dict:
        return self.data["zapret"]

    @property
    def proxy(self) -> dict:
        return self.data["proxy"]

    def ensure_secret(self) -> str:
        """Секрет прокси создаётся один раз и переживает перезапуски (ссылка стабильна)."""
        sec = self.proxy.get("secret")
        if not sec or len(sec) != 32:
            sec = os.urandom(16).hex()
            self.proxy["secret"] = sec
            self.save()
        return sec

    def save(self) -> None:
        paths.CONFIG_FILE.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def load() -> Config:
    data = dict(DEFAULTS)
    if paths.CONFIG_FILE.exists():
        try:
            loaded = json.loads(paths.CONFIG_FILE.read_text(encoding="utf-8"))
            data = _merge(DEFAULTS, loaded)
        except (json.JSONDecodeError, OSError):
            pass
    return Config(data)
