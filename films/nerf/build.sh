#!/usr/bin/env bash
# 從 narration.md 與 index.html 做出成片。照順序跑，不併發（見 flt-11days 的教訓：兩個建置同時寫 out/ 會壞片）。
set -euo pipefail
# 全機重活閘（agent-tools/bin/heavy）：一次只跑一個重活、free 夠才開跑；GPU 被卡死行程佔住時 exit 70（10-14 事故）
[ -n "${HEAVY_HELD:-}" ] || [ ! -x "$HOME/.local/bin/heavy" ] || exec "$HOME/.local/bin/heavy" -- bash "$0" "$@"
cd "$(dirname "$0")"
LIB="${LIB:-$HOME/dev/lemo-opuscar}"
FPS=30
OUT=nerf.mp4
ROOT=../..

step() { printf '\n== %s ==\n' "$1"; }
t0=$(date +%s)


step "旁白"
# 稿沒改的句子不重念；核稿不過 exit 1，整個建置停下
"$ROOT/.venv/bin/python" "$ROOT/scripts/voice.py" .

step "字幕閱讀時長"
# 對談片一句一鏡、字幕跟著口白（參考爆款同節奏），卡片片的閱讀時長基準全句不過；基準是否放寬等使用者審片後裁決，這裡只警告
node "$LIB/core/render/readcheck.mjs" . --size 1080x1920 | grep -c "^BAD" | xargs -I{} echo "閱讀時長：{} 句短於卡片基準（只警告）" || true

step "事件表"
node "$LIB/core/render/events.mjs" . --size 1080x1920

step "混音"
LIB="$LIB" "$LIB/.venv/bin/python" mix.py

step "尋幀一致"
LIB="$LIB" node "$ROOT/scripts/seek_check.mjs" . --fps "$FPS" --workers 6 --size 1080x1920

step "藏字檢查"
LIB="$LIB" node "$ROOT/scripts/textless_check.mjs" . --size 1080x1920 --stills || echo "藏字檢查沒過，precheck 會擋；看 out/textless/"

step "畫面"
rm -f out/video.mp4.lock
node "$LIB/core/render/video.mjs" . --fps "$FPS" --size 1080x1920 --workers 6

step "合軌"
bash "$LIB/core/render/mux.sh" out/video.mp4 out/mix.wav "$OUT" "$FPS"

step "節奏閘門"
python3 "$ROOT/scripts/rhythm_check.py" "$OUT"

printf '\n完成 %s  總耗時 %ds\n' "$OUT" "$(( $(date +%s) - t0 ))"
