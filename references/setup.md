# 從空白開始：環境與依賴

技能包自己帶閘門腳本（`scripts/`）、測試（`tests/`）與一支可建置的範本片（`films/nerf/`），但**渲染器與匯出工具在外部**，是三個公開 repo。這頁跑完才能建片。

## 外部依賴（都是公開 repo，照這三行裝）

```bash
git clone https://github.com/lemomo-ai/lemo-opuscar   ~/dev/lemo-opuscar      # 渲染器（MIT）
git clone https://github.com/kajisho5/ffmpeg-skill    ~/dev/ffmpeg-skill      # 匯出 preset（MIT）
git clone https://github.com/eternityspring/reelbench-skills ~/dev/reelbench-skills  # video-scrub（Apache-2.0）
```

| 依賴 | 路徑（預設） | 誰用 | 沒有會怎樣 |
|---|---|---|---|
| `lemo-opuscar` 渲染器 | `~/dev/lemo-opuscar`（`$LIB`） | `build.sh` 的事件表、渲染、合軌、readcheck | 做不出畫面 |
| `ffmpeg-skill` | `~/dev/ffmpeg-skill/scripts` | `deliver.sh` 的 `export.py`、`check.py` | 匯不出三平台檔 |
| `video-scrub` | `~/dev/reelbench-skills/skills/video-scrub/scripts/video-scrub.mjs` | `deliver.sh` 清來源元資料 | precheck 元資料門不過 |
| 重活閘 `heavy` | `~/.local/bin/heavy` | `build.sh` 開頭自動 exec | 可選；沒有就自己別同時跑兩個建置 |
| ffmpeg / ffprobe | PATH | 到處 | 全掛 |
| node ≥20 | PATH | 渲染、seek／textless 檢查 | 畫面與動畫檢查全掛 |

`$LIB` 可用環境變數覆蓋：`LIB=/path/to/lemo-opuscar bash build.sh`。渲染器自己的依賴（playwright-core、three、它的 `.venv`）照它 README 裝。

## Python 環境

兩個 interpreter，用途不可互換：

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python 'mlx-audio==0.5.8'
```

- `.venv/bin/python` —— 配音（`voice.py`）、核稿、拆解。
- 系統 `python3` —— `precheck.py`、`rhythm_check.py`。
- `$LIB/.venv/bin/python` —— 各片的 `mix.py`。

`mix.py` 也吃 `LIB` 環境變數找音訊工具，所以要 `LIB="$LIB" "$LIB/.venv/bin/python" mix.py`。

`mlx-audio` 的 Qwen3-TTS 只跑 Apple Silicon。沒有 Apple Silicon、或不想自備聲紋，就把 `build.sh` 的「旁白」那步換成渲染器內建的 `"$LIB/.venv/bin/python" "$LIB/core/tts/tts_zh.py" lines.json out/voice`（edge-tts，線上、不用參考音，音色是微軟的 neural voice），其餘步驟不變。注意它不做核稿重念，`narration_check.py` 的字幕對齊門要自己顧。

## 聲音範本（要自備）

配音走聲紋複製：音色＝**一段參考音＋它的逐字稿**，不是廠商的 voice id。這個技能包**不帶任何參考音**，自己錄：

1. 錄 8～12 秒單人乾聲（無音樂、無混響），轉成 24kHz 單聲道 wav，放 `assets/voice/me24k.wav`。
2. 逐字稿一字不差寫進 `assets/voice/me-script.txt`（`voice.py` 拿它當 prompt，錯字會讓音色飄）。
3. 片子的 `cast.json` 指過去：

```json
{"host": {"ref": "assets/voice/me24k.wav", "text": "assets/voice/me-script.txt"}}
```

缺檔時 `voice.py` 會直接報這段補法再退出。第二個聲音（對談用）同理，預設讀 `assets/voice/clawd24k.wav`＋`clawd-script.txt`。

換了參考音，`lines.json` 的 `who` 會帶新檔名，舊音色念過的句子不會被沿用——**所以不要中途換**，整片音色會前後不一。

## 吉祥物素材

`assets/mascot/`（`clawd-bot-shot.mjs` 的 `poseAt(t)`、`clawd-bot/` 向量原檔、`host/`、`scene/`）。進片子用：

```bash
scripts/mascot_install.sh films/<片名>
```

角色是原創幾何設計，可自由替換成自己的 SVG：只要照 `animation.md` 的 `poseAt(t)` 契約輸出同樣的欄位，`seek_check.mjs` 就會過。

## 發布憑證

`scripts/publish/` 與憑證設定綁特定帳號，留在流水線私有端（`docs/PUBLISH-SETUP.md`），不在技能包裡。自己發布就用 `deliver.sh` 產出的三平台檔手動上傳，或接自己的 API。權杖值不進 repo、不進對話。

## 裝機驗收

```bash
for t in tests/test_*.py;  do python3 "$t" || echo "FAIL $t"; done
for t in tests/test_*.mjs; do node    "$t" || echo "FAIL $t"; done
.venv/bin/python -c "import mlx_audio; print('tts ok')"
node -e "console.log(require('fs').existsSync(process.env.HOME+'/dev/lemo-opuscar/core/render/video.mjs') ? 'lib ok' : 'LIB MISSING')"
```

全過才算接手完成。`tests/` 不連網。
