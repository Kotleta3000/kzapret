"""First-run wizard: clone, tests, config choice, proxy, autostart. Console flow."""
from __future__ import annotations

import asyncio
import subprocess
import sys
import webbrowser

from . import autostart, config, paths, proxy_manager, updates, zapret_manager
from .i18n import set_lang, t

_NO_WINDOW = 0x08000000


def _p(msg: str = "") -> None:
    print(msg, flush=True)


def _ask(prompt: str, default: str = "") -> str:
    try:
        ans = input(prompt).strip()
    except EOFError:
        ans = ""
    return ans or default


def _ask_yes(prompt: str, default_yes: bool = True) -> bool:
    suffix = " [Y/n]: " if default_yes else " [y/N]: "
    ans = _ask(prompt + suffix).lower()
    if not ans:
        return default_yes
    return ans in ("y", "yes", "д", "да")


# ---------- preparation ----------

def _choose_language(cfg: config.Config) -> None:
    # asked before language is set, so the prompt is bilingual
    ans = _ask("Language / Язык:  [1] English   [2] Русский   (default 1): ")
    lang = "ru" if ans.strip() == "2" else "en"
    cfg.data["lang"] = lang
    cfg.save()
    set_lang(lang)


def _ensure_repos() -> bool:
    ok = True
    if not zapret_manager.installed():
        _p(t("Cloning zapret-discord-youtube ..."))
        if not updates.clone(paths.ZAPRET_REPO, paths.ZAPRET_DIR, _p):
            _p(t("[!] Could not clone zapret."))
            ok = False
    else:
        _p(t("zapret already present."))
    if not proxy_manager.installed():
        _p(t("Cloning tg-ws-proxy ..."))
        if not updates.clone(paths.PROXY_REPO, paths.PROXY_DIR, _p):
            _p(t("[!] Could not clone tg-ws-proxy."))
            ok = False
    else:
        _p(t("tg-ws-proxy already present."))
    return ok


def _ensure_proxy_deps() -> None:
    py = paths.python_for_proxy()
    check = subprocess.run([py, "-c", "import cryptography"],
                           capture_output=True, creationflags=_NO_WINDOW)
    if check.returncode != 0:
        _p(t("Installing cryptography for the proxy ..."))
        subprocess.run([py, "-m", "pip", "install", "cryptography"], creationflags=_NO_WINDOW)


def _remove_zapret_service_if_present() -> None:
    q = subprocess.run(["sc", "query", "zapret"], capture_output=True,
                       text=True, errors="replace", creationflags=_NO_WINDOW)
    if q.returncode == 0 and "1060" not in (q.stdout + q.stderr):
        _p(t("The 'zapret' service is present - it must be removed for tests."))
        if _ask_yes(t("Remove the zapret service?"), True):
            subprocess.run(["net", "stop", "zapret"], capture_output=True, creationflags=_NO_WINDOW)
            subprocess.run(["sc", "delete", "zapret"], capture_output=True, creationflags=_NO_WINDOW)
            _p(t("Service removed."))


# ---------- wizard steps ----------

def _choose_config(best: str | None) -> str:
    configs = zapret_manager.list_configs()
    if best and _ask_yes(t("Best config by tests: {best}", best=best) + "\n" + t("Set it as auto?"), True):
        return best
    if not best:
        _p("\n" + t("Could not determine the best config automatically."))
    _p("\n" + t("Available configs:"))
    for i, c in enumerate(configs, 1):
        _p(f"  {i:2}. {c}")
    while True:
        ans = _ask(t("Pick a config number (1-{n}): ", n=len(configs)))
        if ans.isdigit() and 1 <= int(ans) <= len(configs):
            return configs[int(ans) - 1]
        _p(t("Invalid number, try again."))


def _choose_gamefilter() -> str:
    _p("\n" + t("Game filter (bypass for games on ports >1023):"))
    _p(t("  0. off   1. TCP+UDP   2. TCP only   3. UDP only"))
    mapping = {"0": "off", "1": "all", "2": "tcp", "3": "udp", "": "off"}
    while True:
        ans = _ask(t("Choice [0-3, default 0]: "))
        if ans in mapping:
            return mapping[ans]
        _p(t("Invalid choice."))


