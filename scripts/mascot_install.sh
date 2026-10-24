#!/usr/bin/env bash
# 把 Clawd Bot 裝進一支片：cp 正本到 <film>/mascot/。
# 為什麼要複製不能引用：core/render/serve.mjs 把片子目錄當掛載根，片子取不到目錄外的檔案（403）。
# 用法：bash scripts/mascot_install.sh films/<名稱>
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FILM="${1:?用法: bash scripts/mascot_install.sh films/<名稱>}"
[ -d "$FILM" ] || { echo "沒有這個片子目錄：$FILM"; exit 2; }
mkdir -p "$FILM/mascot"
cp "$ROOT/assets/mascot/clawd-bot-shot.mjs" "$FILM/mascot/"
cp "$ROOT/assets/mascot/clawd-bot/clawd-bot.svg" "$FILM/mascot/"
echo "裝好：$FILM/mascot/（clawd-bot-shot.mjs、clawd-bot.svg）"
echo "接法見 docs/MASCOT.md；正本改了要重跑這支腳本。"
