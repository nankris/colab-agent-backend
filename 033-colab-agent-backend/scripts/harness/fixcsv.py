# Re-align runs.csv written partly with the pre-rl FIELDS (37 cols) and partly with new FIELDS (41 cols).
import csv, sys, os, json, glob
sys.path.insert(0, os.path.dirname(__file__)); import run_cc
p = sys.argv[1]; rows = list(csv.reader(open(p)))
old_hdr = rows[0]; new = run_cc.FIELDS; out = []
for r in rows[1:]:
    if len(r) == len(new): d = dict(zip(new, r))
    else: d = dict(zip(old_hdr, r))
    if not d.get("rl_5h_util"):
        raw = os.path.join(os.path.dirname(os.path.dirname(p)), d["raw_jsonl"])
        st = run_cc.parse_stream(raw); rl = st["rl"]; w = rl.get("unifiedWindows") or {}
        d.update(rl_status=rl.get("status", ""), rl_5h_util=(w.get("five_hour") or {}).get("utilization", ""),
                 rl_7d_util=(w.get("seven_day") or {}).get("utilization", ""), rl_5h_resets=(w.get("five_hour") or {}).get("resetsAt", ""))
    out.append(d)
w = csv.DictWriter(open(p, "w"), fieldnames=new); w.writeheader(); w.writerows(out); print(len(out), "rows fixed")
