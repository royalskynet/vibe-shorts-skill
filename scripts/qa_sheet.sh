#!/usr/bin/env bash
# 成片目視自評的素材：qa/sheet.jpg（全尺寸拼圖）、qa/sheet-360.jpg（手機寬度）、qa/cuts.json（切點）。
# 用法：scripts/qa_sheet.sh films/<片>
# 看完照 docs/WRITING.md §6 寫 qa/review_log.md，precheck「目視自評」門會驗。
set -euo pipefail
film="${1:?用法：scripts/qa_sheet.sh films/<片>}"
name="$(basename "$film")"
master="$film/$name.mp4"
[ -f "$master" ] || { echo "找不到成片 $master" >&2; exit 1; }
mkdir -p "$film/qa"
python3 "$(dirname "$0")/ref_analyze.py" "$master" --out "$film/qa/final" --cells 20
mv "$film/qa/final-sheet.jpg" "$film/qa/sheet.jpg"
mv "$film/qa/final-sheet-360.jpg" "$film/qa/sheet-360.jpg"
mv "$film/qa/final-info.json" "$film/qa/cuts.json"
echo "video_sha: $(shasum -a 256 "$master" | cut -d' ' -f1)"
