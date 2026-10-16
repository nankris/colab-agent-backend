#!/bin/bash
# Run on the VM over ssh: start Ollama bound to 127.0.0.1 only, then pull the model in the background.
pgrep -x ollama >/dev/null || OLLAMA_HOST=127.0.0.1:11434 OLLAMA_CONTEXT_LENGTH=${TIG_CTX:-65536} OLLAMA_FLASH_ATTENTION=1 \
  OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_KEEP_ALIVE=-1 OLLAMA_NUM_PARALLEL=1 setsid nohup ollama serve > /content/ollama.log 2>&1 < /dev/null &
sleep 4; ollama --version
setsid nohup bash -c "date +%s > /content/pull.start; ollama pull ${TIG_MODEL:-qwen3-coder:30b} > /content/pull.log 2>&1; date +%s > /content/pull.done" > /dev/null 2>&1 < /dev/null &
