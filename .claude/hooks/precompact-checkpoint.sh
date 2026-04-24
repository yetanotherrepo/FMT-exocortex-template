#!/bin/bash
# PreCompact Checkpoint Hook
# Event: PreCompact
# Перед компрессией контекста сохраняет checkpoint: что осталось сделать.
# Записывает в .claude/checkpoint.md (gitignored).
# Read-only для агента: возвращает напоминание через additionalContext.

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')
PROJECT_DIR="${CWD:-$(pwd)}"
CHECKPOINT_FILE="$PROJECT_DIR/.claude/checkpoint.md"

# Напоминание агенту — сохранить контекст перед компрессией
jq -n --arg ctx "⚠️ PRECOMPACT: Контекст будет сжат. Перед продолжением прочитай .claude/checkpoint.md если он есть. Запиши в него: (1) Над каким РП работаешь, (2) Что осталось сделать, (3) Какой протокол выполняешь и на каком шаге, (4) Незавершённые шаги протокола (включая верификацию)." \
  '{hookSpecificOutput: {hookEventName: "PreCompact", additionalContext: $ctx}}'
exit 0
