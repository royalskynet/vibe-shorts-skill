# 匯出與發布

## deliver.sh

```bash
scripts/deliver.sh films/<片名>/<片名>.mp4
# → films/<片名>/dist/<片名>-{shorts,reels,threads}.mp4
```

四步：

1. **色彩範圍**：渲染輸出是全範圍 `yuvj420p`，IG／Threads 預期標準範圍。偵測到就先轉 `scale=in_range=pc:out_range=tv,format=yuv420p` + `-color_range tv`（無損中繼）。
2. **三平台匯出**：`$FFMPEG_SKILL/export.py --preset {shorts|reels}`。**Threads 沒有專屬 preset，借 reels**（同樣 9:16，上限更寬）。reels preset 預設裁到 90 秒是舊規格 —— Meta 官方 Reels API 上限 15 分鐘、Threads 5 分鐘，所以帶 `--allow-long`（2026-10-20 的 `france` 片 125 秒差點被砍掉結尾）。
3. **元資料清理**：`video-scrub run` 刪來源身份字串。
4. **音訊與容器**：
   - shorts 直接沿用 clean 檔的音軌。
   - reels／threads 從 `out/mix.wav` **只重編一次** AAC 128k / 48kHz，套 `loudnorm=I=-14:TP=-2:LRA=11`（避免 AAC 轉轉造成峰值失控）。
   - `-use_editlist 0`（Meta 吃不下 edit list）、`-movflags +faststart+negative_cts_offsets`。

驗證：交付檔不准比成片短（preset 默默裁掉就會少結尾），時長差 ≤ 0.2s，影音 `start_time` 都是 0，搜不到 `elst` 原子，最後跑 `$FFMPEG_SKILL/check.py --platform`。

## 發布

```bash
python3 scripts/publish/public_path.py films/<片名>   # 產隨機 token，先做
python3 scripts/publish/meta_publish.py films/<片名> --yes   # IG Reels + Threads
python3 scripts/publish/yt_upload.py   films/<片名> --yes   # YouTube Shorts
```

發完把平台連結與時間寫進 `meta/published.json`。設定與權杖見 `docs/PUBLISH-SETUP.md`；YT OAuth 在 Testing 狀態 7 天到期，`scripts/publish/tokens.py` 報到期日。

公開網址衛生（三條硬規則）：路徑用 16+ 位十六進位隨機 token，不用片名，每次發布換新；只開那一支 mp4，不暴露資料夾；平台抓完檔立刻關掉 funnel 伺服器。

## 要人點頭的

| 動作 | 為什麼 |
|---|---|
| 發布到 YT／IG／Threads | 不可收回，外人會看到 |
| 刪已發的平台貼文 | IG 貼文 API 刪不掉，要走網頁手動（`docs/HANDOFF-threads-delete.md`） |
| 改編稿開始建置 | 對談稿要使用者核過（2026-10-18 定） |
| 放寬任何閘門基準 | 要目視核准 |

建置、匯出、precheck、改本機檔都全自動，不用問。

## 合規

AI 揭露（`docs/COMPLIANCE.md` 正本）：

- YouTube「是否包含經改造或合成的寫實內容」→ **否**（畫面是網點排版，非寫實）。
- IG／Threads 說明文字要有：**畫面由程式即時渲染，旁白為合成語音（非真人錄製，亦未複製任何人的聲音）。配樂為本片自行生成。** precheck 檢查「合成語音」與「程式」兩個詞。

三份說明文字各要有：AI 揭露句、結尾提問、來源欄，且**內容互不相同**。

授權：配樂程式自生成；旁白是 VoiceDesign 合成音色，不對應真人；TTS 模型 Apache-2.0；字體走系統點陣化不再散布；**衛星底圖只有 EOX s2cloudless 2016 版可商用（CC BY 4.0）**，出處要寫進 `SOURCES.md` 與說明欄。

`SOURCES.md` 要有：稿中說法 / 原始數字 / 來源含 URL 的表格，加上口徑說明（調查對象、年份、地點、可複選）與「刻意不用的數字及理由」。範本 `films/dating-bill/SOURCES.md`。

## 數據回饋

`scripts/publish/stats.py` 拉成效、`scripts/publish/postmortem_refresh.py` 補事後數據，結果進 `refs/VIRAL-LEDGER.md` 與 `refs/postmortem.md`，餵下一支的選題。
