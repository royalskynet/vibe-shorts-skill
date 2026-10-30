---
name: vibe-shorts
description: 營銷號短片流水線：建片、畫面、動畫、配音、閘門、三平台匯出、發布、看數據。說「營銷號」「做片」「下一支片」「vibe shorts」「接續 PLAN」，或要改這條流水線時用。找爆款證據用 viral-scout。
---

# vibe-shorts — 短片流水線

正本是私有 repo，未公開。技能包單獨 clone（`~/.claude/skills/vibe-shorts`）時自己就是可跑的根目錄：`scripts/`、`tests/`、範本片 `films/nerf/`、角色 `assets/mascot/`；渲染器與匯出工具是外部公開 repo（`references/setup.md`）。指令都從根目錄起算，`<片名>` 用 kebab-case。

全部程式生成：畫面是 `index.html` 的 `render(t)`，聲音是本機 Qwen3-TTS＋程式合成配樂；不用 AI 生圖、剪輯軟體、外部 TTS API。改片子＝改程式碼與稿子。

進度正本 `PLAN.md`、repo 規則 `CLAUDE.md`、已裁決不重議 `DECISIONS.md`、寫稿細則 `docs/WRITING.md`、品牌色票 `BRAND.md`、配音選型 `VOICE.md`（私有端，技能包不帶）。

## 硬規則

1. **爆款第一**：選題、鉤子、節奏、畫面先調 `viral-scout`，至少一支 ≥ 10 萬播放，寫進 `TREATMENT.md`「爆款證據：」行（連結＋播放數）並 append `refs/VIRAL-LEDGER.md`。沒這行 precheck 不過。題材不設限。
2. **源頭先對，閘門只驗收**：修在產生問題的地方（稿子、`index.html`、`build.sh`／`deliver.sh`）。閘門假設不符片型就分流（`rhythm-profile`），不扭曲片子；**新增或放寬任何閘門基準要使用者目視核准**。
3. **要人點頭**：發布到 YT／IG／Threads、刪已發貼文、對談改編稿開始建置、放寬閘門。其餘（建置、匯出、precheck、改本機檔）全自動。
4. **建置不併發**：`films/*/build.sh` 一次一支，兩支同寫 `out/` 會壞片。
5. **新片複製 `films/nerf/`**（深夜對談：女主＋Clawd Bot，three.js）。`films/dating-bill/` 是舊資料卡格式，不當模板。
6. **稿子禁防衛性中立語言**（最高嚴重度）：不寫「問法不同」「不能直接比較」「不代表全部」這類自我辯護句；限定範圍寫進事實本身（年份、地點、對象）。
7. **台詞不照抄**爆款原稿（相似度 > 0.6 擋），只借結構（節拍、三段加碼、回扣）。
8. **`render(t)` 只依賴 `t`**：不累積狀態、不讀 `Date.now()`、不發外部請求。所有姿態、鏡頭、轉場都是 `t` 的純函數（`references/animation.md`）。
9. **數字集中在 `index.html` 頂端 `FACTS`**，卡片用 `${FACTS.KEY}` 引用，每個 key 在 `meta/facts.md` 有來源。
10. **三個 Python 不互換**：配音／核稿用 `.venv/bin/python`；`precheck.py`、`rhythm_check.py`、`cdp.py` 用系統 `python3`；各片 `mix.py` 用 `LIB="$LIB" "$LIB/.venv/bin/python"`。
11. **憑證**：發布權杖值不進 repo、不進對話；公開網址用隨機 token，平台抓完立刻關 funnel（`references/deliver-publish.md`）。

## 做一支片

| 步 | 指令／動作 | 驗收 |
|---|---|---|
| 0 選題 | `viral-scout`，先查 `refs/` 帳本 | `TREATMENT.md` 有爆款證據行 |
| 1 建目錄 | `cp -r films/nerf films/<片名>`；清 `out dist qa audit/*.log 舊片.mp4`；`build.sh` 的 `OUT=` 改片名；`scripts/mascot_install.sh films/<片名>`；寫 `rhythm-profile`（對談 `dialogue`、地圖 `map`、資料卡留空） | — |
| 2 寫檔 | `TREATMENT.md`、`narration.md`、`SOURCES.md`、`meta/facts.md`、`index.html`、`mix.py`、`cast.json`、三份 caption（`references/film-from-zero.md`） | `grep -c '^## ' narration.md` ≥ 4；末句問號 |
| 2b 口語化 | 照 genie-humanizer 逐句改台灣口語，寫 `audit/humanize.md`（首行 `narration_sha:`，WRITING §7 第 10 條） | precheck「口語化（humanize）」OK |
| 3 反方稽核 | `scripts/devils.sh films/<片名>`，逐爭點寫 `audit/verdicts.md` | exit 0；每爭點有 VERDICT |
| 4 建置 | `cd films/<片名> && bash build.sh` | `<片名>.mp4` > 0；`out/narration-report.json` 有 `words` |
| 5 目視自評 | `scripts/qa_sheet.sh films/<片名>`，看 `qa/sheet.jpg` 寫 `qa/review_log.md` | 七項各 ≥ 8，`video_sha` 對得上 |
| 6 閘門 | `python3 scripts/precheck.py films/<片名>` | exit 0 才准發 |
| 7 匯出 | `scripts/deliver.sh films/<片名>/<片名>.mp4` | `dist/` 三檔 > 0，時長差 ≤ 0.2s |
| 8 發布（要人點頭） | `scripts/publish/`（`references/deliver-publish.md`） | `meta/published.json` 有三平台連結 |

`build.sh` 順序固定：旁白 → 字幕閱讀時長 → 事件表 → 混音 → 尋幀一致 → 藏字檢查 → 渲染（8–10 分鐘）→ 合軌 → 節奏閘。檢查排在渲染前，不要調順序。

## 收尾

改了程式就跑：

```bash
for t in tests/test_*.py;  do python3 "$t" || echo "FAIL $t"; done
for t in tests/test_*.mjs; do node    "$t" || echo "FAIL $t"; done
```

然後更新 `PLAN.md` 該步狀態、同步 memory `state/vibe-shorts.md`、commit。驗過的新命令或新規則改進本技能包對應段落（改原句，不另加）。

## 查表

- 新機接手、缺依賴、聲音範本、裝機驗收 → `references/setup.md`
- 第 2 步每個檔寫什麼、反方稽核與自評格式 → `references/film-from-zero.md`
- 改畫面、`index.html` 契約、渲染指令、視覺規格、色票、第 0 幀封面 → `references/graphics.md`
- 改動畫、吉祥物 `poseAt`、`seek_check`、節奏基準 → `references/animation.md`
- 改旁白、音色、多角色、混音、`voice.py` 失敗 → `references/audio.md`
- precheck 某道門不過、改閘門要跑哪些測試 → `references/gates.md`
- 匯出細節、發布指令、AI 揭露與授權、數據回饋 → `references/deliver-publish.md`
- 某段說法對應的實作檔與上游 repo（衝突以實作為準） → `references/sources.md`
