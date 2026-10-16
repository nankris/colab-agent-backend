# Runs on the Colab VM (colab exec -s codex-033 -f scripts/vm_setup.py).
# Installs Ollama, starts `ollama serve` bound to 127.0.0.1:11434 (reached from the sandbox only through
# an SSH port-forward, never exposed publicly), and pulls the model.
import subprocess, time, os, urllib.request, json
MODEL = os.environ.get("TIG_MODEL", "qwen3-coder:30b")
def sh(c): print("+", c, flush=True); r = subprocess.run(c, shell=True, capture_output=True, text=True); print((r.stdout + r.stderr)[-1500:], flush=True); return r
sh("nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv")
if not os.path.exists("/usr/local/bin/ollama"):
    sh("apt-get -qq install -y zstd pciutils lshw >/dev/null 2>&1; curl -fsSL https://ollama.com/install.sh | sh 2>&1 | tail -3")
sh("ollama --version")
env = dict(os.environ, OLLAMA_HOST="127.0.0.1:11434", OLLAMA_CONTEXT_LENGTH=os.environ.get("TIG_CTX", "65536"),
           OLLAMA_FLASH_ATTENTION="1", OLLAMA_KV_CACHE_TYPE="q8_0", OLLAMA_KEEP_ALIVE="-1", OLLAMA_NUM_PARALLEL="1")
if subprocess.run("pgrep -f 'ollama serve'", shell=True).returncode != 0:
    subprocess.Popen("nohup ollama serve > /content/ollama.log 2>&1 &", shell=True, env=env)
    time.sleep(5)
t0 = time.time(); sh(f"ollama pull {MODEL} 2>&1 | tail -2"); print("pull_s", round(time.time() - t0), flush=True)
t0 = time.time()
req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=json.dumps({"model": MODEL, "prompt": "Say OK", "stream": False}).encode())
print(json.loads(urllib.request.urlopen(req, timeout=600).read())["response"][:80], "load_s", round(time.time() - t0), flush=True)
sh("ollama ps; nvidia-smi --query-gpu=memory.used --format=csv")
