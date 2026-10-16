# #033 — Colab as your agent's backend

Codex CLI 0.162.1 on its normal ChatGPT Plus backend vs the same Codex CLI pointed at an open coder model served from a Colab GPU.

| | |
|---|---|
| Engine | Ollama 0.40.4 on the Colab VM (bound to 127.0.0.1:11434), reached over one `colab ssh --proxy-mode` ControlMaster tunnel (`scripts/tunnel.sh`), plus a local Responses-API stream shim (`scripts/responses_shim.py`) |
| Model | `qwen3-coder:30b` (Qwen3-Coder-30B-A3B-Instruct, Ollama default 4-bit Q4_K_M), 64K context, q8_0 KV cache, flash attention |
| GPU | 1× NVIDIA L4 24 GB (Colab session `codex-033`) |
| CU used | **≈1.21 CU** (session 20:50:59–21:38:15 UTC, 0.79 h × 1.54 CU/h). Only ≈0.55 CU of that was allocation → last task; the rest was idle after a sandbox reboot cut the tunnel. Cap was 5 CU. |
| Baseline | `gpt-6.1-sol` via ChatGPT Plus, two arms: default flags, and "lean" (same `--disable …`/web_search flags the Colab arm needed) |
| Task set | `SUITE14` T01–T11 (small JS edit/fix tasks with `node test.js`), 2 reps per arm, 66 runs |

## Headline
| arm | pass | median wall | mean tokens | model calls | cost/task |
|---|---|---|---|---|---|
| Codex + gpt-6.1-sol (default) | 22/22 | 16.8 s | 59.0K | 4.0 | 1.91¢ API-equiv. (covered by Plus) |
| Codex + gpt-6.1-sol (lean flags) | 22/22 | 14.7 s | 42.7K | 4.05 | 3.40¢ API-equiv. |
| Codex + Qwen3-Coder-30B on Colab L4 | 19/22 | 21.4 s | 55.2K | 8.8 | 0.55¢ incl. setup / 0.10¢ runtime-only (Colab CU at $9.99/100 CU) |

See `writeup.md` and `results/chart.png`.

## Layout
- `scripts/alloc_retry.sh` — retry `colab new -s codex-033 --gpu L4` (account was at its concurrent-session limit)
- `scripts/vm_setup.py`, `scripts/vm_serve.sh` — install/start Ollama and pull the model on the VM
- `scripts/tunnel.sh` — ssh port-forward sandbox:18434 → VM:11434
- `scripts/responses_shim.py` — fixes Ollama's streamed `/v1/responses` (see writeup); listens on 18436
- `scripts/logproxy.py` — request logger used while debugging the probe
- `scripts/start_arms.sh`, `scripts/driver.sh`, `scripts/jobs_*.txt`, `scripts/lean_flags.txt` — run the arms
- `scripts/harness/` — local copy of `_harness` (`run_one.py`, fixtures)
- `scripts/analyze.py` — `results/summary.csv`, `results/per_task.csv`, `results/chart.png`
- `results/runs.csv`, `results/raw/` — one row / JSONL per run; `results/probe/` — failed first probe (pre-shim)
- `results/session.json`, `results/cu_log.txt`, `results/alloc.log`, `results/vm_setup.log`, `results/shim.log` — CU and friction evidence
