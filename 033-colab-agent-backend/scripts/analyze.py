"""#033: Codex default model vs Codex pointed at a Colab-hosted open model. Tables + chart.
CU accounting comes from results/cu_log.csv (colab usage readings) and results/session.json (start/stop epochs)."""
import csv, json, os, statistics as st
import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
E = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); R = f"{E}/results"
CU_USD = 9.99 / 100  # Colab Pay As You Go: $9.99 per 100 compute units (colab.research.google.com/signup)
rows = list(csv.DictReader(open(f"{R}/runs.csv")))
S = json.load(open(f"{R}/session.json")) if os.path.exists(f"{R}/session.json") else {}
arms = [a for a in ("codex_default", "codex_default_lean", "colab_qwen3coder30b") if any(r["cond"] == a for r in rows)]
out = []
for a in arms:
    v = [r for r in rows if r["cond"] == a]; m = lambda c: st.mean(float(x[c]) for x in v)
    d = dict(arm=a, runs=len(v), passed=sum(int(x["passed"]) for x in v), pass_rate=round(sum(int(x["passed"]) for x in v) / len(v), 3),
             timeouts=sum(x["timed_out"] == "True" for x in v), wall_mean_s=round(m("wall_s"), 1), wall_median_s=round(st.median(float(x["wall_s"]) for x in v), 1),
             total_tokens_mean=round(m("total_tokens")), output_tokens_mean=round(m("output_tokens")), model_calls_mean=round(m("model_calls"), 2),
             api_equiv_usd_per_task=round(m("est_cost_usd"), 4))
    if a.startswith("colab") and S:
        run_s = sum(float(x["wall_s"]) for x in v)
        d.update(cu_session_total=S.get("cu_session"), cu_per_task_incl_setup=round(S["cu_session"] / len(v), 4),
                 cu_per_task_runtime_only=round(S["cu_rate_per_h"] * run_s / 3600 / len(v), 4),
                 usd_per_task_incl_setup=round(S["cu_session"] / len(v) * CU_USD, 4),
                 usd_per_task_runtime_only=round(S["cu_rate_per_h"] * run_s / 3600 / len(v) * CU_USD, 4),
                 api_equiv_if_gpt61sol_prices=round(m("est_cost_usd"), 4))
    out.append(d)
keys = sorted({k for d in out for k in d}, key=lambda k: list(out[-1]).index(k) if k in out[-1] else -1)
with open(f"{R}/summary.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for d in out for k in d))); w.writeheader(); w.writerows(out)
for d in out: print(d)
T = sorted({r["task"] for r in rows})
with open(f"{R}/per_task.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["task"] + [f"{a}_{k}" for a in arms for k in ("passes", "wall_mean_s", "tokens_mean")])
    for t in T:
        line = [t]
        for a in arms:
            v = [r for r in rows if r["cond"] == a and r["task"] == t]
            line += [f"{sum(int(x['passed']) for x in v)}/{len(v)}", round(st.mean(float(x['wall_s']) for x in v), 1) if v else "",
                     round(st.mean(float(x['total_tokens']) for x in v)) if v else ""]
        w.writerow(line)
lab = {"codex_default": "gpt-6.1-sol\n(ChatGPT Plus)", "codex_default_lean": "gpt-6.1-sol lean\n(Colab-arm flags)", "colab_qwen3coder30b": "Qwen3-Coder-30B-A3B\n(Ollama, Colab L4)"}
col = {"codex_default": "tab:blue", "codex_default_lean": "tab:cyan", "colab_qwen3coder30b": "tab:orange"}
fig, ax = plt.subplots(1, 3, figsize=(16, 5))
x = np.arange(len(arms))
ax[0].bar(x, [d["pass_rate"] * 100 for d in out], color=[col[a] for a in arms])
for i, d in enumerate(out): ax[0].text(i, d["pass_rate"] * 100 + 2, f"{d['passed']}/{d['runs']}", ha="center")
ax[0].set_ylim(0, 115); ax[0].set_ylabel("pass rate (%)"); ax[0].set_title("Tasks passed (T01–T11 × 2)")
for i, a in enumerate(arms):
    ys = [float(r["wall_s"]) for r in rows if r["cond"] == a]
    ax[1].scatter(np.full(len(ys), i) + np.random.uniform(-.12, .12, len(ys)), ys, color=col[a], alpha=.7)
    ax[1].hlines(st.median(ys), i - .25, i + .25, color="k")
ax[1].set_yscale("log"); ax[1].set_ylabel("wall time per task (s, log)"); ax[1].set_title("Wall time per task (bar = median)")
cost = []
for d in out:
    cost.append(d.get("usd_per_task_incl_setup", d["api_equiv_usd_per_task"]))
ax[2].bar(x, [c * 100 for c in cost], color=[col[a] for a in arms])
for i, (d, c) in enumerate(zip(out, cost)):
    t = f"{c*100:.2f}¢\n(API-equiv. est.)" if d["arm"].startswith("codex_default") else f"{c*100:.2f}¢\n({d['cu_per_task_incl_setup']:.3f} CU incl. setup)"
    ax[2].text(i, c * 100 * 1.02, t, ha="center", fontsize=8)
ax[2].set_ylabel("¢ per task"); ax[2].set_title("Cost per task: API-equivalent vs Colab CU"); ax[2].set_ylim(0, max(cost) * 100 * 1.35)
for a_ in ax: a_.set_xticks(x); a_.set_xticklabels([lab[a] for a in arms], fontsize=8)
fig.suptitle("#033 Colab as your agent's backend: Codex CLI on its default model vs an open coder served from Colab")
fig.tight_layout(); fig.savefig(f"{R}/chart.png", dpi=110)
