"""Редактирование списков доменов zapret/lists/*.txt (без привязки к UI)."""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List

from . import paths
from .i18n import t

_NO_WINDOW = 0x08000000

# ipset-all.txt управляется командой /zapret ipset (on/off, заглушка/полный список),
# поэтому руками его не правим и не сбрасываем.
_EXCLUDED = {"ipset-all.txt"}


class ListError(Exception):
    """Ошибка операции со списком; текст уже переведён и готов к показу."""


def available() -> List[str]:
    """Имена всех *.txt в zapret/lists/ (парсится с диска, ничего не захардкожено)."""
    if not paths.ZAPRET_LISTS.is_dir():
        return []
    return sorted(
        p.name for p in paths.ZAPRET_LISTS.glob("*.txt")
        if p.name.lower() not in _EXCLUDED
    )


def _path(name: str) -> Path:
    for n in available():
        if n.lower() == name.lower():
            return paths.ZAPRET_LISTS / n
    raise ListError(t("Unknown list: {name}", name=name))


def read(name: str) -> List[str]:
    """Непустые строки списка; номер строки в UI = индекс + 1."""
    p = _path(name)
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ListError(str(exc)) from exc
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _write(name: str, lines: List[str]) -> None:
    p = _path(name)
    try:
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))
    except OSError as exc:
        raise ListError(str(exc)) from exc


def normalize(value: str) -> str:
    """Приводит ввод к виду записи в списке: example.com (без схемы/пути, lower-case)."""
    v = value.strip().lower()
    if "://" in v:
        v = v.split("://", 1)[1]
    for sep in ("/", "?", "#"):
        v = v.split(sep, 1)[0]
    v = v.rstrip(".")
    if not v:
        raise ListError(t("Empty value."))
    if any(ch.isspace() for ch in v):
        raise ListError(t("Value must not contain spaces."))
    return v


def add(name: str, value: str) -> str:
    entry = normalize(value)
    lines = read(name)
    if entry in (ln.lower() for ln in lines):
        raise ListError(t("Already in the list: {entry}", entry=entry))
    lines.append(entry)
    _write(name, lines)
    return entry


def delete(name: str, number: int) -> str:
    lines = read(name)
    if not 1 <= number <= len(lines):
        raise ListError(t("Number must be 1..{n}", n=len(lines)))
    removed = lines.pop(number - 1)
    _write(name, lines)
    return removed


def _rm_readonly(func, path, _exc) -> None:
    # .git содержит read-only файлы - на Windows их надо разблокировать перед удалением
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        pass


def _rmtree(path: str) -> None:
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_rm_readonly)
    else:
        shutil.rmtree(path, onerror=_rm_readonly)


def reset(name: str) -> None:
    """Сброс списка до «заводского»: клон оригинального репозитория Flowseal во временную
    папку и копирование оттуда файла. Блокирующая функция - вызывать из потока."""
    target = _path(name)
    tmp = tempfile.mkdtemp(prefix="kzapret_")
    try:
        try:
            p = subprocess.run(
                ["git", "clone", "--depth", "1", "--quiet", paths.ZAPRET_REPO, tmp],
                capture_output=True, text=True, errors="replace",
                creationflags=_NO_WINDOW, timeout=180,
            )
        except FileNotFoundError as exc:
            raise ListError(t("git is not installed or not in PATH.")) from exc
        except subprocess.TimeoutExpired as exc:
            raise ListError(t("git clone failed: {err}", err="timeout")) from exc
        if p.returncode != 0:
            err = (p.stderr or p.stdout or "").strip().splitlines()
            raise ListError(t("git clone failed: {err}", err=err[-1] if err else p.returncode))
        src = Path(tmp) / "lists" / target.name
        if not src.is_file():
            raise ListError(t("{name} does not exist in the original repository.", name=target.name))
        shutil.copyfile(src, target)
    finally:
        _rmtree(tmp)
