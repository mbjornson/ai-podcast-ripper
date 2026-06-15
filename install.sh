#!/usr/bin/env bash
#
# Podcast Ripper installer (macOS).
#
# Installs dependencies, sets up config, pulls the summarization model, and
# (optionally) schedules a daily automatic run via launchd — asking what time
# you want it to run and offering a matching system wake so a sleeping Mac
# still runs on time.
#
# Safe to re-run: existing config is left untouched and the LaunchAgent is
# reloaded in place.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LABEL="com.shapeandship.podcast-ripper"
TEMPLATE="$SCRIPT_DIR/$LABEL.plist.example"
PLIST_DEST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_PATH="$HOME/Library/Logs/podcast-ripper.log"

info() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!\033[0m  %s\n' "$*"; }
die()  { printf '\033[1;31mx\033[0m  %s\n' "$*" >&2; exit 1; }

# --- 0. Platform -----------------------------------------------------------
[[ "$(uname)" == "Darwin" ]] || die "This installer targets macOS (it uses launchd)."

# --- 1. Prerequisites ------------------------------------------------------
command -v python3 >/dev/null || die "python3 not found. Install Python 3.11+ and re-run."
PYTHON_BIN="$(python3 -c 'import sys; print(sys.executable)')"
info "Using Python: $PYTHON_BIN"

if command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null; then
  info "ffmpeg/ffprobe present."
elif command -v brew >/dev/null; then
  info "Installing ffmpeg via Homebrew..."
  brew install ffmpeg
else
  die "ffmpeg/ffprobe missing and Homebrew not found. Install ffmpeg, then re-run."
fi

# --- 2. Python dependencies ------------------------------------------------
info "Installing Python dependencies into $PYTHON_BIN ..."
"$PYTHON_BIN" -m pip install -r requirements.txt

# --- 3. Config -------------------------------------------------------------
if [[ -f config.yaml ]]; then
  info "config.yaml already exists — leaving it untouched."
else
  cp config.example.yaml config.yaml
  warn "Created config.yaml from the example — edit it to add your podcast feeds."
fi

read_setting() {  # read_setting <key> <fallback>
  "$PYTHON_BIN" -c "import yaml; print(yaml.safe_load(open('config.yaml'))['settings'].get('$1','$2'))" 2>/dev/null || echo "$2"
}

# --- 4. Models -------------------------------------------------------------
OLLAMA_MODEL="$(read_setting ollama_model gemma3)"
WHISPER_MODEL="$(read_setting whisper_model large-v3-turbo)"

if command -v ollama >/dev/null; then
  info "Pulling Ollama summarization model: $OLLAMA_MODEL"
  ollama pull "$OLLAMA_MODEL" || warn "Could not pull '$OLLAMA_MODEL'. Make sure Ollama is running, then: ollama pull $OLLAMA_MODEL"
else
  warn "Ollama not installed. Get it from https://ollama.com (or 'brew install ollama'), then: ollama pull $OLLAMA_MODEL"
fi
info "Faster-Whisper will download its model ('$WHISPER_MODEL') automatically on the first run."

# --- 5. Daily scheduling ---------------------------------------------------
read -rp "$(printf '\033[1;36m?\033[0m  Schedule a daily automatic run? [Y/n] ')" yn
if [[ "${yn:-Y}" =~ ^[Yy]?$ ]]; then
  while true; do
    read -rp "   Run time each day (24-hour HH:MM) [00:00]: " RUN_TIME
    RUN_TIME="${RUN_TIME:-00:00}"
    if [[ "$RUN_TIME" =~ ^([01][0-9]|2[0-3]):([0-5][0-9])$ ]]; then
      RUN_HOUR=$((10#${BASH_REMATCH[1]})); RUN_MINUTE=$((10#${BASH_REMATCH[2]}))
      break
    fi
    warn "Invalid time '$RUN_TIME' — use 24-hour HH:MM, e.g. 06:30."
  done

  mkdir -p "$HOME/Library/LaunchAgents"
  # Substitute the path placeholders; the schedule time is set structurally below.
  sed -e "s|__HOME__|$HOME|g" \
      -e "s|__PROJECT_DIR__|$SCRIPT_DIR|g" \
      -e "s|__PYTHON_BIN__|$PYTHON_BIN|g" \
      "$TEMPLATE" > "$PLIST_DEST"

  # Set StartCalendarInterval precisely via plistlib (sed can't tell Hour's 0
  # from Minute's 0).
  "$PYTHON_BIN" - "$PLIST_DEST" "$RUN_HOUR" "$RUN_MINUTE" <<'PY'
import sys, plistlib
path, hour, minute = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
with open(path, "rb") as f:
    data = plistlib.load(f)
data["StartCalendarInterval"] = {"Hour": hour, "Minute": minute}
with open(path, "wb") as f:
    plistlib.dump(data, f)
PY

  plutil -lint "$PLIST_DEST" >/dev/null || die "Generated plist failed validation: $PLIST_DEST"

  launchctl unload "$PLIST_DEST" 2>/dev/null || true
  launchctl load "$PLIST_DEST"
  info "$(printf 'Scheduled daily at %02d:%02d. Logs: %s' "$RUN_HOUR" "$RUN_MINUTE" "$LOG_PATH")"

  # Offer a system wake a few minutes early so a sleeping Mac runs on time.
  read -rp "$(printf '\033[1;36m?\033[0m  Also wake the Mac 5 min early so a sleeping machine runs on time? (needs sudo) [y/N] ')" wk
  if [[ "${wk:-N}" =~ ^[Yy]$ ]]; then
    total=$(( (RUN_HOUR * 60 + RUN_MINUTE - 5 + 1440) % 1440 ))
    WAKE_TIME="$(printf '%02d:%02d:00' $((total / 60)) $((total % 60)))"
    info "Scheduling daily wake at ${WAKE_TIME% *} (sudo password required)..."
    if sudo pmset repeat wakeorpoweron MTWRFSU "$WAKE_TIME"; then
      info "Wake scheduled. Verify with: pmset -g sched"
    else
      warn "pmset failed. Run manually: sudo pmset repeat wakeorpoweron MTWRFSU $WAKE_TIME"
    fi
  fi
else
  info "Skipping scheduling. To schedule later, re-run ./install.sh."
fi

# --- Done ------------------------------------------------------------------
info "Setup complete. Run a transcription now with:  $PYTHON_BIN rip.py"
