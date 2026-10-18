"""Command definitions: tree for /help, autocompletion and input hints.

Descriptions are stored in English (default language) and translated at render time.
"""
from __future__ import annotations

from typing import List, Tuple

# (command, args, english description) - single source for /help and completion.
COMMANDS: List[Tuple[str, str, str]] = [
    ("/help", "", "show this command list"),
    ("/zapret start", "[config]", "start zapret (default: auto config)"),
    ("/zapret stop", "", "stop zapret (winws)"),
    ("/zapret restart", "", "restart zapret"),
    ("/zapret status", "", "zapret state and current config"),
    ("/zapret list", "", "list available configs"),
    ("/zapret config", "<config>", "set auto config (and restart)"),
    ("/zapret gamefilter", "<off|tcp|udp|all>", "game filter for games (ports >1023)"),
    ("/zapret ipset", "<on|off>", "ipset filter (full list / off)"),
    ("/zapret domainlists", "", "edit domain lists (opens a separate window)"),
    ("/zapret autotest", "<on|off>", "test the config at system start (needs autostart)"),
    ("/zapret test", "", "run tests, find the best config"),
    ("/zapret update", "", "update zapret (git pull)"),
    ("/tg-ws-proxy start", "", "start the Telegram proxy (headless)"),
    ("/tg-ws-proxy stop", "", "stop the proxy"),
    ("/tg-ws-proxy restart", "", "restart the proxy"),
    ("/tg-ws-proxy status", "", "proxy state"),
    ("/tg-ws-proxy link", "", "show and copy the proxy link"),
    ("/tg-ws-proxy open", "", "open the proxy link (add to Telegram)"),
    ("/tg-ws-proxy port", "<number>", "change proxy port (default 1443)"),
    ("/tg-ws-proxy secret", "<hex|new>", "set/regenerate the secret"),
    ("/tg-ws-proxy update", "", "update tg-ws-proxy (git pull)"),
    ("/kzapret autostart", "<on|off|status>", "autostart kzapret at Windows logon"),
    ("/kzapret update", "", "check updates for both tools"),
    ("/kzapret lang", "<en|ru>", "interface language"),
    ("/kzapret status", "", "overall state"),
    ("/clear", "", "clear on-screen logs"),
    ("/quit", "", "stop everything and quit (alias: /exit)"),
]

# top-level aliases
ALIASES = {
    "/tgwsproxy": "/tg-ws-proxy",
    "/tg": "/tg-ws-proxy",
    "/z": "/zapret",
    "/exit": "/quit",
    "/q": "/quit",
}

# enumerated subcommand values (for hints / tab-complete)
ENUM_ARGS = {
    "/zapret gamefilter": ["off", "tcp", "udp", "all"],
    "/zapret ipset": ["on", "off"],
    "/zapret autotest": ["on", "off"],
    "/kzapret autostart": ["on", "off", "status"],
    "/kzapret lang": ["en", "ru"],
    "/tg-ws-proxy secret": ["new"],
}

_CANON = [c for c, _, _ in COMMANDS]


def normalize(value: str) -> str:
    """Expand a first-token alias (/tg -> /tg-ws-proxy)."""
    value = value.lstrip()
    if not value:
        return value
    parts = value.split(" ", 1)
    head = ALIASES.get(parts[0].lower(), parts[0])
    return head + (" " + parts[1] if len(parts) > 1 else "")


def completions(configs: List[str]) -> List[str]:
    """All candidate strings for completion (including config names)."""
    out: List[str] = list(_CANON)
    for base in ("/zapret config", "/zapret start"):
        for cfg in configs:
            out.append(f'{base} "{cfg}"')
    for base, vals in ENUM_ARGS.items():
        for v in vals:
            out.append(f"{base} {v}")
    return out


def best_suggestion(value: str, configs: List[str]) -> str | None:
    """First candidate that starts with value (for inline ghost completion)."""
    if not value:
        return None
    low = normalize(value).lower()
    for cand in completions(configs):
        if cand.lower().startswith(low) and cand.lower() != low:
            return cand
    return None


def hints(value: str, configs: List[str]) -> List[str]:
    """Short list of matching commands for the hint line under the input."""
    norm = normalize(value).lower()
    if not norm:
        return [c for c, _, _ in COMMANDS[:6]]
    matches = [c for c in completions(configs) if c.lower().startswith(norm)]
    seen: List[str] = []
    for m in matches:
        key = " ".join(m.split(" ")[:2])
        if key not in seen:
            seen.append(key)
        if len(seen) >= 8:
            break
    return seen


def help_lines() -> List[Tuple[str, str]]:
    """Returns (left, english_description) for nice /help output."""
    out = []
    for cmd, args, desc in COMMANDS:
        left = cmd + (f" {args}" if args else "")
        out.append((left, desc))
    return out