async def _proxy_smoke(secret: str, port: int) -> bool:
    if not proxy_manager.port_free(port):
        owner = proxy_manager.port_owner(port)
        who = f" (PID {owner[0]} {owner[1]})" if owner else ""
        _p("  " + t("[!] Port {port} is busy{who} - an old tg-ws-proxy may be running.",
                    port=port, who=who))
        _p(t("    Close it, or later change the port: /tg-ws-proxy port <n>"))
        return False

    seen = {"ok": False}

    def on_line(line: str):
        _p("  " + line)
        if "Listening on" in line or "Connect:" in line:
            seen["ok"] = True

    rt = proxy_manager.ProxyRuntime()
    await rt.start(secret, port, on_line)
    for _ in range(60):
        if seen["ok"]:
            break
        await asyncio.sleep(0.1)
    await asyncio.sleep(0.3)
    await rt.stop()
    return seen["ok"]


# ---------- main flow ----------

def run(cfg: config.Config) -> None:
    _choose_language(cfg)

    _p("=" * 64)
    _p(t("  FIRST RUN kzapret - setup"))
    _p("=" * 64)

    if not _ensure_repos():
        _p("\n" + t("[!] Repos are required. Check the internet and run again."))
        sys.exit(1)
    _ensure_proxy_deps()

    # --- zapret tests ---
    _remove_zapret_service_if_present()
    _p("\n" + t("Running zapret tests (standard / all configs)."))
    _p(t("This takes a few minutes - progress below:") + "\n")
    best = asyncio.run(zapret_manager.run_tests(_p))

    # --- choose auto config ---
    chosen = _choose_config(best)
    cfg.zapret["auto_config"] = chosen
    _p("\n" + t("Auto config: {name}", name=chosen))

    # --- game filter ---
    gf = _choose_gamefilter()
    zapret_manager.set_gamefilter(gf)
    cfg.zapret["gamefilter"] = gf
    _p(t("Game filter: {mode}", mode=gf))

    # --- ipset ---
    ip_on = _ask_yes("\n" + t("Enable ipset filter (full IP list)?"), False)
    status = zapret_manager.set_ipset(ip_on, _p)
    cfg.zapret["ipset"] = "on" if ip_on else "off"
    _p(t("ipset: {status}", status=status))

    cfg.save()

    # --- tg-ws-proxy ---
    _p("\n" + t("Setting up tg-ws-proxy (headless, no UI)..."))
    secret = cfg.ensure_secret()
    port = cfg.proxy.get("port", 1443)
    ok = asyncio.run(_proxy_smoke(secret, port))
    link = proxy_manager.proxy_link(secret, port)
    link_https = proxy_manager.proxy_link_https(secret, port)
    _p("\n" + "=" * 64)
    _p("  " + (t("Telegram proxy is ready. Link to add:") if ok
              else t("Proxy configured (starts with the panel). Link:")))
    _p("")
    _p("    " + link)
    _p("    " + link_https)
    _p("")
    _p("  " + t("Copy the link and open it, or click it to add the proxy to Telegram."))
    _p("=" * 64)
    if _ask_yes(t("Open the link now?"), False):
        try:
            webbrowser.open(link)
        except Exception:  # noqa: BLE001
            _p(t("Could not open automatically - copy the link manually."))

    # --- autostart ---
    _p("")
    if _ask_yes(t("Add kzapret to Windows autostart (start at logon)?"), False):
        done, out = autostart.enable()
        cfg.data["autostart"] = bool(done)
        _p(t("Autostart enabled.") if done else t("Could not enable autostart: {out}", out=out))
    else:
        cfg.data["autostart"] = False
        _p(t("No autostart. Enable later: /kzapret autostart on"))

    cfg.data["first_run_done"] = True
    cfg.save()
    _p("\n" + t("Setup complete.") + "\n")
