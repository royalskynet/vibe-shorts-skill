# 從空白做出一支片

環境沒裝過先跑 `setup.md`。指令都從 repo 根目錄 `~/dev/vibe-shorts-pipeline` 起算，`<片名>` 用 kebab-case。

## 0. 選題（先做，沒證據不准開工）

調 skill `viral-scout` 找對標爆款。先查 `refs/VIRAL-LEDGER.md`、`refs/BENCHMARKS.md`、`refs/BREAKDOWN.md`，命中就引用，不從頭抓。證據 append 回 `refs/VIRAL-LEDGER.md`。

需要：至少一支 **≥ 10 萬播放** 的同題爆款，附平台、播放數、連結。`precheck.py`「爆款證據」門機械檢查。

## 1. 建片目錄

```bash
cp -r films/nerf films/<片名>
cd films/<片名>
rm -rf out dist qa audit/*.log <舊片名>.mp4
mv index.html index.html   # 保留結構，內容重寫
```

**範本一律用 `films/nerf/`**（對談格式：女主＋Clawd Bot，three.js）。`films/dating-bill/` 是舊的資料卡格式，只因已發布而留著，不要拿來當模板。

`build.sh` 裡 `OUT=` 改成 `<片名>.mp4`。角色素材：`scripts/mascot_install.sh films/<片名>`。

片型標記寫 `rhythm-profile`（對談片寫 `dialogue`，地圖片 `map`，資料卡留空）—— 它決定節奏閘門與格線門用哪組基準。

## 2. 人要寫的檔

| 檔 | 內容 | 門 |
|---|---|---|
| `TREATMENT.md` | 「爆款證據：」行、分鏡表（卡號／字幕／**動作**／衝擊事件）、「## 禁止清單」節 | 爆款證據、禁止清單、寫稿規則 |
| `narration.md` | 四段式旁白稿，見 `audio.md` | 旁白稿結構、台詞非照抄 |
| `SOURCES.md` | 每個數字的一手出處＋口徑說明＋刻意不用的數字 | 人工，合規要求 |
| `meta/facts.md` | `index.html` 的 `FACTS` 每一值對應一行來源 | 數字都有來源 |
| `index.html` | 畫面與動作，見 `graphics.md`、`animation.md` | 多道 |
| `mix.py` | 音效對應，見 `audio.md` | — |
| `cast.json`（對談片） | Clawd 的台詞清單 | — |
| `pace.json`（可選） | 句間距、語速 | — |
| `meta/caption-{shorts,reels,threads}.txt` | 三份**內容互不相同**的說明文字 | 見 `deliver-publish.md` |

寫稿硬規則在 `docs/WRITING.md`，兩條最容易犯：

- **禁防衛性中立語言**（最高嚴重度）：不准出現「問法不同」「不能直接比較」「不代表全部」這類沒資訊的自我辯護句。限定範圍要寫進事實本身（年份、地點、對象）。
- **分鏡表「動作」欄要寫能畫的動詞**（蓋章、壓下、堆疊）。抽象詞（意義、象徵、科技、進步）會被擋。「衝擊事件」只能寫 `events.json` 裡存在的 type。
- **對談稿從爆款原稿改編，台詞不能照抄**：`refs/dialogue-corpus/` 的直譯句相似度 > 0.6 就擋。只借結構（節拍、三段加碼、回扣），台詞重寫。**改編稿要使用者核過才建置。**

數字一律集中在 `index.html` 頂端的 `FACTS` 物件，卡片引用 `${FACTS.KEY}`，不准直接寫數字 —— 不然改一處漏一處。

## 3. 反方稽核

```bash
scripts/devils.sh films/<片名>
```

產 `audit/claims.md`、`audit/devils-advocate.md`（每爭點要有 URL＋摘錄，或標 `NO_EVIDENCE_BACKED_OBJECTION`）。主 session 逐爭點寫 `audit/verdicts.md`：engine 宣告、sha256 綁定、每爭點 `VERDICT`（`PRO_WINS`／`CON_WINS`／`SPLIT`／`UNRESOLVED`）＋ `REASON`。

稿或來源改過要重跑 —— `verdicts.md` 綁的是當時的 sha，對不上門就不過。

## 4. 建置

```bash
cd films/<片名> && bash build.sh
```

`build.sh` 的順序（不要自己調）：旁白 → 字幕閱讀時長（警告）→ 事件表 → 混音 → **尋幀一致** → **藏字檢查** → 畫面 → 合軌 → 節奏閘門。檢查排在渲染之前，是為了在花 8–10 分鐘渲圖前先擋下來。

**一次只能跑一支**（`CLAUDE.md`）。兩個建置同時寫 `out/` 會壞片；`heavy` 閘會擋，GPU 被卡死行程佔住時 exit 70。

產出：`<片名>.mp4`、`timeline.js`、`out/{voice/,mix.wav,video.mp4,*-report.json}`。

## 5. 目視自評

```bash
scripts/qa_sheet.sh films/<片名>
```

看 `qa/sheet.jpg` 自己打分，寫 `qa/review_log.md`：首行 `video_sha`（成片 sha256），七項各一行「- 項目：分數 — 理由」，**每項 ≥ 8** 才過。成片重渲過就要重看重打，sha 對不上門不過。

## 6. 閘門

```bash
python3 scripts/precheck.py films/<片名>
```

全過（exit 0）才准發。各門與修法見 `gates.md`。

## 7. 匯出

```bash
scripts/deliver.sh films/<片名>/<片名>.mp4
```

## 8. 發布（要人點頭）

見 `deliver-publish.md`。

## 9. 收尾

更新 `PLAN.md` 該步狀態、同步 memory `state/vibe-shorts.md`、commit。發布數據回饋進 `refs/VIRAL-LEDGER.md`。

## 每步怎麼知道成功了

| 步 | 驗收 |
|---|---|
| 2 | `grep 爆款證據 TREATMENT.md`；`grep -c '^## ' narration.md` ≥ 4；末句有問號 |
| 3 | `devils.sh` exit 0；`verdicts.md` 每爭點有 VERDICT |
| 4 | `<片名>.mp4` size > 0；`out/narration-report.json` 有 `words` |
| 5 | `qa/review_log.md` 七項 ≥ 8 且 `video_sha` 對得上 |
| 6 | `python3 scripts/precheck.py films/<片名>; echo $?` → 0 |
| 7 | `dist/` 三檔都 > 0；時長與成片差 ≤ 0.2s |
| 8 | `meta/published.json` 有三平台連結 |
