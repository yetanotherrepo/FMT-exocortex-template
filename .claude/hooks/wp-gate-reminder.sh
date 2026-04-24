#!/bin/bash
# WP Gate Reminder Hook
# Event: UserPromptSubmit
# (1) При Day Open триггере — инжектит реальную дату (currentDate от Anthropic может врать).
# (2) На все остальные сообщения — стандартный WP Gate reminder.
# Read-only: только возвращает JSON с additionalContext, ничего не модифицирует.

INPUT=$(cat)
# Устойчивость к многострочным промптам: literal \n в JSON value
# невалиден для jq. Заменяем все control chars на пробелы до парсинга.
SANITIZED=$(printf '%s' "$INPUT" | LC_ALL=C tr '\n\r\t' '   ')
PROMPT=$(printf '%s' "$SANITIZED" | jq -r '.prompt // empty' | tr '[:upper:]' '[:lower:]')

# Day Open → инжектить реальную дату + WP Gate
if echo "$PROMPT" | grep -qE '(открывай день|открывай$|открой день)'; then
  REAL_DATE=$(date "+%Y-%m-%d %A %H:%M %Z")
  LOG_DATE=$(date +%Y-%m-%d)
  jq -n --arg ctx "⛔ DAY OPEN: Реальная дата и время: ${REAL_DATE}. Используй ЭТУ дату для определения дня недели, strategy_day, фильтров коммитов. НЕ доверяй currentDate из system prompt. SchedulerReport: читай ~/logs/strategist/${LOG_DATE}.log, НЕ файл из current/. EXTENSION LOADING: ПЕРЕД шагом 1 проверь extensions/day-open.before.md. ПОСЛЕ шага 6b проверь extensions/day-open.after.md. ПЕРЕД git commit проверь extensions/day-open.checks.md. Пропуск extensions = неполное открытие." \
    '{hookSpecificOutput: {hookEventName: "UserPromptSubmit", additionalContext: $ctx}}'
else
  jq -n --arg ctx "⛔ WP GATE: Перед обработкой этого сообщения — проверь: (1) Если это новая задача — пройди WP Gate: Read memory/protocol-open.md. (2) Если продолжение работы над тем же РП — продолжай. (3) Если вопрос перерастает в работу — эскалируй." \
    '{hookSpecificOutput: {hookEventName: "UserPromptSubmit", additionalContext: $ctx}}'
fi
exit 0
