# 從空白開始：環境與依賴

這個 repo **不能單獨跑**。渲染器、匯出 preset、元資料清理都在 repo 外。換機器或新機接手先把這頁跑完。

## 外部依賴

| 依賴 | 路徑（預設） | 誰用 | 沒有會怎樣 |
|---|---|---|---|
| `lemo-opuscar` 渲染器 | `~/dev/lemo-opuscar`（`$LIB`） | `build.sh` 的事件表、渲染、合軌、readcheck | 做不出畫面 |
| `ffmpeg-skill` | `~/dev/ffmpeg-skill/scripts` | `deliver.sh` 的 `export.py`、`check.py` | 匯不出三平台檔 |
| `video-scrub` | `~/dev/reelbench-skills/skills/video-scrub/scripts/video-scrub.mjs` | `deliver.sh` 清來源元資料 | precheck 元資料門不過 |
| 重活閘 `heavy` | `~/.local/bin/heavy` | `build.sh` 開頭自動 exec | 可選，但同時跑兩個重活會搶爆 GPU／記憶體 |
| ffmpeg / ffprobe | PATH | 到處 | 全掛 |
| node | PATH | 渲染、seek／textless 檢查 | 畫面與動畫檢查全掛 |

`$LIB` 可用環境變數覆蓋：`LIB=/path/to/lemo-opuscar bash build.sh`。

## Python 環境

兩個 interpreter，用途不可互換（`CLAUDE.md` 規則）：

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python 'mlx-audio==0.5.8'
```

- `.venv/bin/python` —— 配音（`voice.py`）、核稿、拆解。
- 系統 `python3` —— `precheck.py`、`rhythm_check.py`、`scripts/publish/cdp.py`（`.venv` 沒裝 playwright）。
- `$LIB/.venv/bin/python` —— 各片的 `mix.py`。

`mix.py` 也吃 `LIB` 環境變數找音訊工具，所以要 `LIB="$LIB" "$LIB/.venv/bin/python" mix.py`。

## 聲音範本

`assets/voice/` 的 `d24k.wav`＋`script.txt`（女主）、`clawd24k.wav`＋`clawd-script.txt`（Clawd）是音色的唯一來源，**進版控、不要動**。動了全片音色就飄，而且舊音檔不會自動重念。

## 吉祥物素材

`assets/mascot/`（`clawd-bot-shot.mjs`、`clawd-bot/`、`host/`、`scene/`）。進片子用：

```bash
scripts/mascot_install.sh films/<片名>
```

## 發布憑證

YouTube／Meta 的權杖設定全寫在 `docs/PUBLISH-SETUP.md`，續期靠 `ops/com.host.vibe-token-refresh.plist`（launchd）。權杖值不進 repo、不進對話。Testing 狀態的 YT OAuth 7 天到期，`scripts/publish/tokens.py` 會報到期日。

## 裝機驗收

```bash
cd ~/dev/vibe-shorts-pipeline
for t in tests/test_*.py;  do python3 "$t" || echo "FAIL $t"; done
for t in tests/test_*.mjs; do node    "$t" || echo "FAIL $t"; done
.venv/bin/python -c "import mlx_audio; print('tts ok')"
node -e "console.log(require('fs').existsSync(process.env.HOME+'/dev/lemo-opuscar/core/render/video.mjs') ? 'lib ok' : 'LIB MISSING')"
```

全過才算接手完成。`tests/` 不連網。
