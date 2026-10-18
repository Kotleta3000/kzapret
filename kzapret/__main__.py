"""Entry point: python -m kzapret [--auto]."""
from __future__ import annotations

import argparse
import ctypes
import datetime
import sys
import traceback

from . import commands, config, firstrun, paths, updates
from .app import KzapretApp
from .i18n import set_lang, t


def _log_crash(exc: BaseException) -> None:
    """Write any uncaught failure to logs/kzapret.log and to the screen."""
    try:
        paths.LOG_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().isoformat(timespec="seconds")
        with open(paths.LOG_DIR / "kzapret.log", "a", encoding="utf-8") as f:
            f.write(f"\n===== CRASH {stamp} =====\n")
            f.write("".join(traceback.format_exception(exc)))
    except Exception:  # noqa: BLE001
        pass
    print("\n[kzapret] error:\n", flush=True)
    traceback.print_exc()


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:  # noqa: BLE001
        return False


def _print_help_console() -> None:
    print("\n" + "=" * 64)
    print(t("  KZAPRET COMMANDS"))
    print("=" * 64)
    lines = [(left, t(desc)) for left, desc in commands.help_lines()]
    width = max(len(left) for left, _ in lines)
    for left, desc in lines:
        print(f"  {left.ljust(width + 2)}{desc}")
    print("=" * 64)


def _check_updates_console(cfg: config.Config) -> None:
    print(t("Checking updates (GitHub Flowseal)..."), flush=True)
    for info, apply_fn in (
        (updates.check_zapret(), updates.update_zapret),
        (updates.check_proxy(), updates.update_proxy),
    ):
        if info.error:
            print(f"  {info.name}: {info.error}")
        elif info.has_update:
            print(t("  {name}: new version {current} -> {latest}",
                    name=info.name, current=info.current, latest=info.latest))
            ans = input(t("  Update {name}?", name=info.name) + " [Y/n]: ").strip().lower()
            if ans in ("", "y", "yes", "д", "да"):
                ok = apply_fn(lambda m: print("    " + m))
                print(t("  Updated.") if ok else t("  Update failed."))
        else:
            print(t("  {name}: up to date ({current}).", name=info.name, current=info.current))


def _run() -> None:
    ap = argparse.ArgumentParser(prog="kzapret")
    ap.add_argument("--auto", action="store_true",
                    help="autostart mode: no interactive prompts")
    args = ap.parse_args()

    if sys.platform != "win32":
        print("kzapret is for Windows.")
        sys.exit(1)

    cfg = config.load()
    set_lang(cfg.lang)

    if not _is_admin():
        print(t("[!] Warning: no administrator rights. winws (zapret) requires admin."))
        print(t("    Launch via kzapret.bat (it requests elevation)."))

    if not cfg.first_run_done:
        if args.auto:
            pass  # autostart before initial setup -> just open the TUI
        else:
            firstrun.run(cfg)   # also sets the language
            _print_help_console()
            try:
                input("\n" + t("Press Enter to start zapret and tg-ws-proxy in auto mode..."))
            except EOFError:
                pass
    elif not args.auto:
        _check_updates_console(cfg)

    KzapretApp(cfg, autostart_on_mount=True, boot_mode=args.auto).run()


def main() -> None:
    try:
        _run()
    except KeyboardInterrupt:
        pass
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001
        _log_crash(exc)
        try:
            input("\nPress Enter to close...")
        except EOFError:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
