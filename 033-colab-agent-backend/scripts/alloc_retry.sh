#!/bin/bash
# Retry `colab new -s codex-033 --gpu L4` every 60 s (account was at its concurrent-session limit).
source /workspace/tools/setup.sh >/dev/null 2>&1
LOG=$1; END=$(( $(date +%s) + ${2:-3600} ))
while [ $(date +%s) -lt $END ]; do
  colab sessions 2>/dev/null | grep -q '^\[codex-033\]' && { echo "$(date -u +%s) ALLOCATED" >> $LOG; exit 0; }
  out=$(timeout 150 colab new -s codex-033 --gpu L4 2>&1 | tail -1)
  echo "$(date -u +%s) $out" >> $LOG
  colab sessions 2>/dev/null | grep -q '^\[codex-033\]' && { echo "$(date -u +%s) ALLOCATED"; colab usage; } >> $LOG && exit 0
  sleep 30
done
echo "$(date -u +%s) GAVE_UP" >> $LOG
