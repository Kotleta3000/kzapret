# kzapret

A CLI manager for two [Flowseal](https://github.com/Flowseal) tools:
[**zapret**](https://github.com/Flowseal/zapret-discord-youtube) (DPI bypass) and
[**tg-ws-proxy**](https://github.com/Flowseal/tg-ws-proxy) (Telegram proxy).

One window: zapret logs on the left, tg-ws-proxy logs on the right, a command line
below. Launch once — both tools come up automatically.

## Run

1. Put the `kzapret` folder anywhere (path without non-ASCII characters).
2. Requires [Python 3.8+](https://python.org) and `git`.
3. Run **`kzapret.bat`** (it requests administrator rights — needed by winws/WinDivert).

**First run** automatically:
- clones the repos into `zapret/` and `tg-ws-proxy/`;
- runs the zapret tests (standard / all configs) and offers the best config as "auto"
  (you can decline and pick your own);
- asks about game filter and ipset;
- starts tg-ws-proxy and shows the `tg://proxy?...` link to add in Telegram;
- asks whether to add kzapret to Windows autostart;
- shows the available commands.

On every later launch kzapret checks both tools for updates on GitHub.

## Language

The interface is **English** by default. Switch anytime with `/kzapret lang ru` (or `en`).
The language is also asked on first run.

## Command line

Commands start with the tool name. **Tab** completes (press Tab again to cycle
matches); there is also a ghost suggestion (accept with →) and a hint line.
`/help` lists everything.

### zapret
| Command | Description |
|---|---|
| `/zapret start [config]` | start (default: auto config) |
| `/zapret stop` | stop winws |
| `/zapret restart` | restart |
| `/zapret status` | state and current config |
| `/zapret list` | list configs |
| `/zapret config "<name>"` | set auto config |
| `/zapret gamefilter <off\|tcp\|udp\|all>` | game filter |
| `/zapret ipset <on\|off>` | ipset filter |
| `/zapret test` | run tests, find the best config |
| `/zapret update` | update (git pull) |

### tg-ws-proxy
| Command | Description |
|---|---|
| `/tg-ws-proxy start` | start the proxy (headless) |
| `/tg-ws-proxy stop` | stop |
| `/tg-ws-proxy restart` | restart |
| `/tg-ws-proxy status` | state and link |
| `/tg-ws-proxy link` | show and copy the link |
| `/tg-ws-proxy open` | open the link (add to Telegram) |
| `/tg-ws-proxy port <number>` | change port (default 1443) |
| `/tg-ws-proxy secret <hex\|new>` | set/regenerate the secret |
| `/tg-ws-proxy update` | update (git pull) |

Aliases: `/tg`, `/tgwsproxy` → `/tg-ws-proxy`; `/z` → `/zapret`.

### kzapret / general
| Command | Description |
|---|---|
| `/kzapret autostart <on\|off\|status>` | autostart at Windows logon |
| `/kzapret update` | check updates for both tools |
| `/kzapret lang <en\|ru>` | interface language |
| `/kzapret status` | overall state |
| `/clear` | clear logs (or `Ctrl+L`) |
| `/quit` | stop everything and quit (alias `/exit`, or `Ctrl+C`) |

## Add the proxy to Telegram

Copy the link from `/tg-ws-proxy link` (or the first-run wizard) and open it —
Telegram will offer to connect the proxy:
`tg://proxy?server=127.0.0.1&port=1443&secret=dd<secret>`.

## Notes

- The proxy secret is generated once and stored in `kzapret.json`, so the link
  stays stable across restarts. `kzapret.json` is local and not committed.
- zapret runs as a child process (not a Windows service) so its output shows in
  the left pane. Game filter and ipset are toggled via the same files that the
  stock `service.bat` uses.
- `zapret/` and `tg-ws-proxy/` are cloned on first run and are not part of this repo.
