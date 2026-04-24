---
name: week-close
description: "Протокол закрытия недели (Week Close). Алиас для /run-protocol week-close -- симметрия с /day-open."
argument-hint: ""
version: 1.1.0
---

# Week Close (алиас)

> **Симметрия:** `/day-open` открывает, `/week-close` закрывает неделю.
> **Реализация:** делегирует в `/run-protocol week-close`.

Выполни `/run-protocol week-close` с полным алгоритмом из `memory/protocol-close.md § Неделя`.

## Платформенные шаги (выполняются всегда)

### Скан незакоммиченных файлов

> Скрипт лежит в FMT-exocortex-template. Использует `$IWE_WORKSPACE` env var
> (должен быть set в окружении на реальный path IWE, включая non-стандартные
> пути типа `~/Documents/IWE`). Fallback на `~/IWE` для стандартной установки.

```bash
IWE="${IWE_WORKSPACE:-$HOME/IWE}"
WORKSPACE_DIR="$IWE" bash "$IWE/FMT-exocortex-template/scripts/check-dirty-repos.sh"
```

Если есть грязные репо → закоммитить и запушить ДО завершения Week Close.
