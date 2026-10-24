#!/usr/bin/env bash
# 9:16 SVG → PNG 定格，不經 chromium／GPU（GPU 卡死時也能出樣張，見 fixindex 10570）。
# qlmanage 只出正方縮圖，所以先包進 1920×1920 正方畫布置中，再裁回 1080×1920。
# 用法：bash preview.sh night.svg   → night.png
set -euo pipefail
SRC="${1:?用法: bash preview.sh <9:16 的 svg>}"
DIR="$(cd "$(dirname "$SRC")" && pwd)"; BASE="$(basename "$SRC" .svg)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
printf '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="-420 0 1920 1920" width="1920" height="1920"><rect x="-420" width="1920" height="1920" fill="#000"/>%s</svg>' \
  "$(sed -e '1s/<svg[^>]*>//' -e '$s#</svg>##' "$SRC" | sed '1{/^<?xml/d;}')" > "$TMP/sq.svg"
# 外層 <svg> 已剝掉，內容直接落在 0..1080 的座標上
qlmanage -t -s 1920 -o "$TMP" "$TMP/sq.svg" >/dev/null 2>&1
[ -f "$TMP/sq.svg.png" ] || { echo "qlmanage 沒產出縮圖"; exit 1; }
magick "$TMP/sq.svg.png" -crop 1080x1920+420+0 +repage "$DIR/$BASE.png"
echo "寫出 $DIR/$BASE.png"
