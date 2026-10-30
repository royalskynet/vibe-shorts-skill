# 做片第 2–5 步細節：人要寫的檔、反方稽核、目視自評

步驟總表與指令在 `SKILL.md`「做一支片」；環境沒裝過先跑 `setup.md`。

## 人要寫的檔

| 檔 | 內容 | 對應的門 |
|---|---|---|
| `TREATMENT.md` | 「爆款證據：」行、分鏡表（卡號／字幕／**動作**／衝擊事件）、「## 禁止清單」節 | 爆款證據、禁止清單、寫稿規則 |
| `narration.md` | 四段式旁白稿，見 `audio.md` | 旁白稿結構、台詞非照抄 |
| `SOURCES.md` | 稿中說法／原始數字／來源 URL 表格＋口徑說明（對象、年份、地點、可複選）＋刻意不用的數字及理由 | 人工，合規 |
| `meta/facts.md` | `FACTS` 每一值一行來源 | 數字都有來源 |
| `index.html` | 畫面與動作，見 `graphics.md`、`animation.md` | 多道 |
| `mix.py` | 音效對應，見 `audio.md` | — |
| `cast.json`（對談片） | Clawd 的台詞清單 | — |
| `pace.json`（可選） | 句間距、語速 | — |
| `meta/caption-{shorts,reels,threads}.txt` | 三份**內容互不相同**的說明文字 | 見 `deliver-publish.md` |

分鏡表「動作」欄寫能畫的動詞（蓋章、壓下、堆疊）；抽象詞（意義、象徵、科技、進步）會被擋。「衝擊事件」只能寫 `events.json` 裡存在的 type。

對談稿從 `refs/dialogue-corpus/` 的爆款原稿改編，**改編稿要使用者核過才建置**。

## 反方稽核

`scripts/devils.sh films/<片名>` 產 `audit/claims.md`、`audit/devils-advocate.md`（每爭點要有 URL＋摘錄，或標 `NO_EVIDENCE_BACKED_OBJECTION`）。

`audit/verdicts.md` 由主 session 逐爭點寫：engine 宣告、sha256 綁定現稿、每爭點 `VERDICT`（`PRO_WINS`／`CON_WINS`／`SPLIT`／`UNRESOLVED`）＋ `REASON`。稿或來源改過就重跑，sha 對不上門不過。

## 目視自評

`qa/review_log.md`：首行 `video_sha`（成片 sha256），七項各一行「- 項目：分數 — 理由」，每項 ≥ 8 才過。成片重渲就重看重打。

## 建置的失敗碼

`heavy` 閘擋併發；GPU 被卡死行程佔住時 `build.sh` exit 70。
