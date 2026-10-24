# 閘門：precheck.py 與各段檢查

```bash
python3 scripts/precheck.py films/<片名>      # exit 0 = 全過
```

零 token，全機械判定。`scripts/precheck.py` 是**實作正本**，下表是導覽與修法；閾值以檔案頂端常數為準。

## 最高原則：源頭先對，閘門只驗收

（使用者 2026-10-20 定）問題修在**產生它的地方** —— 寫稿、`index.html`、`build.sh`／`deliver.sh`，不是靠閘門擋下再退回重做。

閘門的假設不符片型就**改閘門**（用 `rhythm-profile` 分流），不要扭曲片子去過門。但 **閘門基準改動要使用者目視核准**（`rhythm_check.py` 的 map 基準就是這樣放寬的），不准自己放寬。

## 門一覽

**交付與封面**（三平台各驗一次）

| 門 | 要什麼 | 不過怎麼修 |
|---|---|---|
| 成片比頁面新 | `index.html` 改過要重渲 | 重跑 `build.sh` |
| 交付檔 | `dist/<片名>-{shorts,reels,threads}.mp4` 存在且比成片新 | 重跑 `deliver.sh` |
| 封面幀亮度 | 第 0 幀平均亮度 ≥ `COVER_LUMA_MIN = 24`（0–255，limited range 全黑是 16） | 片頭不要從黑淡入 |
| 封面有字 | 第 0 幀 OCR 到 ≥ `COVER_TEXT_MIN = 2` 個中文字或數字，字高 ≥ 畫面 `COVER_TEXT_H = 4%` | 第一卡大標改成第 0 幀就完整顯示，不靠淡入 |
| 元資料 | `video-scrub verify` 過（來源身份字串沒漏進輸出） | 重跑 `deliver.sh` |

**說明文字**

| 門 | 要什麼 |
|---|---|
| 說明文字存在 | `meta/caption-{shorts,reels,threads}.txt` 三份都有 |
| 三份互不相同 | 三份 sha256 全不同（複製貼上會被平台壓低觸及） |
| 結尾提問 | 每份以問號收尾 |
| AI 揭露 | 每份含「合成語音」與「程式」（`docs/COMPLIANCE.md` 的標準句） |
| 列出來源 | 每份有以「來源」開頭的行 |
| 公開路徑是隨機 token | `meta/public-path.txt` 是 16+ 位十六進位、不含片名 → 跑 `scripts/publish/public_path.py` |

**內容**

| 門 | 閾值 | 修法 |
|---|---|---|
| 爆款證據 | `TREATMENT.md`「爆款證據：」行有連結＋播放數，至少一筆 ≥ `VIRAL_MIN = 100,000` | 跑 `viral-scout`，寫進 `TREATMENT.md` 與 `refs/VIRAL-LEDGER.md` |
| 禁止清單 | `TREATMENT.md` 有「## 禁止清單」節，至少一條 | 寫這支片禁用的畫面寫法 |
| 寫稿規則 | 分鏡表每卡「動作」欄非空且是能畫的動詞（抽象詞擋）；「衝擊事件」type 要在 `events.json` 裡 | 改分鏡表 |
| 旁白稿結構 | 鉤子／轉折／落點／提問四段齊＋順序對；鉤子首句 ≤ `HOOK_MAX_CHARS = 25` 字且含「你」或問號；提問段末為問句 | 改 `narration.md` |
| 台詞非照抄（僅 `dialogue`） | 與 `refs/dialogue-corpus/originals-zh.md` 直譯句相似度 ≤ `COPY_SIM_MAX = 0.6`；< `COPY_MIN_CHARS = 5` 字的句子與圈內梗白名單豁免 | 重寫台詞，只借結構 |
| 數字都有來源 | `index.html` 的 `FACTS` 每個 key 在 `meta/facts.md` 有來源行；卡片裡 3 位數以上的數字都走 `${FACTS.KEY}` | 補 `facts.md`；卡片改引用 FACTS。對談片稿中沒有 3 位數以上數字會自動豁免 |
| 反方稽核 | `audit/devils-advocate.md` 每爭點有 URL＋摘錄或 `NO_EVIDENCE_BACKED_OBJECTION`；`audit/verdicts.md` 有 engine 宣告、sha256 對得上現稿、每爭點 VERDICT＋REASON | 跑 `scripts/devils.sh`，逐爭點填 `verdicts.md` |
| 目視自評 | `qa/review_log.md` 首行 `video_sha` 等於成片 sha256，七項各 ≥ `REVIEW_MIN = 8` | `qa_sheet.sh` 看拼圖重打分 |

**聲畫**

| 門 | 閾值 | 修法 |
|---|---|---|
| 旁白進成片 | 成片聽寫相似度 ≥ `ASR_SIM_MIN = 0.85`；第一個字 ≤ `LEAD_SILENCE_MAX = 0.5s`；結尾提問在片尾 `QUESTION_TAIL_S = 15s` 內且相似度 ≥ `QUESTION_SIM_MIN = 0.7` | 確認 `mix.py` 把旁白混進去了、重渲重合軌 |
| 鏡頭格線 | 無配音時鏡長中位數貼卡片格線（差 < 10%）；有配音時每個切點落在句界 ±0.3s。地圖格式豁免 | 改卡片數／運鏡，或讓 `timeline.js` 切點貼句界 |
| 節奏閘門 | `rhythm_check.py`，基準按 `rhythm-profile` 分流，見 `animation.md` | 加亮度變化、降靜止比例 |
| 尋幀一致 | `seek_check.mjs`：交界幀冷啟動＝接續、無外部請求、`SHAKES` 對得上 `EV` | 見 `animation.md`，把狀態從 `render(t)` 拔掉 |
| 藏字檢查 | `textless_check.mjs`：卡片把字藏掉後不能只剩外框 | 卡片加背景動畫或非字幕元素；真的不適用可寫 `meta/textless-waive.txt` 豁免 |

## 改了閘門要跑的測試

```bash
for t in tests/test_*.py;  do python3 "$t" || echo "FAIL $t"; done
for t in tests/test_*.mjs; do node    "$t" || echo "FAIL $t"; done
```

對應關係：`precheck.py` → `test_precheck_copy.py`、`test_precheck_cover.py`、`test_precheck_review.py`、`test_story_gates.py`、`test_storyboard_rows.py`；`rhythm_check.py` → `test_rhythm_profile.py`；`seek_check.mjs` → `test_seek_check.py`；`textless_check.mjs` → `test_textless_check.py`；`clawd-bot-shot.mjs` → `test_mascot_pose.mjs`、`test_mascot_sync.py`；`devils.sh` → `test_devils_gate.py`；`voice.py` → `test_voice.py`、`test_voice_reusable.py`；發布腳本 → `test_meta_publish.py`、`test_social.py`、`test_threads_post.py`、`test_yt_upload.py`、`test_yt_channel_guard.py`、`test_tokens.py`、`test_stats.py`、`test_funnel.py`。

改到閘門或發布腳本，對應測試要能在邏輯改錯時失敗。負向斷言在 `set -e` 下用 `if cmd; then exit 1; fi`，不要用 `!`。
