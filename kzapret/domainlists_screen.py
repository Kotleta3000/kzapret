"""Отдельное окно (Textual Screen) для редактирования списков доменов: /zapret domainlists."""
from __future__ import annotations

import asyncio
from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Input, RichLog, Static

from . import domainlists
from .i18n import t

ST_OK = "bold #5fff87"
ST_WARN = "bold #ffd75f"
ST_ERR = "bold #ff5f5f"


class DomainListsScreen(Screen[bool]):
    """Результат закрытия: True, если списки менялись (приложение перезапустит zapret)."""

    BINDINGS = [("escape", "leave", "Exit")]

    DEFAULT_CSS = """
    DomainListsScreen { background: #000000; }
    #dl-title { height: 1; color: #000000; background: #ffd75f; padding: 0 1; text-style: bold; }
    #dl-view {
        height: 1fr; background: #000000; color: #cfcfcf; border: solid #ffd75f;
        scrollbar-size-vertical: 1; scrollbar-size-horizontal: 0;
        scrollbar-background: #000000; scrollbar-color: #585858;
    }
    #dl-status { height: 1; padding: 0 1; background: #000000; }
    #dl-help { height: 1; color: #00d7ff; background: #000000; padding: 0 1; }
    #dl-cmd { dock: bottom; background: #000000; color: #ffffff; border: solid #875fff; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.lists: list[str] = []
        self.current: Optional[str] = None
        self.changed = False
        self._busy = False

    # ---------- layout ----------
    def compose(self) -> ComposeResult:
        yield Static("", id="dl-title")
        yield RichLog(id="dl-view", wrap=False, highlight=False, markup=False, auto_scroll=False)
        yield Static("", id="dl-status")
        yield Static("", id="dl-help")
        yield Input(placeholder=t("list number or /command"), id="dl-cmd")

    def on_mount(self) -> None:
        self._show_lists()
        self.query_one("#dl-cmd", Input).focus()

    # ---------- helpers ----------
    def _status(self, msg: str, style: str = ST_OK) -> None:
        self.query_one("#dl-status", Static).update(Text(msg, style=style))

    def _header(self, title: str, help_text: str) -> None:
        self.query_one("#dl-title", Static).update(Text(title))
        self.query_one("#dl-help", Static).update(Text(help_text))

    def _show_lists(self) -> None:
        self.current = None
        self.lists = domainlists.available()
        view = self.query_one("#dl-view", RichLog)
        view.clear()
        self._header(
            t("Domain lists - choose a list"),
            t("Enter a list number or name  |  /reset <list>  |  /exit"),
        )
        if not self.lists:
            view.write(Text(t("No lists found in zapret/lists/. Is zapret installed?"), style=ST_ERR))
            return
        width = len(str(len(self.lists)))
        for i, name in enumerate(self.lists, 1):
            try:
                count = len(domainlists.read(name))
            except domainlists.ListError:
                count = 0
            view.write(Text(f"{i:>{width}}. {name}  ({count})"))

    def _show_entries(self, keep_scroll: bool = False, to_end: bool = False) -> None:
        assert self.current
        view = self.query_one("#dl-view", RichLog)
        y = view.scroll_y
        entries = domainlists.read(self.current)
        view.clear()
        width = max(3, len(str(len(entries))))
        for i, entry in enumerate(entries, 1):
            view.write(Text(f"{i:>{width}}  {entry}"))
        self._header(
            t("{name} - {n} entries", name=self.current, n=len(entries)),
            t("/add <domain>   /delete <number>   /reset <list>   /back   /exit"),
        )
        if to_end:
            view.call_after_refresh(view.scroll_end, animate=False)
        elif keep_scroll:
            view.call_after_refresh(view.scroll_to, y=y, animate=False)

    def _resolve(self, arg: str, allow_number: bool) -> Optional[str]:
        a = arg.strip().strip('"')
        if allow_number and a.isdigit():
            i = int(a)
            return self.lists[i - 1] if 1 <= i <= len(self.lists) else None
        low = a.lower()
        for name in self.lists:
            if name.lower() in (low, low + ".txt"):
                return name
        return None

    # ---------- events ----------
    def action_leave(self) -> None:
        if not self._busy:
            self.dismiss(self.changed)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "dl-cmd":
            return
        event.stop()
        raw = event.value.strip()
        event.input.value = ""
        if raw:
            await self._handle(raw)

    async def _handle(self, raw: str) -> None:
        if self._busy:
            return
        parts = raw.split(None, 1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""
        try:
            if cmd in ("/exit", "/quit", "/q"):
                self.dismiss(self.changed)
            elif cmd == "/back":
                self._show_lists()
                self._status("")
            elif cmd == "/add":
                self._cmd_add(arg)
            elif cmd == "/delete":
                self._cmd_delete(arg)
            elif cmd == "/reset":
                await self._cmd_reset(arg)
            elif not cmd.startswith("/") and self.current is None:
                name = self._resolve(raw, allow_number=True)
                if not name:
                    raise domainlists.ListError(
                        t("Enter a list number (1-{n}) or name.", n=max(len(self.lists), 1)))
                self.current = name
                self._show_entries()
                self._status("")
            else:
                raise domainlists.ListError(t("Unknown command: {cmd}", cmd=cmd))
        except domainlists.ListError as exc:
            self._status(str(exc), ST_ERR)

    def _need_list(self) -> str:
        if self.current is None:
            raise domainlists.ListError(t("Select a list first."))
        return self.current

    def _cmd_add(self, arg: str) -> None:
        name = self._need_list()
        if not arg:
            raise domainlists.ListError(t("Usage: /add <domain>"))
        entry = domainlists.add(name, arg)
        self.changed = True
        self._show_entries(to_end=True)
        self._status(t("Added: {entry}", entry=entry))

    def _cmd_delete(self, arg: str) -> None:
        name = self._need_list()
        if not arg.isdigit():
            raise domainlists.ListError(t("Usage: /delete <number>"))
        number = int(arg)
        removed = domainlists.delete(name, number)
        self.changed = True
        self._show_entries(keep_scroll=True)
        self._status(t("Deleted #{n}: {entry}", n=number, entry=removed))

    async def _cmd_reset(self, arg: str) -> None:
        if not arg and self.current is None:
            raise domainlists.ListError(t("Usage: /reset <list>"))
        if arg:
            target = self._resolve(arg, allow_number=self.current is None)
            if not target:
                raise domainlists.ListError(t("Unknown list: {name}", name=arg))
        else:
            target = self.current
        assert target
        self._busy = True
        self._status(t("Resetting {name} from Flowseal GitHub...", name=target), ST_WARN)
        try:
            await asyncio.to_thread(domainlists.reset, target)
        finally:
            self._busy = False
        self.changed = True
        if self.current is None:
            self._show_lists()
        elif self.current == target:
            self._show_entries()
        self._status(t("{name} reset to the original list.", name=target))
