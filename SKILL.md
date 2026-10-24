---
name: vibe-shorts
description: 營銷號短片流水線：從零建片、產圖（HTML/Canvas 程式渲染）、產動畫（無狀態 poseAt）、做聲音（本機 Qwen3-TTS 配音與混音）、閘門、三平台匯出、發布、看數據。說「營銷號」「做片」「下一支片」「vibe shorts」「接續 PLAN」，或要改這條流水線的畫面、動畫、配音、閘門時用。找爆款證據另用 viral-scout。
---

# vibe-shorts — 短片流水線

專案：`/Users/you/dev/vibe-shorts-pipeline`（私有正本，未公開）。

這份技能包自帶全部做片能力，不必再去翻實作檔。**按需讀 `references/`，不要一次全讀。**

## 這條流水線是什麼

對標爆款 → 寫稿 → 本機 TTS 配音 → 程式合成混音 → HTML/Canvas 逐幀渲染 → 機械閘門 → 三平台匯出 → 發布 → 數據回饋。

**全部程式生成：沒有 AI 生圖、沒有剪輯軟體、沒有真人配音、沒有外部 TTS API。** 畫面是 `index.html` 的 `render(t)`，聲音是本機 Qwen3-TTS＋正弦波合成配樂，改片子就是改程式碼與稿子。

## 先分流

| 你要做的 | 讀這個 |
|---|---|
| 接續進度、現在該做第幾步 | `PLAN.md`（進度正本）→ `CLAUDE.md`（repo 規則） |
| 新機接手、環境裝不起來、缺依賴 | `references/setup.md` |
| 從零做一支新片 | `references/film-from-zero.md` |
| 改畫面、卡片、字幕、色票、第 0 幀 | `references/graphics.md` |
| 改動畫、吉祥物、鏡頭、節奏不過 | `references/animation.md` |
| 改旁白、換音色、多角色、混音、音量 | `references/audio.md` |
| precheck 某道門不過 | `references/gates.md` |
| 匯出、發布、合規、授權 | `references/deliver-publish.md` |
| 選題、鉤子、節奏、畫面要依據 | skill `viral-scout` |

決議理由查 `DECISIONS.md`（已裁決的不重議）；寫稿細則 `docs/WRITING.md`；品牌與視覺 `BRAND.md`；配音選型 `VOICE.md`。

## 不准違反的

1. **爆款第一**。選題、鉤子、節奏、畫面一律先調 `viral-scout` 拿證據，至少一支 ≥ 10 萬播放，寫進該片 `TREATMENT.md` 的「爆款證據：」行（連結＋播放數），再 append 到 `refs/VIRAL-LEDGER.md`。沒這行 `precheck.py` 不給過。題材不設限。
2. **源頭先對，閘門只驗收**。問題修在產生它的地方（稿子、`index.html`、`build.sh`／`deliver.sh`），不靠閘門擋下再退回重做。**放寬任何閘門基準要使用者目視核准。**
3. **對外發布、刪平台貼文前停下問使用者**；對談改編稿要使用者核過才建置。其餘（建置、匯出、precheck、改本機檔）全自動，不用問。
4. **建置不併發**。`films/*/build.sh` 一次只跑一支，兩個同時寫 `out/` 會壞片。
5. **新片格式是深夜對談（女主＋Clawd Bot）**，範本 `films/nerf/`。`films/dating-bill/` 是舊的資料卡格式，不要當模板。
6. **稿子禁防衛性中立語言**（最高嚴重度）：不准出現「問法不同」「不能直接比較」「不代表全部」這類沒資訊的自我辯護句。限定範圍寫進事實本身。
7. **對談台詞不能照抄**爆款原稿直譯（相似度 > 0.6 擋），只借結構。
8. **兩個 Python 不可互換**：配音用 `.venv/bin/python`，`precheck.py` 與 `cdp.py` 用系統 `python3`，`mix.py` 用 `$LIB/.venv/bin/python`。

## 最短路徑

```bash
cd ~/dev/vibe-shorts-pipeline
cd films/<片名> && bash build.sh                 # 旁白→混音→檢查→渲染→合軌→節奏閘
cd ../.. && scripts/qa_sheet.sh films/<片名>      # 看 qa/sheet.jpg，寫 qa/review_log.md
python3 scripts/precheck.py films/<片名>          # exit 0 才准發
scripts/deliver.sh films/<片名>/<片名>.mp4        # → dist/ 三平台
# 發布要人點頭：scripts/publish/
```

## 收尾

改完程式要跑：

```bash
for t in tests/test_*.py;  do python3 "$t" || echo "FAIL $t"; done
for t in tests/test_*.mjs; do node    "$t" || echo "FAIL $t"; done
```

然後更新 `PLAN.md` 該步狀態、同步 memory `state/vibe-shorts.md`、commit。驗過的新命令或新教訓補回本技能包的 `references/`。
