#!/bin/bash
# Start the shim and both P=1 drivers (colab arm + lean default arm). PIDs go to results/pids.txt.
cd "$(dirname "$0")/.."
source /workspace/tools/setup.sh >/dev/null 2>&1
export NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost
setsid nohup python3 -u scripts/responses_shim.py 18436 http://127.0.0.1:18434 > results/shim.log 2>&1 < /dev/null &
echo "shim $!" > results/pids.txt
echo "$(date -u +%s) before_colab_arm $(colab usage | tr '\n' ' ')" >> results/cu_log.txt
colab sessions >> results/cu_log.txt
setsid nohup scripts/driver.sh scripts/jobs_colab.txt 1 results/driver_colab.log > /dev/null 2>&1 < /dev/null &
echo "driver_colab $!" >> results/pids.txt
setsid nohup scripts/driver.sh scripts/jobs_default_lean.txt 1 results/driver_default_lean.log > /dev/null 2>&1 < /dev/null &
echo "driver_lean $!" >> results/pids.txt
