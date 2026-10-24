# 做聲音：旁白、角色音、混音

全在本機跑，**不打任何 TTS API、不需要憑證**。模型是 Apache-2.0，產出可商用。

## 引擎

| 用途 | 模型 |
|---|---|
| TTS | `mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16` |
| 核稿 ASR | `mlx-community/whisper-large-v3-turbo` |

跑在 M4 的 `mlx-audio==0.5.8` / `mlx 0.32.3`，用 repo 的 `.venv/bin/python`。16 秒旁白約 1.5–3 分鐘（多半是載模型，批次攤掉）。環境建置見 `setup.md`。

## 音色＝範本音檔，不是 voice id

Base 模型靠 `--ref_audio` + `--ref_text` 複製音色。範本在 `assets/voice/`：

| 角色 | 範本 | 逐字稿 |
|---|---|---|
| 女主（host，定案音色 D） | `d24k.wav` | `script.txt` |
| Clawd Bot | `clawd24k.wav` | `clawd-script.txt` |
| 備選男聲 | `m24k.wav` / `m2-24k.wav` / `m3-24k.wav` | `m-script.txt` / `m*-design.txt` |

D 是用 Qwen3 VoiceDesign 以「台灣口音年輕女性、清亮溫柔、紀錄片旁白」生出來的，一致性已用 I1/I2 兩次複製驗過。**範本音檔與逐字稿要一字不差對應**，改了逐字稿音色就會飄。挑選過程與否決理由在 `VOICE.md`。

## narration.md 契約

```markdown
## 鉤子
你覺得台灣人單身，是因為沒錢嗎？

## 錨點
2013 年，行政院主計總處的婦女婚育與就業調查，問了台北市二十五到四十九歲的未婚女性。

## 轉折
但同一份調查問到什麼會讓人更想結婚，排第一的是穩定的工作和收入。

## 落點
...

## 提問
你覺得現在年輕人結婚率低，真正的原因是什麼？
```

硬規則（`precheck.py` 的「旁白稿結構」門）：**鉤子 → 轉折 → 落點 → 提問** 四段齊備且順序正確（中間可插「錨點」等自訂段）；鉤子第一句 ≤ 25 字且含「你」或問號；提問段最後一句以問號收尾。

斷句規則就是按 `。？！?!` 切，所以**標點直接決定一句一檔的切法**。

## scripts/voice.py 做什麼

```bash
.venv/bin/python scripts/voice.py films/<片名>
```

1. 切句、逐句 TTS，輸出 `out/voice/01.wav`…`NN.wav`（48kHz 立體聲，頭尾靜音已切）。
2. 每句用 Whisper 聽回來跟原稿比字元相似度，不到 `SIM_MIN = 0.9` 就重念，最多 `TRIES = 3` 次取最好的一次。三次都不過 → **exit 1，整個 build 停下**。
3. 排時間軸，產 `out/voice/lines.json` 與 `timeline.js`（`window.TL`，畫面端讀它對字幕）。

時間軸常數（`scripts/voice.py` 頂端）：

```
LEAD        = 0.3   第一句開口前的空白（precheck 上限 0.5）
GAP_LINE    = 0.25  同段句子之間
GAP_SECTION = 0.6   換段多停一下，給畫面轉場
TAIL        = 1.2   最後一句到片尾
TEMPO       = 1.0   整片語速（ffmpeg atempo，音高不變）
```

`pace.json` 可覆蓋 `gap_line`、`gap_section`、`tempo`。

`lines.json` 每句：

```json
{"section":"鉤子","text":"你覺得台灣人單身，是因為沒錢嗎？","dur":4.646,
 "t0":0.3,"t1":4.946,"file":"01.wav","sim":1.0,"heard":"你觉得台湾人单身是因为没钱吗","who":"host"}
```

