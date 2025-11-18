#!/usr/bin/env bash
# start_llama3_local.sh
# Simple helper to run a local Llama 3 server with an OpenAI-compatible API.

set -e

# ----- CONFIG SECTION -----
# Adjust these paths/values to match your setup.

# Project root (directory where this script lives)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Python virtualenv (if you have one, e.g. venv/, .venv/, etc.)
VENV_PATH="$PROJECT_ROOT/venv"    # change if your venv is named differently

# Path to your GGUF model
MODEL_PATH="$PROJECT_ROOT/models/Meta-Llama-3-8B-Instruct-Q3_K_M.gguf"

# Server port + host
HOST="127.0.0.1"
PORT=8001

# Context window and threads
N_CTX=4096
# Use Mac CPU core count if available, else default to 8
N_THREADS="$(sysctl -n hw.logicalcpu 2>/dev/null || echo 8)"

# ----- END CONFIG -----


echo "=== Prompt Builder Jam: Llama 3 local server ==="
echo "Project root : $PROJECT_ROOT"
echo "Model path   : $MODEL_PATH"
echo "Host:Port    : $HOST:$PORT"
echo "n_ctx        : $N_CTX"
echo "n_threads    : $N_THREADS"
echo

# Activate virtualenv if it exists
if [ -d "$VENV_PATH" ]; then
  echo "Activating virtualenv at $VENV_PATH"
  # shellcheck disable=SC1090
  source "$VENV_PATH/bin/activate"
else
  echo "No virtualenv found at $VENV_PATH (continuing anyway)"
fi

# Check llama_cpp is installed
if ! python -c "import llama_cpp" >/dev/null 2>&1; then
  echo "ERROR: llama_cpp Python package not found."
  echo "Run:  pip install llama-cpp-python"
  exit 1
fi

# Check model exists
if [ ! -f "$MODEL_PATH" ]; then
  echo "ERROR: Model file not found at:"
  echo "  $MODEL_PATH"
  exit 1
fi

echo "Starting llama_cpp.server..."
echo "You should be able to hit: http://$HOST:$PORT/v1/chat/completions"
echo "Press Ctrl+C to stop."
echo

python -m llama_cpp.server \
  --model "$MODEL_PATH" \
  --host "$HOST" \
  --port "$PORT" \
  --n_ctx "$N_CTX" \
  --n_threads "$N_THREADS"

