#!/bin/bash
# chain_cc.sh EXP COND REP NPKG [extra claude args...]
# Fix SUITE14 packages one per turn in ONE working dir. Default: one long Claude session (claude -p --resume <id>).
# With FRESH=1 every package gets its own fresh claude -p (no resume) in the same dir.
source /workspace/tools/setup.sh >/dev/null 2>&1
H=/workspace/work/tig/_harness
EXP=$1; COND=$2; REP=$3; N=$4; shift 4
FL=(); for c in "$@"; do FL+=(--flag="$c"); done
WORK=$(mktemp -d /tmp/tigccchain_XXXX); rm -rf "$WORK"; cp -r $H/fixtures/SUITE14 "$WORK"
SID=""
for pkg in $(ls $H/fixtures/SUITE14 | grep -v run_all.js | sort | head -n $N); do
  [ -e $H/CC_QUOTA_HIT ] && { echo "quota flag, stopping chain"; break; }
  PROMPT="Make \`node test.js\` pass inside the package folder \`$pkg/\` by fixing that package's code. Do not edit any test.js. Only work on $pkg/ in this turn."
  if [ -z "$SID" ] || [ "${FRESH:-0}" = 1 ]; then
    python3 $H/run_cc.py --exp "$EXP" --cond "$COND" --task "$H/fixtures/SUITE14/$pkg" --rep "$REP" --tag chain \
      --workdir "$WORK" --persist --check "cd $pkg && node test.js" --prompt "$PROMPT" --timeout 600 "${FL[@]}"
    rc=$?
    [ "${FRESH:-0}" = 1 ] || SID=$(python3 -c "import csv,sys; rows=list(csv.DictReader(open(sys.argv[1]))); print([r for r in rows if r['cond']==sys.argv[2] and str(r['rep'])==sys.argv[3]][-1]['session_id'])" "$EXP/results/runs.csv" "$COND" "$REP")
  else
    python3 $H/run_cc.py --exp "$EXP" --cond "$COND" --task "$H/fixtures/SUITE14/$pkg" --rep "$REP" --tag chain \
      --workdir "$WORK" --resume "$SID" --check "cd $pkg && node test.js" --prompt "$PROMPT" --timeout 600 "${FL[@]}"
    rc=$?
  fi
  [ $rc -eq 3 ] && { echo "quota hit during chain"; break; }
done
cd "$WORK"; echo "CHAIN_DONE exp=$EXP cond=$COND rep=$REP session=$SID $(node run_all.js 2>/dev/null | grep SUMMARY)"
rm -rf "$WORK"