`who` 是「音色＋語速」的指紋（`host`、`clawd`、`host:m24k`、`host@1.2`）。**稿沒改、`who` 沒變的句子不重念** —— 這是改一句不用重跑全片的機制。改音色或 tempo 會讓全片 `who` 變動而全部重念。

## 多角色：cast.json

```json
{
  "_doc": "列在 clawd 裡的句子用 Clawd 音色，其餘用女主 D 音色",
  "clawd": ["沒有。", "嗯。", "因為妳只打了「修一下」。", "我用猜的。"]
}
```

比對是**字串完全相等**，所以 `cast.json` 的句子要跟 `narration.md` 斷句後一字不差（含標點、全半角）。對不上就會用錯音色，而且不報錯。換主旁白：

```json
{"host": {"ref": "assets/voice/m24k.wav", "text": "assets/voice/m-script.txt"}, "clawd": [...]}
```

## 混音：各片自己的 mix.py

```bash
LIB=$LIB "$LIB/.venv/bin/python" mix.py      # 在片目錄下跑
```

讀 `out/voice/lines.json`（旁白位置）＋ `events.json`（音效時間），配樂與音效**全部程式合成**（正弦波和弦、鼓點），沒有第三方素材、沒有授權問題。輸出 `out/mix.wav`（48kHz 立體聲）。

典型參數（`films/dating-bill/mix.py`）：

```
MUSIC_GAIN = 0.55        VOICE_GAIN = 1.0
DUCK_DB   = -11.0        旁白有聲時配樂側鏈壓低（10ms 起音 / 250ms 釋放）
淡入 0.02s / 淡出 0.8s，tanh 飽和 + soft limit
```

事件對聲音：`bed` 配樂床、`blip` 表情變化、`turn` 卡片切換、`whoosh` 過場、`pop`/`stamp`/`swish` UI、`ticks`/`bell` 計數與鈴、`cut` 對談切鏡（不配聲）。`index.html` 新增事件 type 一定要同步補 `mix.py`，否則靜音。

成片響度由 `deliver.sh` 的 `loudnorm` 統一壓到 **-14 LUFS / TP -2**，`mix.py` 不必自己對齊平台標準。

## 驗收

```bash
.venv/bin/python scripts/verify_tts.py films/<片名>/out/voice/01.wav [稿檔]
# exit 0 = 一字不差；exit 1 = 印出缺字與順序問題
# 比對前會正規化：去標點、繁簡、數字讀法（149 → 一百四十九）、同音字（她→他、妳→你、得→的）

.venv/bin/python scripts/narration_check.py films/<片名>
# 聽寫「成片 mp4」本身（不是旁白檔），輸出 out/narration-report.json
# 含 master_sha / narration_sha，precheck 用它驗「旁白真的混進成片了」
```

`precheck.py` 的「旁白進成片」門：聽寫相似度 ≥ 0.85、第一個字 ≤ 0.5s、結尾提問落在片尾 15 秒內且相似度 ≥ 0.7。

## 常見失敗

| 症狀 | 根因 | 處置 |
|---|---|---|
| `voice.py` exit 1 | 單句三次核稿都 < 0.9 | 看 `heard` 欄：多半是繁簡、標點、數字讀法或生僻詞。改稿讓它好念，不要調低門檻 |
| 某句音色錯了但沒報錯 | `cast.json` 句子與 `narration.md` 斷句後不完全相等 | 逐字比對含標點；斷句規則是 `。？！?!` |
| 改一句卻全片重念 | 改了音色範本或 `pace.json` 的 tempo（`who` 全變） | 預期行為，等它跑完 |
| Metal kernel 載入失敗（啟動幾秒內掛） | 記憶體不足 | 關掉其他程式重跑；`heavy` 閘本來就在管這件事 |
| 成片沒聲音 | `mux.sh` 沒吃到 `out/mix.wav` | 檢查 `mix.py` 輸出路徑與 `build.sh` 的合軌那步 |
| 新加的視覺事件沒聲音 | `mix.py` 沒有該 type 的對應 | 補 `mix.py` |
