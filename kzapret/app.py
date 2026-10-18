"""Textual TUI: zapret log (left), tg-ws-proxy log (right), command line (bottom)."""
from __future__ import annotations

import asyncio
import shlex
import subprocess
import time
import webbrowser
from typing import List, Optional

from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.suggester import Suggester
from textual.widgets import Input, RichLog, Static

from . import autostart, autotest, commands, config, proxy_manager, updates, zapret_manager
from .domainlists_screen import DomainListsScreen
from .i18n import set_lang, t

_NO_WINDOW = 0x08000000

# message styles (bright on black)
ST_INFO = "bold #00d7ff"
ST_OK = "bold #5fff87"
ST_WARN = "bold #ffd75f"
ST_ERR = "bold #ff5f5f"
ST_ECHO = "bold #ffffff"


def _copy_clipboard(text: str) -> bool:
    try:
        subprocess.run("clip", input=text, text=True, creationflags=_NO_WINDOW, check=True)
        return True
    except Exception:  # noqa: BLE001
        return False


class CommandSuggester(Suggester):
    def __init__(self, app: "KzapretApp"):
        super().__init__(use_cache=False, case_sensitive=False)
        self._app = app

    async def get_suggestion(self, value: str) -> Optional[str]:
        return commands.best_suggestion(value, self._app.configs)


class CommandInput(Input):
    """Input with Tab-completion (cycles through matching commands)."""

    def __init__(self, app: "KzapretApp", **kw):
        super().__init__(**kw)
        self._app_ref = app
        self._matches: List[str] = []
        self._mi = -1

    def on_key(self, event: events.Key) -> None:
        if event.key == "tab":
            event.prevent_default()
            event.stop()
            self._tab_complete()
        else:
            # any other keypress ends the current completion cycle
            self._matches = []
            self._mi = -1

    def _tab_complete(self) -> None:
        if not self._matches:
            base = commands.normalize(self.value).lower()
            if not base:
                return
            self._matches = [
                c for c in commands.completions(self._app_ref.configs)
                if c.lower().startswith(base)
            ]
            self._mi = -1
        if not self._matches:
            return
        self._mi = (self._mi + 1) % len(self._matches)
        self.value = self._matches[self._mi]
        self.cursor_position = len(self.value)


