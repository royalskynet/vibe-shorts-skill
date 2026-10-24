#!/usr/bin/env bash
# 旁白稿定稿前的反方稽核：沿用 /research 第三輪（devil's advocate）的引擎與協定，不另造一套。
# 用法：scripts/devils.sh films/<片>
#
# 把 narration.md＋SOURCES.md 合成 audit/claims.md 當「報告」，交給 research skill 的 devils_advocate.sh
# （codex → opencode，第二模型獨立上下文、可上網找反證，每條反證要 URL＋摘錄）。證據包寫到 audit/devils-advocate.md。
# exit 3＝第二模型都不可用：主 session 照 research 的 round3-devils-advocate.md「派遣 prompt 模板」派一次 subagent，
#   報告路徑填 audit/claims.md、輸出填 audit/devils-advocate.md。
# 之後主 session 逐爭點裁決寫 audit/verdicts.md（格式見 docs/WRITING.md §4），precheck「反方稽核」門判它。
set -euo pipefail
[ $# -eq 1 ] || { sed -n 2,10p "$0"; exit 2; }
FILM="$(cd "$1" && pwd)"
DA="$(ls ~/.claude/skills/synced/*/research/scripts/devils_advocate.sh ~/.claude/skills/research/scripts/devils_advocate.sh 2>/dev/null | head -1 || true)"
[ -n "$DA" ] || { echo "找不到 research skill 的 devils_advocate.sh" >&2; exit 2; }
[ -f "$FILM/narration.md" ] || { echo "缺 $FILM/narration.md" >&2; exit 2; }
mkdir -p "$FILM/audit"
{
  echo "# $(basename "$FILM") 旁白稿與數據來源（待稽核）"
  echo
  echo "核心結論＝旁白稿逐句陳述的事實。下方「旁白稿」是要對外發布的文字，「數據來源」是作者自述的出處與算法。"
  echo
  echo "## 旁白稿"
  sed 's/^## /### /' "$FILM/narration.md"
  echo
  echo "## 數據來源"
  if [ -f "$FILM/SOURCES.md" ]; then sed 's/^#/##/' "$FILM/SOURCES.md"; else echo "（無 SOURCES.md）"; fi
} > "$FILM/audit/claims.md"
echo "PROTO=$(cd "$(dirname "$DA")/../references" && pwd)/round3-devils-advocate.md"
# </dev/null：codex exec 在 stdin 沒關時會卡在 "Reading additional input from stdin..." 直到逾時
exec "$DA" "$FILM/audit/claims.md" "$FILM/audit/devils-advocate.md" </dev/null
