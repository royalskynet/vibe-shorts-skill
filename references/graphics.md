# 產圖：畫面怎麼來的

`index.html`（HTML＋Canvas／WebGL）→ headless Chromium 逐幀 `render(t)` 截 PNG → ffmpeg 合 `out/video.mp4` → 與 `out/mix.wav` 合軌成 `<片名>.mp4`。改畫面就是改 `index.html`。

## 渲染指令（`$LIB`，預設 `~/dev/lemo-opuscar`）

```bash
node $LIB/core/render/events.mjs . --size 1080x1920                       # window.EV → events.json（混音對時）
node $LIB/core/render/video.mjs  . --fps 30 --size 1080x1920 --workers 6  # 逐幀 → out/video.mp4；6 個 worker 各自冷啟動
bash $LIB/core/render/mux.sh out/video.mp4 out/mix.wav <片名>.mp4 30      # 合軌
node $LIB/core/render/readcheck.mjs . --size 1080x1920                    # 字幕閱讀時長（對談片只警告）
```

## index.html 的對外契約

渲染器只認這些全域變數，少一個就渲不出來：

```js
window.DUR    = 43.808;          // 片長（秒），通常讀 TL.dur
window.render = (t) => { ... };  // 畫第 t 秒，直接寫 canvas
window.READY  = true;            // 字型與資源載完才設 true
window.CUES   = [{t0, t1, text}];        // 字幕表，readcheck 用
window.TEXTS  = (t) => [{id, text, x0, y0, x1, y1, screen}];  // 該幀可見文字位置，textless_check 用
window.EV     = [{t, type, len?}];       // 音效事件，events.mjs 匯出
window.SHAKES = [t, ...];                // 可選：鏡頭震動時間點，要對得上 EV
```

## 資料檔

| 檔 | 產生者 | 內容 |
|---|---|---|
| `timeline.js` | `scripts/voice.py` 產生，**不手改** | `window.TL = {dur, lines:[{section,text,t0,t1,who?}]}`，驅動字幕與卡片切點 |
| `events.json` | `events.mjs` 從 `window.EV` 匯出 | `{dur, ev:[{t,type,len?}]}`，給 `mix.py` |
| `pace.json` | 手寫（可選） | `{"gap_line":1.0,"gap_section":1.3,"tempo":1.0}` |

`EV` 的 type 與對應音效見 `audio.md`；新增 type 要同步該片 `mix.py`，否則沒聲音。

## 視覺硬規格

- 畫布 **1080×1920**、**30 fps**。
- 左右各留 **60px**；主內容在 420px 以下（上面是 HUD／進度刻度）；字幕帶 **1860–1920px**。
- 字體：中文 `"PingFang TC"`，數字年份 `Menlo`。大標 190–250px 粗體、字幕 44–60px、HUD 標籤 24–40px。
- **第 0 幀就是封面縮圖**：大標在 `t=0` 已完整顯示，不靠淡入（`docs/WRITING.md` §6.3）。
- 片尾最後 0.6 秒淡黑。

色票（`BRAND.md` 正本）：

```
#F29172 亮部／標題      #D97757 主色（Clawd）   #BC5C3E 暗部
#252422 描邊            #201F1D 底色            #3A3632 內框
#F6B966 星芒／思考態    #68E399 LED 正常        #FF856D 腮紅   #FF8577 休眠／錯誤
```

## 片型

對談型（現行）：範本 `films/nerf/`，three.js WebGL＋2D 疊層，女主＋Clawd Bot，渲染約 8–10 分鐘。資料卡型 `films/dating-bill/`（Canvas 2D，約 3 分鐘）只因已發布保留。
