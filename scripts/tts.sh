#!/usr/bin/env bash
# 用鎖定的 D 音色念一段稿。用法：scripts/tts.sh <稿檔> [輸出前綴]
# 需要 .venv（見 VOICE.md「復現方式」）。
set -euo pipefail
# 全機重活閘（agent-tools/bin/heavy）：一次只跑一個重活、free 夠才開跑；GPU 被卡死行程佔住時 exit 70（10-14 事故）
[ -n "${HEAVY_HELD:-}" ] || [ ! -x "$HOME/.local/bin/heavy" ] || exec "$HOME/.local/bin/heavy" -- bash "$0" "$@"
cd "$(dirname "$0")/.."

SCRIPT_FILE=${1:?用法: scripts/tts.sh <稿檔> [輸出前綴]}
PREFIX=${2:-take-$(date +%H%M%S)}
REF=assets/voice/d24k.wav
REF_TEXT=$(tr -d '\n' < assets/voice/script.txt)

mkdir -p out
.venv/bin/mlx_audio.tts.generate \
  --model mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16 \
  --text "$(tr -d '\n' < "$SCRIPT_FILE")" \
  --lang_code Chinese \
  --ref_audio "$REF" --ref_text "$REF_TEXT" \
  --output_path ./out --file_prefix "$PREFIX" --join_audio

# ponytail: 只報長度，沒有核稿。要防吃字就接 whisper 比對逐字稿。
ffprobe -v error -show_entries format=duration -of csv=p=0 "out/$PREFIX.wav"
