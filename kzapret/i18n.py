"""Localization
"""
from __future__ import annotations

_LANG = "en"


def set_lang(lang: str) -> None:
    global _LANG
    _LANG = "ru" if str(lang).lower().startswith("ru") else "en"


def get_lang() -> str:
    return _LANG


def t(s: str, **kw) -> str:
    out = _RU.get(s, s) if _LANG == "ru" else s
    return out.format(**kw) if kw else out


# Русский — стиль существительных для действий: "Запуск", "Проверка", "Остановка".
_RU = {
    # --- общее / app ---
    "kzapret ready. Type /help for commands.": "kzapret готов. /help — список команд.",
    "kzapret commands:": "Команды kzapret:",
    "Unknown command: {head}. Type /help.": "Неизвестная команда: {head}. /help.",
    "Logs cleared.": "Логи очищены.",
    "Stopping zapret and tg-ws-proxy...": "Остановка zapret и tg-ws-proxy...",
    "Error: {exc}": "Ошибка: {exc}",
    "Cleanup of leftover processes...": "Очистка зависших процессов...",
    "running": "работает",
    "stopped": "остановлен",
    # --- zapret ---
    "No zapret config set. Use /zapret list and /zapret config <name>.":
        "Конфиг zapret не задан. /zapret list и /zapret config <имя>.",
    "Config not found: {name}. Use /zapret list.":
        "Конфиг не найден: {name}. /zapret list.",
    "Start zapret: {name}": "Запуск zapret: {name}",
    "zapret stopped (code {rc}).": "zapret остановлен (код {rc}).",
    "Specify: start|stop|restart|status|list|config|gamefilter|ipset|domainlists|autotest|test|update":
        "Уточните: start|stop|restart|status|list|config|gamefilter|ipset|domainlists|autotest|test|update",
    "zapret stopped.": "zapret остановлен.",
    "zapret: {state} | config: {cfg} | gamefilter: {gf} | ipset: {ip} | pid: {pid}":
        "zapret: {state} | конфиг: {cfg} | gamefilter: {gf} | ipset: {ip} | pid: {pid}",
    "Auto config: {name}": "Авто-конфиг: {name}",
    "Usage: /zapret gamefilter <off|tcp|udp|all>":
        "Использование: /zapret gamefilter <off|tcp|udp|all>",
    "Game filter: {mode} (restart zapret to apply)":
        "Game filter: {mode} (перезапуск zapret для применения)",
    "Usage: /zapret ipset <on|off>": "Использование: /zapret ipset <on|off>",
    "Changing ipset...": "Смена ipset...",
    "ipset: {status} (restart zapret to apply)":
        "ipset: {status} (перезапуск zapret для применения)",
    "Running zapret tests (a few minutes)...":
        "Запуск тестов zapret (несколько минут)...",
    "Best config by tests: {best}": "Лучший конфиг по тестам: {best}",
    "Apply: /zapret config \"{best}\"": "Применить: /zapret config \"{best}\"",
    "Could not determine best config (see the zapret log).":
        "Не удалось определить лучший конфиг (см. лог zapret).",
    "zapret paused during tests.": "zapret приостановлен на время тестов.",
    "Updating zapret...": "Обновление zapret...",
    "zapret updated.": "zapret обновлён.",
    "zapret update failed.": "Обновление zapret не удалось.",
    "Unknown zapret subcommand: {sub}": "Неизвестная подкоманда zapret: {sub}",
    # --- tg-ws-proxy ---
    "Specify: start|stop|restart|status|link|open|port|secret|update":
        "Уточните: start|stop|restart|status|link|open|port|secret|update",
    "Port {port} is busy{who}. Another tg-ws-proxy may be running.":
        "Порт {port} занят{who}. Возможно, запущен другой tg-ws-proxy.",
    "Close it and /tg-ws-proxy start, or change port: /tg-ws-proxy port <n>":
        "Закройте его и /tg-ws-proxy start, либо смените порт: /tg-ws-proxy port <n>",
    "Freeing port {port}: stopping stale process PID {pid}...":
        "Освобождение порта {port}: остановка зависшего процесса PID {pid}...",
    "Start tg-ws-proxy on 127.0.0.1:{port} (headless)":
        "Запуск tg-ws-proxy на 127.0.0.1:{port} (headless)",
    "tg-ws-proxy stopped (code {rc}).": "tg-ws-proxy остановлен (код {rc}).",
    "tg-ws-proxy stopped.": "tg-ws-proxy остановлен.",
    "tg-ws-proxy: {state} | port: {port} | pid: {pid}":
        "tg-ws-proxy: {state} | порт: {port} | pid: {pid}",
    "link: {link}": "ссылка: {link}",
    "Telegram link:": "Ссылка для Telegram:",
    "(copied to clipboard)": "(скопировано в буфер обмена)",
    "Proxy port: {port}": "Порт прокси: {port}",
    "Usage: /tg-ws-proxy port <number>": "Использование: /tg-ws-proxy port <число>",
    "Usage: /tg-ws-proxy secret <32hex|new>":
        "Использование: /tg-ws-proxy secret <32hex|new>",
    "Secret must be exactly 32 hex chars.":
        "Секрет должен быть ровно 32 hex-символа.",
    "Secret updated.": "Секрет обновлён.",
    "Opening: {link}": "Открытие: {link}",
    "Could not open: {exc}": "Не удалось открыть: {exc}",
    "Updating tg-ws-proxy...": "Обновление tg-ws-proxy...",
    "tg-ws-proxy updated.": "tg-ws-proxy обновлён.",
    "tg-ws-proxy update failed.": "Обновление tg-ws-proxy не удалось.",
    "Unknown tg-ws-proxy subcommand: {sub}":
        "Неизвестная подкоманда tg-ws-proxy: {sub}",
    # --- kzapret ---
    "Specify: autostart|update|status|lang": "Уточните: autostart|update|status|lang",
    "Autostart enabled.": "Автозагрузка включена.",
    "Autostart disabled.": "Автозагрузка выключена.",
    "Failed: {out}": "Не удалось: {out}",
    "Autostart: {state}": "Автозагрузка: {state}",
    "enabled": "включена",
    "disabled": "выключена",
    "Checking updates...": "Проверка обновлений...",
    "{name}: update available {current} -> {latest}. Command: {cmd}":
        "{name}: доступно обновление {current} -> {latest}. Команда: {cmd}",
    "{name}: up to date ({current}).": "{name}: актуальная версия ({current}).",
    "{name}: {error}": "{name}: {error}",
    "zapret: {zs} (v{zv}) | tg-ws-proxy: {ps} (v{pv})":
        "zapret: {zs} (v{zv}) | tg-ws-proxy: {ps} (v{pv})",
    "Language: {lang}": "Язык: {lang}",
    "Usage: /kzapret lang <en|ru>": "Использование: /kzapret lang <en|ru>",
    "Unknown kzapret subcommand: {sub}": "Неизвестная подкоманда kzapret: {sub}",
    # --- command descriptions (/help) ---
    "show this command list": "список команд",
    "start zapret (default: auto config)": "запуск zapret (по умолчанию авто-конфиг)",
    "stop zapret (winws)": "остановка zapret (winws)",
    "restart zapret": "перезапуск zapret",
    "zapret state and current config": "состояние zapret и текущий конфиг",
    "list available configs": "список доступных конфигов",
    "set auto config (and restart)": "выбор авто-конфига (и перезапуск)",
    "game filter for games (ports >1023)": "game filter для игр (порты >1023)",
    "ipset filter (full list / off)": "ipset-фильтр (полный список / выкл)",
    "run tests, find the best config": "тесты, поиск лучшего конфига",
    "update zapret (git pull)": "обновление zapret (git pull)",
    "start the Telegram proxy (headless)": "запуск прокси для Telegram (headless)",
    "stop the proxy": "остановка прокси",
    "restart the proxy": "перезапуск прокси",
    "proxy state": "состояние прокси",
    "show and copy the proxy link": "показ и копирование ссылки прокси",
    "open the proxy link (add to Telegram)": "открытие ссылки прокси (добавить в Telegram)",
    "change proxy port (default 1443)": "смена порта прокси (по умолчанию 1443)",
    "set/regenerate the secret": "задать/перегенерировать секрет",
    "update tg-ws-proxy (git pull)": "обновление tg-ws-proxy (git pull)",
    "autostart kzapret at Windows logon": "автозагрузка kzapret при входе в Windows",
    "check updates for both tools": "проверка обновлений обеих утилит",
    "interface language": "язык интерфейса",
    "overall state": "общее состояние",
    "clear on-screen logs": "очистка логов на экране",
    "stop everything and quit (alias: /exit)": "остановка всего и выход (alias: /exit)",
    # --- first run wizard ---
    "  FIRST RUN kzapret - setup": "  ПЕРВЫЙ ЗАПУСК kzapret - настройка",
    "zapret already present.": "zapret уже на месте.",
    "tg-ws-proxy already present.": "tg-ws-proxy уже на месте.",
    "Cloning zapret-discord-youtube ...": "Клонирование zapret-discord-youtube ...",
    "Cloning tg-ws-proxy ...": "Клонирование tg-ws-proxy ...",
    "[!] Could not clone zapret.": "[!] Не удалось склонировать zapret.",
    "[!] Could not clone tg-ws-proxy.": "[!] Не удалось склонировать tg-ws-proxy.",
    "Installing cryptography for the proxy ...": "Установка cryptography для прокси ...",
    "The 'zapret' service is present - it must be removed for tests.":
        "Служба 'zapret' установлена - для тестов её нужно убрать.",
    "Remove the zapret service?": "Удалить службу zapret?",
    "Service removed.": "Служба удалена.",
    "[!] Repos are required. Check the internet and run again.":
        "[!] Без репозиториев нельзя продолжить. Проверьте интернет и запустите снова.",
    "Running zapret tests (standard / all configs).":
        "Запуск тестов zapret (standard / all configs).",
    "This takes a few minutes - progress below:":
        "Это займёт несколько минут - прогресс ниже:",
    "Set it as auto?": "Поставить его в авто?",
    "Could not determine the best config automatically.":
        "Не удалось определить лучший конфиг автоматически.",
    "Available configs:": "Доступные конфиги:",
    "Pick a config number (1-{n}): ": "Выберите номер конфига (1-{n}): ",
    "Invalid number, try again.": "Неверный номер, попробуйте снова.",
    "Game filter (bypass for games on ports >1023):":
        "Game filter (обход для игр на портах >1023):",
    "  0. off   1. TCP+UDP   2. TCP only   3. UDP only":
        "  0. выкл   1. TCP+UDP   2. только TCP   3. только UDP",
    "Choice [0-3, default 0]: ": "Выбор [0-3, по умолчанию 0]: ",
    "Invalid choice.": "Неверный выбор.",
    "Game filter: {mode}": "Game filter: {mode}",
    "Enable ipset filter (full IP list)?": "Включить ipset-фильтр (полный список IP)?",
    "ipset: {status}": "ipset: {status}",
    "Setting up tg-ws-proxy (headless, no UI)...":
        "Настройка tg-ws-proxy (headless, без интерфейса)...",
    "[!] Port {port} is busy{who} - an old tg-ws-proxy may be running.":
        "[!] Порт {port} занят{who} - возможно, запущен старый tg-ws-proxy.",
    "    Close it, or later change the port: /tg-ws-proxy port <n>":
        "    Закройте его, либо позже смените порт: /tg-ws-proxy port <n>",
    "Telegram proxy is ready. Link to add:":
        "Прокси для Telegram готов. Ссылка для добавления:",
    "Proxy configured (starts with the panel). Link:":
        "Прокси настроен (стартует вместе с панелью). Ссылка:",
    "Copy the link and open it, or click it to add the proxy to Telegram.":
        "Скопируйте ссылку и откройте её, либо нажмите, чтобы добавить прокси в Telegram.",
    "Open the link now?": "Открыть ссылку сейчас?",
    "Could not open automatically - copy the link manually.":
        "Не удалось открыть автоматически - скопируйте ссылку вручную.",
    "Add kzapret to Windows autostart (start at logon)?":
        "Добавить kzapret в автозагрузку Windows (старт при входе)?",
    "Could not enable autostart: {out}": "Не удалось включить автозагрузку: {out}",
    "No autostart. Enable later: /kzapret autostart on":
        "Без автозагрузки. Включить позже: /kzapret autostart on",
    "Setup complete.": "Настройка завершена.",
    # --- списки доменов (/zapret domainlists) ---
    "edit domain lists (opens a separate window)": "редактор списков доменов (отдельное окно)",
    "test the config at system start (needs autostart)":
        "тест конфига при старте системы (нужен автозапуск)",
    "list number or /command": "номер списка или /команда",
    "Domain lists - choose a list": "Списки доменов - выберите список",
    "Enter a list number or name  |  /reset <list>  |  /exit":
        "Введите номер или имя списка  |  /reset <список>  |  /exit",
    "No lists found in zapret/lists/. Is zapret installed?":
        "В zapret/lists/ списков не найдено. zapret установлен?",
    "{name} - {n} entries": "{name} - записей: {n}",
    "/add <domain>   /delete <number>   /reset <list>   /back   /exit":
        "/add <домен>   /delete <номер>   /reset <список>   /back   /exit",
    "Enter a list number (1-{n}) or name.": "Введите номер списка (1-{n}) или имя.",
    "Unknown command: {cmd}": "Неизвестная команда: {cmd}",
    "Select a list first.": "Сначала выберите список.",
    "Usage: /add <domain>": "Использование: /add <домен>",
    "Usage: /delete <number>": "Использование: /delete <номер>",
    "Usage: /reset <list>": "Использование: /reset <список>",
    "Unknown list: {name}": "Неизвестный список: {name}",
    "Added: {entry}": "Добавлено: {entry}",
    "Deleted #{n}: {entry}": "Удалено #{n}: {entry}",
    "Resetting {name} from Flowseal GitHub...": "Сброс {name} из GitHub Flowseal...",
    "{name} reset to the original list.": "{name} сброшен до оригинального списка.",
    "Empty value.": "Пустое значение.",
    "Value must not contain spaces.": "Значение не должно содержать пробелов.",
    "Already in the list: {entry}": "Уже есть в списке: {entry}",
    "Number must be 1..{n}": "Номер должен быть от 1 до {n}",
    "git is not installed or not in PATH.": "git не установлен или не найден в PATH.",
    "git clone failed: {err}": "Не удалось клонировать репозиторий (git): {err}",
    "{name} does not exist in the original repository.":
        "{name} отсутствует в оригинальном репозитории.",
    "Domain lists changed.": "Списки доменов изменены.",
    "Restarting zapret to apply the changes...": "Перезапуск zapret для применения изменений...",
    "Changes will apply on next zapret start.": "Изменения применятся при следующем запуске zapret.",
    # --- автотест (/zapret autotest) ---
    "Autotest requires autostart. Enable it first: /kzapret autostart on":
        "Автотест работает только с автозагрузкой. Сначала: /kzapret autostart on",
    "Autotest enabled (runs at system start).": "Автотест включён (запускается при старте системы).",
    "Autotest disabled.": "Автотест выключен.",
    "Autotest: {state}": "Автотест: {state}",
    "Usage: /zapret autotest <on|off>": "Использование: /zapret autotest <on|off>",
    "Autotest disabled because autostart was turned off.":
        "Автотест выключен, так как выключена автозагрузка.",
    "Autotest: waiting for network...": "Автотест: ожидание сети...",
    "Autotest: no network, starting the current config without testing.":
        "Автотест: сети нет, запускаю текущий конфиг без теста.",
    "Autotest: checking {name}...": "Автотест: проверка {name}...",
    "Autotest: all {n} targets reachable - keeping {name}.":
        "Автотест: доступны все цели ({n}) - оставляю {name}.",
    "Autotest: {bad} of {n} targets failed ({names}). Testing all configs...":
        "Автотест: недоступно целей {bad} из {n} ({names}). Тест всех конфигов...",
    "Autotest: no auto config yet, testing all configs...":
        "Автотест: авто-конфиг не задан, тест всех конфигов...",
    "Autotest: switched to {name}.": "Автотест: переключено на {name}.",
    "Autotest: no best config found, keeping {name}.":
        "Автотест: лучший конфиг не найден, оставляю {name}.",
    "Autotest: no best config found and no auto config set.":
        "Автотест: лучший конфиг не найден, авто-конфиг не задан.",
    # --- console (__main__) ---
    "[!] Warning: no administrator rights. winws (zapret) requires admin.":
        "[!] Внимание: нет прав администратора. winws (zapret) требует админ-прав.",
    "    Launch via kzapret.bat (it requests elevation).":
        "    Запускайте через kzapret.bat (он сам запросит повышение прав).",
    "Checking updates (GitHub Flowseal)...":
        "Проверка обновлений (GitHub Flowseal)...",
    "  {name}: new version {current} -> {latest}":
        "  {name}: новая версия {current} -> {latest}",
    "  Update {name}?": "  Обновить {name}?",
    "  Updated.": "  Обновлено.",
    "  Update failed.": "  Не удалось обновить.",
    "  {name}: up to date ({current}).": "  {name}: актуальная версия ({current}).",
    "  KZAPRET COMMANDS": "  КОМАНДЫ kzapret",
    "Press Enter to start zapret and tg-ws-proxy in auto mode...":
        "Нажмите Enter, чтобы запустить zapret и tg-ws-proxy в авто-режиме...",
}
