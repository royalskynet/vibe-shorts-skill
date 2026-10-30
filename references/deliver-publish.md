# 匯出與發布

## deliver.sh

```bash
scripts/deliver.sh films/<片名>/<片名>.mp4
# → films/<片名>/dist/<片名>-{shorts,reels,threads}.mp4
```

1. **色彩範圍**：渲染輸出全範圍 `yuvj420p`，IG／Threads 要標準範圍 → `scale=in_range=pc:out_range=tv,format=yuv420p`＋`-color_range tv`。
2. **三平台匯出**：`$FFMPEG_SKILL/export.py --preset {shorts|reels}`。Threads 借 reels preset。reels 預設裁到 90 秒是舊規格（Reels API 上限 15 分鐘、Threads 5 分鐘），帶 `--allow-long`。
3. **元資料清理**：`video-scrub run` 刪來源身份字串。
4. **音訊與容器**：shorts 沿用 clean 檔音軌；reels／threads 從 `out/mix.wav` 只重編一次 AAC 128k／48kHz，套 `loudnorm=I=-14:TP=-2:LRA=11`；`-use_editlist 0`（Meta 吃不下 edit list）、`-movflags +faststart+negative_cts_offsets`。

驗證：交付檔不比成片短、時長差 ≤ 0.2s、影音 `start_time` 都是 0、無 `elst` 原子，最後 `$FFMPEG_SKILL/check.py --platform`。

## 發布（要使用者點頭，不可收回）

```bash
python3 scripts/publish/public_path.py films/<片名>          # 先產隨機 token
python3 scripts/publish/meta_publish.py films/<片名> --yes   # IG Reels + Threads
python3 scripts/publish/yt_upload.py   films/<片名> --yes   # YouTube Shorts
```

發完把平台連結與時間寫進 `meta/published.json`。設定與權杖見 `docs/PUBLISH-SETUP.md`；權杖值不進 repo、不進對話。YT OAuth 在 Testing 狀態 7 天到期，`scripts/publish/tokens.py` 報到期日。

公開網址衛生：路徑用 16+ 位十六進位隨機 token、不用片名、每次換新；只開那一支 mp4，不暴露資料夾；平台抓完立刻關 funnel 伺服器。

刪已發貼文也要點頭；IG 貼文 API 刪不掉，走網頁（`docs/HANDOFF-threads-delete.md`）。

## 合規

AI 揭露（正本 `docs/COMPLIANCE.md`）：

- YouTube「是否包含經改造或合成的寫實內容」→ **否**（網點排版，非寫實）。
- IG／Threads 說明文字要有：**畫面由程式即時渲染，旁白為合成語音（非真人錄製，亦未複製任何人的聲音）。配樂為本片自行生成。** precheck 檢查「合成語音」與「程式」兩詞。

三份說明文字各要有 AI 揭露句、結尾提問、「來源」開頭行，且**內容互不相同**。

授權：配樂程式自生成；旁白是 VoiceDesign 合成音色，不對應真人；TTS 模型 Apache-2.0；字體系統點陣化不散布；**衛星底圖只有 EOX s2cloudless 2016 版可商用（CC BY 4.0）**，出處寫進 `SOURCES.md` 與說明欄。`SOURCES.md` 範本 `films/dating-bill/SOURCES.md`。

## 數據回饋

`scripts/publish/stats.py` 拉成效、`scripts/publish/postmortem_refresh.py` 補事後數據，寫進 `refs/VIRAL-LEDGER.md` 與 `refs/postmortem.md`，餵下一支選題。
