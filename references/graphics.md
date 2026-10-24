# 產圖：畫面怎麼來的

**全部程式生成，沒有一張 AI 生圖，也沒有 Figma／PS。** 畫面是 HTML + Canvas／WebGL，用 headless Chromium 一幀一幀截圖，再 ffmpeg 合成。要改畫面就是改 `index.html`。

## 渲染鏈

```
index.html  ──(Playwright 逐幀 render(t))──>  PNG 序列  ──(ffmpeg)──>  out/video.mp4
                                                              + out/mix.wav ──> <片名>.mp4
```

渲染器不在本 repo，在 `$LIB`（預設 `~/dev/lemo-opuscar`）：

| 指令 | 作用 |
|---|---|
| `node $LIB/core/render/events.mjs . --size 1080x1920` | 從 `window.EV` 匯出 `events.json`（給混音對時） |
| `node $LIB/core/render/video.mjs . --fps 30 --size 1080x1920 --workers 6` | 逐幀截圖 → `out/video.mp4` |
| `bash $LIB/core/render/mux.sh out/video.mp4 out/mix.wav <片名>.mp4 30` | 合軌成片 |
| `node $LIB/core/render/readcheck.mjs . --size 1080x1920` | 字幕閱讀時長（對談片只警告） |

`--workers 6` 開 6 個 worker 各自從不同幀冷啟動 —— 這是 `render(t)` 必須純函數的原因，見 `animation.md`。

## index.html 的對外契約

渲染器只認這幾個全域變數。少一個就渲不出來。

```js
window.DUR    = 43.808;          // 片長（秒），通常讀 TL.dur
window.render = (t) => { ... };  // 畫第 t 秒，直接寫 canvas，無回傳
window.READY  = true;            // 字型與資源載完才設 true，渲染器等這個
window.CUES   = [{t0, t1, text}];        // 字幕表，readcheck 用
window.TEXTS  = (t) => [{id, text, x0, y0, x1, y1, screen}];  // 該幀所有可見文字的位置，textless_check 用
window.EV     = [{t, type, len?}];       // 音效事件，events.mjs 匯出
window.SHAKES = [t, ...];                // 可選：鏡頭震動時間點，要對得上 EV
```

`render(t)` 只准依賴 `t`。不要在裡面累積狀態、不要讀 `Date.now()`、不要發外部網路請求（`seek_check.mjs` 會擋非 localhost 的 request）。

## 三個資料檔誰產生

| 檔 | 產生者 | 內容 |
|---|---|---|
| `timeline.js` | `scripts/voice.py` 自動產生，**不要手改** | `window.TL = {dur, lines:[{section,text,t0,t1,who?}]}`，驅動字幕與卡片切點 |
| `events.json` | `$LIB/core/render/events.mjs` 從 `window.EV` 匯出 | `{dur, ev:[{t,type,len?}]}`，給 `mix.py` 配音效 |
| `pace.json` | 手寫（可選） | `{"gap_line":1.0,"gap_section":1.3,"tempo":1.0}`，調句間距與語速 |

事件 `type` 用過的有：`bed`（整片配樂床）、`pop`、`stamp`、`turn`、`whoosh`、`swish`、`ticks`、`bell`、`blip`、`chime`、`cut`、`click`。新增 type 要同步改該片 `mix.py`，否則沒聲音。

## 視覺硬規格

- 畫布 **1080×1920**（9:16），fps **30**。三平台都吃這組。
- 左右各留 **60px**；頂部 420px 以下才放主內容（上面是 HUD／進度刻度）；字幕帶在 **1860–1920px**。
- 字體：中文 `"PingFang TC"`，數字年份用 `Menlo`。大標 190–250px 粗體、字幕 44–60px、HUD 標籤 24–40px。
- **第 0 幀就是封面縮圖**（IG／Threads／YT 都抓它）：大標必須在 `t=0` 已完整顯示，不能靠動畫淡入。`docs/WRITING.md` §6.3 是正本。
- 片尾最後 0.6 秒淡黑，避免跳接。

色票（`BRAND.md` 正本，全片統一）：

```
#F29172 亮部／標題      #D97757 主色（Clawd）   #BC5C3E 暗部
#252422 描邊            #201F1D 底色            #3A3632 內框
#F6B966 星芒／思考態    #68E399 LED 正常        #FF856D 腮紅   #FF8577 休眠／錯誤
```

## 兩種片型

| | 資料卡型 | 對談型（**現行格式**） |
|---|---|---|
| 範本 | `films/dating-bill/` | `films/nerf/` |
| 引擎 | Canvas 2D | three.js WebGL ＋ 2D 疊層 |
| 角色 | 無 | 女主 ＋ Clawd Bot |
| 渲染耗時 | 約 3 分鐘 | 約 8–10 分鐘 |

**新片一律複製 `films/nerf/`。** 對談格式是對標爆款定的（`BRAND.md`「吉祥物與視覺風格」），`dating-bill` 只因已發布而保留，不要當模板。
