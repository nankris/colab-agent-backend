# #033 Colab as your agent's backend — writeup

## Question
Can you point Codex CLI at an open coder model you serve yourself from a Colab GPU, and how does it compare with Codex on its normal ChatGPT Plus backend on the same small coding tasks?

## Setup
- Codex CLI 0.162.1, `codex exec` via the shared harness (`run_one.py`), P=1 per arm, 900 s timeout (600 s baseline).
- Tasks: SUITE14 T01–T11 — small JavaScript bug-fix/edit tasks (`broken.js` + `test.js`; pass = test passes and `test.js` untouched). 2 reps each.
- Baseline: `gpt-6.1-sol` on ChatGPT Plus, default flags (run first, 20:15–20:23 UTC) and a "lean" arm with the same feature-disable flags as the Colab arm (run concurrently with it, 20:57–21:12 UTC).
- Colab arm: Colab L4 (24 GB), Ollama 0.40.4, `qwen3-coder:30b` (Qwen3-Coder-30B-A3B, Q4_K_M, ~19 GB), 64K context, q8_0 KV cache. Codex custom provider `wire_api="responses"` → local shim (127.0.0.1:18436) → ssh tunnel → Ollama on the VM. No public tunnel; the endpoint was only ever bound to localhost on both ends.
- API-equivalent cost uses gpt-6.1-sol list price ($2.00 in / $0.10 cached / $10.00 out per 1M) for every arm, so the Colab arm's "API-equiv." is "what those tokens would cost at gpt-6.1-sol prices". Colab cost uses $9.99 per 100 CU and a measured L4 rate of 1.54 CU/h (from successive `colab usage` readings: 2×L4 = 3.08/h).

## Results (66 runs)
| arm | pass | mean / median wall | mean tokens | mean output tok | model calls | cost per task |
|---|---|---|---|---|---|---|
| gpt-6.1-sol default | 22/22 (100%) | 19.6 / 16.8 s | 59,041 | 292 | 4.0 | 1.91¢ API-equiv. |
| gpt-6.1-sol lean | 22/22 (100%) | 20.2 / 14.7 s | 42,715 | 296 | 4.05 | 3.40¢ API-equiv. (fewer tokens but much lower cache hit rate) |
| Qwen3-Coder-30B on Colab L4 | 19/22 (86%) | 23.0 / 21.4 s | 55,189 | 787 | 8.8 | 0.55¢ (0.055 CU) incl. setup and idle; 0.10¢ (0.0099 CU) runtime-only |

- **Failures (all Colab arm):** T02_duplicate 0/2 — the file has two identical-looking functions and only one should change; Qwen edited/reasoned about the wrong one and stopped. T06_neardup 1/2 — the failing rep thrashed for 21 model calls / 154K tokens. These are edit-precision tasks; gpt-6.1-sol got both 2/2 in both arms.
- **Speed:** the L4 serves ~2.2 s per model call on average (194 calls in `shim.log`), but Qwen takes ~2× as many calls (8.8 vs 4.0: it runs `cat`, `node test.js`, patches and re-tests in small steps), so median wall is ~1.3–1.5× the baseline. One lean-baseline outlier (T08 rep 2, 137 s) was backend latency, not extra work.
- **Cost:** a single Colab L4 session costs ≈1.54 CU/h ≈ $0.15/h. This whole arm (22 tasks) consumed ≈0.55 CU from allocation to last task, ≈1.21 CU including ~26 min of idle after the crash. On ChatGPT Plus the baseline costs nothing extra until you hit the 5-hour window (it moved the primary window from 67% to 76% over 44 runs); at API prices it would be ~2–3.4¢ per task.

## Setup friction (the real cost)
1. **Allocation:** `colab new --gpu L4` was refused ("precondition failed", concurrent-session limit) for ~40 min (20:11–20:51 UTC) until another worker's session freed up. `scripts/alloc_retry.sh` polled every ~60 s.
2. **Serving:** first `ollama pull` ran before `ollama serve` was up (connection refused); fixed by `vm_serve.sh` (setsid serve, then background pull). Allocation → first real task took ~12.7 min (install + ~19 GB pull + load + debugging).
3. **Tunnel:** Colab allows one `colab ssh` per runtime, so the port-forward had to be a single ssh ControlMaster reused for all commands.
4. **Protocol bug:** first probe failed (T01 0/1, 2 model calls): Ollama 0.40.4's *streamed* `/v1/responses` gives a text message and the following function_call the same `output_index` and never closes the message, so Codex keeps the text and drops the tool call — the agent "announces" a step and ends its turn. Non-streamed responses are correct, so `responses_shim.py` requests `stream=false` and replays a well-formed SSE stream to Codex. With the shim, the arm ran cleanly.
5. **Codex warnings:** "Model metadata for `qwen3-coder:30b` not found. Defaulting to fallback metadata" on every run (harmless here), and default features (apps, multi-agent, web search, unified_exec, …) had to be disabled for the open model, hence the lean baseline arm for a fair comparison.
6. **Fragility:** a sandbox reboot at ~21:17 UTC killed the tunnel; the VM idled until Colab terminated it at 21:38 UTC. The experiment data was already complete.

## Verdict
It works: Codex CLI can drive a self-served Qwen3-Coder-30B-A3B on a Colab L4 at 86% vs 100% on these small edit tasks, ~1.3× slower per task, for ~0.1¢ of GPU time per task while warm. But the setup took ~1 h of allocation waiting plus ~13 min of serving work and a custom protocol shim, and the GPU bills while idle. For someone already on ChatGPT Plus, the normal backend is better on every axis except marginal cost; the Colab route makes sense only for batch runs long enough to amortise setup, for privacy/offline-model experiments, or once Plus quota is exhausted.

## Caveats
- Small task set (11 tasks × 2 reps), JS only; differences of 1–3 tasks are not statistically strong.
- Default and lean baselines ran at different times; lean ran concurrently with the Colab arm.
- Session end time comes from `colab log -s codex-033` (terminated, not an explicit stop from this repo); CU is computed from the measured L4 rate, not a per-session meter (the account balance also reflects other workers' sessions).
- The Colab arm's token counts come from Ollama's usage via the shim; Ollama's "cached" counts are prompt-cache reuse, not billed differently.
