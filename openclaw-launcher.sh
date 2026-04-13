#!/bin/bash
# ============================================
# OpenClaw Connector — Auto-Restart Launcher
# ============================================
# Keeps the connector running. If it crashes, restarts automatically.
#
# Usage:
#   chmod +x openclaw-launcher.sh
#   ./openclaw-launcher.sh              # default port 61632
#   ./openclaw-launcher.sh 8000         # custom port
#   ./openclaw-launcher.sh --background # run in background (detached)
#
# To stop:
#   kill $(cat ~/.openclaw/launcher.pid)
#   OR press Ctrl+C if running in foreground

PORT="${1:-61632}"
BACKGROUND=false
RESTART_DELAY=3
MAX_RESTARTS=50
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check for --background flag
for arg in "$@"; do
  case "$arg" in
    --background|-bg) BACKGROUND=true ;;
    [0-9]*) PORT="$arg" ;;
  esac
done

# Ensure PID dir exists
mkdir -p ~/.openclaw

# Save PID
echo $$ > ~/.openclaw/launcher.pid

cleanup() {
  echo ""
  echo "🦞 Stopping OpenClaw Connector..."
  rm -f ~/.openclaw/launcher.pid
  # Kill the uvicorn process if running
  if [ -n "$UVICORN_PID" ] && kill -0 "$UVICORN_PID" 2>/dev/null; then
    kill "$UVICORN_PID" 2>/dev/null
    wait "$UVICORN_PID" 2>/dev/null
  fi
  echo "🦞 Stopped."
  exit 0
}
trap cleanup SIGINT SIGTERM

run_connector() {
  local restart_count=0

  echo "🦞 ═══════════════════════════════════════════════"
  echo "🦞  OpenClaw+ Connector Launcher"
  echo "🦞  Port: $PORT"
  echo "🦞  Dashboard: http://localhost:$PORT"
  echo "🦞  Auto-restart: ON (max $MAX_RESTARTS)"
  echo "🦞 ═══════════════════════════════════════════════"
  echo ""

  while [ "$restart_count" -lt "$MAX_RESTARTS" ]; do
    echo "🦞 Starting connector (attempt $((restart_count + 1)))..."

    cd "$SCRIPT_DIR"
    python3 -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" &
    UVICORN_PID=$!

    # Wait for the process to exit
    wait "$UVICORN_PID"
    EXIT_CODE=$?

    # Check if it was a clean shutdown (SIGTERM/SIGINT)
    if [ $EXIT_CODE -eq 0 ] || [ $EXIT_CODE -eq 130 ] || [ $EXIT_CODE -eq 143 ]; then
      echo "🦞 Connector stopped cleanly."
      break
    fi

    restart_count=$((restart_count + 1))
    echo ""
    echo "🦞 ⚠️  Connector crashed (exit code $EXIT_CODE). Restarting in ${RESTART_DELAY}s... ($restart_count/$MAX_RESTARTS)"
    sleep "$RESTART_DELAY"
  done

  if [ "$restart_count" -ge "$MAX_RESTARTS" ]; then
    echo "🦞 ❌ Max restarts reached ($MAX_RESTARTS). Giving up."
    exit 1
  fi
}

if [ "$BACKGROUND" = true ]; then
  LOG_FILE="$HOME/.openclaw/connector.log"
  echo "🦞 Starting in background. Logs: $LOG_FILE"
  echo "🦞 Dashboard: http://localhost:$PORT"
  echo "🦞 Stop with: kill \$(cat ~/.openclaw/launcher.pid)"
  run_connector >> "$LOG_FILE" 2>&1 &
  disown
  echo $! > ~/.openclaw/launcher.pid
  echo "🦞 Launcher PID: $(cat ~/.openclaw/launcher.pid)"
else
  run_connector
fi
