#!/bin/bash
# Open ONE ssh connection to the Colab VM (Colab allows only one `colab ssh` per runtime) as a ControlMaster,
# forwarding sandbox 127.0.0.1:18434 -> VM 127.0.0.1:11434 (Ollama). Other commands reuse it with: ssh -S $CP x CMD
# The key lives in ../.local_ssh/ (gitignored, deleted at the end).
D=$(cd "$(dirname "$0")/.." && pwd); K=$D/.local_ssh/id_ed25519; CP=$D/.local_ssh/cm.sock
exec ssh -i $K -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ServerAliveInterval=15 \
  -o ExitOnForwardFailure=yes -o ControlMaster=yes -o ControlPath=$CP \
  -o "ProxyCommand=colab ssh --proxy-mode -s codex-033 -i $K" -N -L 127.0.0.1:18434:127.0.0.1:11434 root@codex-033
