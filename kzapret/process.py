"""Управляемый дочерний процесс с захватом вывода построчно в callback.

Используется и для winws.exe (zapret), и для headless tg-ws-proxy.
"""
from __future__ import annotations

import asyncio
import subprocess
from typing import Awaitable, Callable, List, Optional, Sequence

LineCb = Callable[[str], None]
ExitCb = Callable[[Optional[int]], None]


class ManagedProcess:
    def __init__(self, name: str):
        self.name = name
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._reader: Optional[asyncio.Task] = None
        self._kill_names: List[str] = []

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    @property
    def pid(self) -> Optional[int]:
        return self._proc.pid if self._proc else None

    async def start(
        self,
        cmd: Sequence[str],
        cwd: Optional[str],
        on_line: LineCb,
        on_exit: Optional[ExitCb] = None,
        env: Optional[dict] = None,
        kill_names: Optional[Sequence[str]] = None,
    ) -> None:
        if self.running:
            return
        self._kill_names = list(kill_names or [])

        # CREATE_NO_WINDOW, чтобы консольные окна дочерних процессов не всплывали
        flags = 0x08000000  # CREATE_NO_WINDOW

        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=flags,
        )
        self._reader = asyncio.create_task(self._pump(on_line, on_exit))

    async def _pump(self, on_line: LineCb, on_exit: Optional[ExitCb]) -> None:
        assert self._proc and self._proc.stdout
        try:
            while True:
                raw = await self._proc.stdout.readline()
                if not raw:
                    break
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if line:
                    on_line(line)
        except asyncio.CancelledError:
            pass
        finally:
            rc = await self._proc.wait()
            if on_exit:
                on_exit(rc)

    async def stop(self) -> None:
        # Сначала убиваем по имени (winws.exe переживает kill родительского cmd)
        for nm in self._kill_names:
            await _taskkill(nm)
        if self._proc and self._proc.returncode is None:
            try:
                self._proc.terminate()
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                try:
                    self._proc.kill()
                except ProcessLookupError:
                    pass
        if self._reader:
            self._reader.cancel()
        self._proc = None
        self._reader = None


async def _taskkill(image_name: str) -> None:
    try:
        proc = await asyncio.create_subprocess_exec(
            "taskkill", "/F", "/IM", image_name, "/T",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=0x08000000,
        )
        await proc.wait()
    except Exception:
        pass


async def run_capture(
    cmd: Sequence[str],
    cwd: Optional[str],
    on_line: LineCb,
    env: Optional[dict] = None,
) -> int:
    """Запустить процесс до завершения, стримя вывод построчно. Возвращает код выхода."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=0x08000000,
    )
    assert proc.stdout
    while True:
        raw = await proc.stdout.readline()
        if not raw:
            break
        line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
        on_line(line)
    return await proc.wait()
