#!/bin/bash
# wait for 012 rep3 chains, then run 012 rep4 + 006 fresh rep3
while pgrep -f "chain.sh /workspace/work/tig/012-codex-early-vs-late-compaction .* 3" >/dev/null; do sleep 10; done
[ -e /workspace/work/tig/_harness/QUOTA_HIT ] && exit 0
cd /workspace/work/tig/012-codex-early-vs-late-compaction && REPS=4 setsid nohup scripts/run_chains.sh >/dev/null 2>&1 < /dev/null &
E6=/workspace/work/tig/006-codex-cache-resumed-vs-fresh
FRESH=1 /workspace/work/tig/_harness/chain.sh $E6 fresh 3 >> $E6/results/chain.log 2>&1