class KzapretApp(App):
    CSS = """
    Screen { background: #000000; }
    #panes { height: 1fr; }
    RichLog {
        background: #000000; color: #cfcfcf;
        scrollbar-size-vertical: 1; scrollbar-size-horizontal: 0;
        scrollbar-background: #000000; scrollbar-color: #585858;
    }
    #zapret { width: 1fr; height: 100%; border: solid #00ff5f; border-title-color: #00ff5f; margin: 0 1 0 0; }
    #proxy  { width: 1fr; height: 100%; border: solid #00d7ff; border-title-color: #00d7ff; }
    #system { height: 11; border: solid #ffd75f; border-title-color: #ffd75f; background: #000000; }
    #hints  { height: 1; color: #00d7ff; background: #000000; padding: 0 1; }
    #cmd    { dock: bottom; background: #000000; color: #ffffff; border: solid #875fff; }
    """

    BINDINGS = [
        ("ctrl+c", "quit_app", "Quit"),
        ("ctrl+l", "clear_logs", "Clear"),
    ]

    def __init__(self, cfg: config.Config, autostart_on_mount: bool = True,
                 boot_mode: bool = False):
        super().__init__()
        self.cfg = cfg
        self._boot_mode = boot_mode  # запущены задачей автозагрузки (--auto)
        set_lang(cfg.lang)
        self._autostart = autostart_on_mount
        self.zapret = zapret_manager.ZapretRuntime()
        self.proxy = proxy_manager.ProxyRuntime()
        self.configs: List[str] = zapret_manager.list_configs()

    # ---------- layout ----------
    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(id="panes"):
                yield RichLog(id="zapret", wrap=True, highlight=True, max_lines=2000)
                yield RichLog(id="proxy", wrap=True, highlight=True, max_lines=2000)
            yield RichLog(id="system", wrap=True, highlight=True, max_lines=1000)
            yield Static("/help", id="hints")
            yield CommandInput(self, placeholder="command (e.g. /zapret status) - Tab to complete",
                               id="cmd", suggester=CommandSuggester(self))

    def on_mount(self) -> None:
        self.query_one("#zapret", RichLog).border_title = "zapret"
        self.query_one("#proxy", RichLog).border_title = "tg-ws-proxy"
        self.query_one("#system", RichLog).border_title = "kzapret"
        self.query_one("#cmd", Input).focus()
        self.sys(t("kzapret ready. Type /help for commands."))
        if self._autostart:
            self._spawn(self._autostart_both())

    # ---------- output ----------
    def _log(self, widget_id: str, text: str, style: Optional[str] = None) -> None:
        rl = self.screen_stack[0].query_one(f"#{widget_id}", RichLog)
        rl.write(Text(text, style=style) if style else text)

    def zlog(self, line: str) -> None:
        self._log("zapret", line)

    def plog(self, line: str) -> None:
        self._log("proxy", line)

    def sys(self, line: str, style: str = ST_INFO) -> None:
        self._log("system", line, style)

    def sys_ok(self, line: str) -> None:
        self._log("system", line, ST_OK)

    def sys_err(self, line: str) -> None:
        self._log("system", line, ST_ERR)

    # ---------- task spawning with guard ----------
    def _spawn(self, coro) -> None:
        async def _wrap():
            try:
                await coro
            except Exception as exc:  # noqa: BLE001
                self.sys_err(t("Error: {exc}", exc=repr(exc)))
        asyncio.create_task(_wrap())

    async def _cleanup_leftovers(self) -> None:
        """Free the slate before autostart: kill orphan winws and stale proxy on our port."""
        self.sys(t("Cleanup of leftover processes..."), style=ST_WARN)
        await asyncio.to_thread(zapret_manager.kill_winws)
        port = int(self.cfg.proxy.get("port", 1443))
        await asyncio.to_thread(proxy_manager.free_port, port, None)

    async def _autostart_both(self) -> None:
        await self._cleanup_leftovers()
        autotest_on = (self._boot_mode and self.cfg.autostart
                       and bool(self.cfg.zapret.get("autotest", False)))
        if self.cfg.zapret.get("autostart", True):
            if autotest_on:
                # тест может идти минуты - не задерживаем запуск прокси
                self._spawn(self._autotest_boot())
            else:
                await self._zapret_start(None)
        if self.cfg.proxy.get("autostart", True):
            await self._proxy_start()

    # ---------- автотест при старте системы ----------
    async def _wait_winws(self, timeout: float = 15.0) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            if await asyncio.to_thread(zapret_manager.winws_running):
                break
            await asyncio.sleep(0.5)
        await asyncio.sleep(3.0)  # дать winws начать перехват трафика

    async def _autotest_boot(self) -> None:
        name = self.cfg.zapret.get("auto_config")
        self.sys(t("Autotest: waiting for network..."), style=ST_WARN)
        if not await asyncio.to_thread(autotest.wait_for_network, 90.0):
            self.sys_err(t("Autotest: no network, starting the current config without testing."))
            await self._zapret_start(None)
            return

        if name and name in self.configs:
            self.sys(t("Autotest: checking {name}...", name=name))
            await self._zapret_start(name)
            await self._wait_winws()
            ok, results = await asyncio.to_thread(autotest.check_targets)
            if ok:
                self.sys_ok(t("Autotest: all {n} targets reachable - keeping {name}.",
                              n=len(results), name=name))
                return
            bad = [n for n, good in results if not good]
            self.sys(t("Autotest: {bad} of {n} targets failed ({names}). Testing all configs...",
                       bad=len(bad), n=len(results), names=", ".join(bad)), style=ST_WARN)
            await self.zapret.stop()
        else:
            self.sys(t("Autotest: no auto config yet, testing all configs..."), style=ST_WARN)

        started = time.time()
        best = await zapret_manager.run_tests(self.zlog, since=started)
        if best and best not in self.configs and best + ".bat" in self.configs:
            best += ".bat"
        if best and best in self.configs:
            self.cfg.zapret["auto_config"] = best
            self.cfg.save()
            self.sys_ok(t("Autotest: switched to {name}.", name=best))
            await self._zapret_start(best)
        elif name and name in self.configs:
            self.sys_err(t("Autotest: no best config found, keeping {name}.", name=name))
            await self._zapret_start(name)
        else:
            self.sys_err(t("Autotest: no best config found and no auto config set."))

    # ---------- input events ----------
    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "cmd":
            return
        hints_widgets = self.query("#hints")
        if not hints_widgets:
            return  # not mounted yet / tearing down
        hs = commands.hints(event.value, self.configs)
        hints_widgets.first(Static).update("  ".join(hs) if hs else "")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "cmd":
            return
        raw = event.value.strip()
        event.input.value = ""
        self.query_one("#hints", Static).update("")
        if not raw:
            return
        self.sys(f"> {raw}", style=ST_ECHO)
        await self.dispatch(raw)

    # ---------- command dispatch ----------
    async def dispatch(self, raw: str) -> None:
        norm = commands.normalize(raw)
        try:
            parts = shlex.split(norm)
        except ValueError:
            parts = norm.split()
        if not parts:
            return
        head = parts[0].lower()
        args = parts[1:]

        if head == "/help":
            self._cmd_help()
        elif head == "/clear":
            self.action_clear_logs()
        elif head == "/quit":
            await self._cmd_quit()
        elif head == "/zapret":
            await self._cmd_zapret(args)
        elif head == "/tg-ws-proxy":
            await self._cmd_proxy(args)
        elif head == "/kzapret":
            await self._cmd_kzapret(args)
        else:
            self.sys_err(t("Unknown command: {head}. Type /help.", head=head))

    # ---------- /help ----------
    def _cmd_help(self) -> None:
        s = self.query_one("#system", RichLog)
        s.write(Text(t("kzapret commands:"), style="bold underline #00d7ff"))
        lines = [(left, t(desc)) for left, desc in commands.help_lines()]
        width = max(len(left) for left, _ in lines)
        for left, desc in lines:
            line = Text()
            line.append(left.ljust(width + 2), style=ST_OK)
            line.append(desc, style="#cfcfcf")
            s.write(line)

    # ---------- zapret ----------
    async def _zapret_start(self, cfg_name: Optional[str]) -> None:
        name = cfg_name or self.cfg.zapret.get("auto_config")
        if not name:
            self.sys_err(t("No zapret config set. Use /zapret list and /zapret config <name>."))
            return
        if name not in self.configs:
            self.sys_err(t("Config not found: {name}. Use /zapret list.", name=name))
            return
        self.sys(t("Start zapret: {name}", name=name))
        await self.zapret.start(name, self.zlog, on_exit=self._zapret_exit)

    def _zapret_exit(self, rc: Optional[int]) -> None:
        self.sys(t("zapret stopped (code {rc}).", rc=rc), style=ST_WARN)

    async def _cmd_zapret(self, args: List[str]) -> None:
        if not args:
            self.sys_err(t("Specify: start|stop|restart|status|list|config|gamefilter|ipset|domainlists|autotest|test|update"))
            return
        sub = args[0].lower()
        rest = args[1:]
        if sub == "start":
            await self._zapret_start(rest[0] if rest else None)
        elif sub == "stop":
            await self.zapret.stop()
            self.sys(t("zapret stopped."))
        elif sub == "restart":
            await self.zapret.stop()
            await self._zapret_start(None)
        elif sub == "status":
            state = t("running") if self.zapret.running else t("stopped")
            self.sys(t("zapret: {state} | config: {cfg} | gamefilter: {gf} | ipset: {ip} | pid: {pid}",
                       state=state,
                       cfg=self.zapret.current_config or self.cfg.zapret.get("auto_config"),
                       gf=zapret_manager.get_gamefilter(),
                       ip=zapret_manager.get_ipset_status(),
                       pid=self.zapret.proc.pid))
        elif sub == "list":
            self.configs = zapret_manager.list_configs()
            auto = self.cfg.zapret.get("auto_config")
            for c in self.configs:
                mark = "  <- auto" if c == auto else ""
                self.sys(f"  {c}{mark}", style="#cfcfcf")
        elif sub == "config":
            if not rest:
                self.sys_err(t("No zapret config set. Use /zapret list and /zapret config <name>."))
                return
            name = " ".join(rest)
            if name not in self.configs:
                self.sys_err(t("Config not found: {name}. Use /zapret list.", name=name))
                return
            self.cfg.zapret["auto_config"] = name
            self.cfg.save()
            self.sys(t("Auto config: {name}", name=name))
            if self.zapret.running:
                await self.zapret.stop()
                await self._zapret_start(name)
        elif sub == "gamefilter":
            if not rest or rest[0].lower() not in ("off", "tcp", "udp", "all"):
                self.sys_err(t("Usage: /zapret gamefilter <off|tcp|udp|all>"))
                return
            mode = rest[0].lower()
            zapret_manager.set_gamefilter(mode)
            self.cfg.zapret["gamefilter"] = mode
            self.cfg.save()
            self.sys(t("Game filter: {mode} (restart zapret to apply)", mode=mode))
            if self.zapret.running:
                await self.zapret.stop()
                await self._zapret_start(None)
        elif sub == "ipset":
            if not rest or rest[0].lower() not in ("on", "off"):
                self.sys_err(t("Usage: /zapret ipset <on|off>"))
                return
            self._spawn(self._apply_ipset(rest[0].lower() == "on"))
        elif sub == "domainlists":
            self.push_screen(DomainListsScreen(), self._domainlists_closed)
        elif sub == "autotest":
            self._cmd_autotest(rest)
        elif sub == "test":
            self.sys(t("Running zapret tests (a few minutes)..."))
            self._spawn(self._run_tests())
        elif sub == "update":
            self.sys(t("Updating zapret..."))
            self._spawn(self._update_zapret())
        else:
            self.sys_err(t("Unknown zapret subcommand: {sub}", sub=sub))

    def _domainlists_closed(self, changed: Optional[bool]) -> None:
        self.query_one("#cmd", Input).focus()
        if not changed:
            return
        self.sys(t("Domain lists changed."))
        if self.zapret.running:
            self.sys(t("Restarting zapret to apply the changes..."))
            self._spawn(self._restart_current())
        else:
            self.sys(t("Changes will apply on next zapret start."))

    async def _restart_current(self) -> None:
        name = self.zapret.current_config
        await self.zapret.stop()
        await self._zapret_start(name)

    def _cmd_autotest(self, rest: List[str]) -> None:
        mode = rest[0].lower() if rest else "status"
        if mode == "on":
            if not self.cfg.autostart:
                self.sys_err(t("Autotest requires autostart. Enable it first: /kzapret autostart on"))
                return
            self.cfg.zapret["autotest"] = True
            self.cfg.save()
            self.sys_ok(t("Autotest enabled (runs at system start)."))
        elif mode == "off":
            self.cfg.zapret["autotest"] = False
            self.cfg.save()
            self.sys_ok(t("Autotest disabled."))
        elif mode == "status":
            on = bool(self.cfg.zapret.get("autotest", False))
            self.sys(t("Autotest: {state}", state=t("enabled") if on else t("disabled")))
        else:
            self.sys_err(t("Usage: /zapret autotest <on|off>"))

    async def _apply_ipset(self, on: bool) -> None:
        self.sys(t("Changing ipset..."))
        status = await asyncio.to_thread(zapret_manager.set_ipset, on, self.sys)
        self.cfg.zapret["ipset"] = "on" if on else "off"
        self.cfg.save()
        self.sys(t("ipset: {status} (restart zapret to apply)", status=status))
        if self.zapret.running:
            await self.zapret.stop()
            await self._zapret_start(None)

    async def _run_tests(self) -> None:
        was_running = self.zapret.running
        if was_running:
            await self.zapret.stop()
            self.sys(t("zapret paused during tests."), style=ST_WARN)
        best = await zapret_manager.run_tests(self.zlog)
        if best:
            self.sys_ok(t("Best config by tests: {best}", best=best))
            self.sys(t('Apply: /zapret config "{best}"', best=best))
        else:
            self.sys_err(t("Could not determine best config (see the zapret log)."))
        if was_running:
            await self._zapret_start(None)

    async def _update_zapret(self) -> None:
        ok = await asyncio.to_thread(updates.update_zapret, self.sys)
        self.configs = zapret_manager.list_configs()
        self.sys_ok(t("zapret updated.")) if ok else self.sys_err(t("zapret update failed."))

    # ---------- tg-ws-proxy ----------
    async def _proxy_start(self) -> None:
        secret = self.cfg.ensure_secret()
        port = int(self.cfg.proxy.get("port", 1443))
        ftls = self.cfg.proxy.get("fake_tls_domain", "") or ""
        if not self.proxy.running and not proxy_manager.port_free(port):
            owner = await asyncio.to_thread(proxy_manager.port_owner, port)
            if owner and owner[1].lower() in ("python.exe", "pythonw.exe"):
                self.sys(t("Freeing port {port}: stopping stale process PID {pid}...",
                           port=port, pid=owner[0]), style=ST_WARN)
                freed = await asyncio.to_thread(proxy_manager.free_port, port, None)
                if not freed:
                    self.sys_err(t("Port {port} is busy{who}. Another tg-ws-proxy may be running.",
                                   port=port, who=f" (PID {owner[0]} {owner[1]})"))
                    return
            else:
                who = f" (PID {owner[0]} {owner[1]})" if owner else ""
                self.sys_err(t("Port {port} is busy{who}. Another tg-ws-proxy may be running.",
                               port=port, who=who))
                self.sys(t("Close it and /tg-ws-proxy start, or change port: /tg-ws-proxy port <n>"))
                return
        self.sys(t("Start tg-ws-proxy on 127.0.0.1:{port} (headless)", port=port))
        await self.proxy.start(secret, port, self.plog, fake_tls_domain=ftls,
                               on_exit=self._proxy_exit)

    def _proxy_exit(self, rc: Optional[int]) -> None:
        self.sys(t("tg-ws-proxy stopped (code {rc}).", rc=rc), style=ST_WARN)

    async def _cmd_proxy(self, args: List[str]) -> None:
        if not args:
            self.sys_err(t("Specify: start|stop|restart|status|link|open|port|secret|update"))
            return
        sub = args[0].lower()
        rest = args[1:]
        if sub == "start":
            await self._proxy_start()
        elif sub == "stop":
            await self.proxy.stop()
            self.sys(t("tg-ws-proxy stopped."))
        elif sub == "restart":
            await self.proxy.stop()
            await self._proxy_start()
        elif sub == "status":
            state = t("running") if self.proxy.running else t("stopped")
            self.sys(t("tg-ws-proxy: {state} | port: {port} | pid: {pid}",
                       state=state, port=self.cfg.proxy.get("port", 1443),
                       pid=self.proxy.proc.pid))
            self.sys(t("link: {link}", link=self._current_link()), style="#cfcfcf")
        elif sub == "link":
            self._show_link(copy=True)
        elif sub == "open":
            link = self._current_link()
            self.sys(t("Opening: {link}", link=link))
            try:
                webbrowser.open(link)
            except Exception as exc:  # noqa: BLE001
                self.sys_err(t("Could not open: {exc}", exc=exc))
        elif sub == "port":
            if not rest or not rest[0].isdigit():
                self.sys_err(t("Usage: /tg-ws-proxy port <number>"))
                return
            self.cfg.proxy["port"] = int(rest[0])
            self.cfg.save()
            self.sys(t("Proxy port: {port}", port=rest[0]))
            if self.proxy.running:
                await self.proxy.stop()
                await self._proxy_start()
        elif sub == "secret":
            if not rest:
                self.sys_err(t("Usage: /tg-ws-proxy secret <32hex|new>"))
                return
            val = rest[0]
            if val.lower() == "new":
                import os
                self.cfg.proxy["secret"] = os.urandom(16).hex()
            else:
                if len(val) != 32 or any(c not in "0123456789abcdefABCDEF" for c in val):
                    self.sys_err(t("Secret must be exactly 32 hex chars."))
                    return
                self.cfg.proxy["secret"] = val.lower()
            self.cfg.save()
            self.sys(t("Secret updated."))
            self._show_link(copy=False)
            if self.proxy.running:
                await self.proxy.stop()
                await self._proxy_start()
        elif sub == "update":
            self.sys(t("Updating tg-ws-proxy..."))
            self._spawn(self._update_proxy())
        else:
            self.sys_err(t("Unknown tg-ws-proxy subcommand: {sub}", sub=sub))

    def _current_link(self) -> str:
        return self.proxy.link() or proxy_manager.proxy_link(
            self.cfg.ensure_secret(),
            int(self.cfg.proxy.get("port", 1443)),
            fake_tls_domain=self.cfg.proxy.get("fake_tls_domain", "") or "",
        )

    def _show_link(self, copy: bool) -> None:
        link = self._current_link()
        self.sys_ok(t("Telegram link:"))
        self.sys("  " + link, style="#cfcfcf")
        if copy and _copy_clipboard(link):
            self.sys_ok(t("(copied to clipboard)"))

    async def _update_proxy(self) -> None:
        ok = await asyncio.to_thread(updates.update_proxy, self.sys)
        self.sys_ok(t("tg-ws-proxy updated.")) if ok else self.sys_err(t("tg-ws-proxy update failed."))

    # ---------- kzapret ----------
    async def _cmd_kzapret(self, args: List[str]) -> None:
        if not args:
            self.sys_err(t("Specify: autostart|update|status|lang"))
            return
        sub = args[0].lower()
        rest = args[1:]
        if sub == "autostart":
            mode = (rest[0].lower() if rest else "status")
            if mode == "on":
                ok, out = await asyncio.to_thread(autostart.enable)
                self.cfg.data["autostart"] = bool(ok)
                self.cfg.save()
                self.sys_ok(t("Autostart enabled.")) if ok else self.sys_err(t("Failed: {out}", out=out))
            elif mode == "off":
                ok, out = await asyncio.to_thread(autostart.disable)
                self.cfg.data["autostart"] = False
                if self.cfg.zapret.get("autotest"):
                    self.cfg.zapret["autotest"] = False
                    self.sys(t("Autotest disabled because autostart was turned off."))
                self.cfg.save()
                self.sys_ok(t("Autostart disabled.")) if ok else self.sys_err(t("Failed: {out}", out=out))
            else:
                en = await asyncio.to_thread(autostart.is_enabled)
                self.sys(t("Autostart: {state}", state=t("enabled") if en else t("disabled")))
        elif sub == "update":
            self.sys(t("Checking updates..."))
            self._spawn(self._check_updates())
        elif sub == "status":
            self._cmd_status()
        elif sub == "lang":
            if not rest or rest[0].lower() not in ("en", "ru"):
                self.sys_err(t("Usage: /kzapret lang <en|ru>"))
                return
            lang = rest[0].lower()
            self.cfg.data["lang"] = lang
            self.cfg.save()
            set_lang(lang)
            self.sys(t("Language: {lang}", lang=lang))
        else:
            self.sys_err(t("Unknown kzapret subcommand: {sub}", sub=sub))

    def _cmd_status(self) -> None:
        self.sys(t("zapret: {zs} (v{zv}) | tg-ws-proxy: {ps} (v{pv})",
                   zs=t("running") if self.zapret.running else t("stopped"),
                   zv=zapret_manager.version(),
                   ps=t("running") if self.proxy.running else t("stopped"),
                   pv=proxy_manager.version()))

    async def _check_updates(self) -> None:
        zi = await asyncio.to_thread(updates.check_zapret)
        pi = await asyncio.to_thread(updates.check_proxy)
        for info in (zi, pi):
            if info.error:
                self.sys_err(t("{name}: {error}", name=info.name, error=info.error))
            elif info.has_update:
                cmd = "/zapret update" if info.name == "zapret" else "/tg-ws-proxy update"
                self.sys(t("{name}: update available {current} -> {latest}. Command: {cmd}",
                           name=info.name, current=info.current, latest=info.latest, cmd=cmd),
                         style=ST_WARN)
            else:
                self.sys_ok(t("{name}: up to date ({current}).", name=info.name, current=info.current))

    # ---------- misc ----------
    def action_clear_logs(self) -> None:
        for wid in ("zapret", "proxy", "system"):
            self.screen_stack[0].query_one(f"#{wid}", RichLog).clear()
        self.sys(t("Logs cleared."))

    async def _cmd_quit(self) -> None:
        await self.action_quit_app()

    async def action_quit_app(self) -> None:
        self.sys(t("Stopping zapret and tg-ws-proxy..."))
        await self.zapret.stop()
        await self.proxy.stop()
        self.exit()

    async def on_unmount(self) -> None:
        await self.zapret.stop()
        await self.proxy.stop()
