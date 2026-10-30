# 做聲音：旁白、角色音、混音

全在本機跑，不打 TTS API、不需要憑證；模型 Apache-2.0，產出可商用。

## 引擎

TTS `mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16`；核稿 ASR `mlx-community/whisper-large-v3-turbo`。`mlx-audio==0.5.8`／`mlx 0.32.3`，repo 的 `.venv/bin/python`。16 秒旁白約 1.5–3 分鐘（多半在載模型）。

## 音色＝範本音檔＋逐字稿

Base 模型靠 `--ref_audio`＋`--ref_text` 複製音色，範本在 `assets/voice/`：

| 角色 | 範本 | 逐字稿 |
|---|---|---|
| 女主（host，定案音色 D） | `d24k.wav` | `script.txt` |
| Clawd Bot | `clawd24k.wav` | `clawd-script.txt` |
| 備選男聲 | `m24k.wav`／`m2-24k.wav`／`m3-24k.wav` | `m-script.txt`／`m*-design.txt` |

**範本音檔與逐字稿要一字不差對應**，否則音色飄。選型理由在 `VOICE.md`。

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

precheck「旁白稿結構」門：**鉤子 → 轉折 → 落點 → 提問** 四段齊且順序對（中間可插自訂段）；鉤子首句 ≤ 25 字且含「你」或問號；提問段末句以問號收尾。

斷句按 `。？！?!` 切，**標點直接決定一句一檔的切法**。

## voice.py

```bash
.venv/bin/python scripts/voice.py films/<片名>
```

1. 逐句 TTS → `out/voice/01.wav`…（48kHz 立體聲，頭尾靜音已切）。
2. 每句 Whisper 聽回比字元相似度，< `SIM_MIN = 0.9` 重念，最多 `TRIES = 3` 取最好；三次都不過 → exit 1，build 停。
3. 產 `out/voice/lines.json` 與 `timeline.js`（`window.TL`）。

時間軸常數（檔頂；`pace.json` 可覆蓋 `gap_line`、`gap_section`、`tempo`）：

```
LEAD        = 0.3   第一句開口前（precheck 上限 0.5）
GAP_LINE    = 0.25  同段句間
GAP_SECTION = 0.6   換段
TAIL        = 1.2   末句到片尾
TEMPO       = 1.0   整片語速（atempo，音高不變）
```

`lines.json` 每句：

```json
{"section":"鉤子","text":"你覺得台灣人單身，是因為沒錢嗎？","dur":4.646,
 "t0":0.3,"t1":4.946,"file":"01.wav","sim":1.0,"heard":"你觉得台湾人单身是因为没钱吗","who":"host"}
```

`who` 是「音色＋語速」指紋（`host`、`clawd`、`host:m24k`、`host@1.2`）。**稿與 `who` 都沒變的句子不重念**；改音色範本或 tempo 會全片重念。整片中途不換參考音，否則音色前後不一。

## 多角色：cast.json

```json
{
  "_doc": "列在 clawd 裡的句子用 Clawd 音色，其餘用女主 D 音色",
  "clawd": ["沒有。", "嗯。", "因為妳只打了「修一下」。", "我用猜的。"]
}
```

比對是**字串完全相等**：`cast.json` 的句子要與 `narration.md` 斷句後一字不差（含標點、全半角），對不上會用錯音色且不報錯。換主旁白：

```json
{"host": {"ref": "assets/voice/m24k.wav", "text": "assets/voice/m-script.txt"}, "clawd": [...]}
```

## 混音：各片的 mix.py

```bash
LIB=$LIB "$LIB/.venv/bin/python" mix.py      # 在片目錄下跑
```

讀 `out/voice/lines.json`＋`events.json`，配樂與音效全程式合成（正弦波和弦、鼓點），輸出 `out/mix.wav`（48kHz 立體聲）。典型參數（`films/dating-bill/mix.py`）：

```
MUSIC_GAIN = 0.55        VOICE_GAIN = 1.0
DUCK_DB   = -11.0        旁白有聲時配樂側鏈壓低（10ms 起音 / 250ms 釋放）
淡入 0.02s / 淡出 0.8s，tanh 飽和 + soft limit
```

事件 type：`bed` 配樂床、`blip` 表情變化、`turn` 卡片切換、`whoosh` 過場、`pop`／`stamp`／`swish` UI、`ticks`／`bell` 計數與鈴、`chime`、`click`、`cut` 對談切鏡（不配聲）。`index.html` 新增 type 要同步補 `mix.py`，否則靜音。

響度由 `deliver.sh` 的 `loudnorm` 統一壓到 -14 LUFS／TP -2，`mix.py` 不必自己對齊。

## 驗收

```bash
.venv/bin/python scripts/verify_tts.py films/<片名>/out/voice/01.wav [稿檔]
# exit 0 = 一字不差；exit 1 印缺字與順序。比對前正規化：去標點、繁簡、數字讀法、同音字（她→他、妳→你、得→的）

.venv/bin/python scripts/narration_check.py films/<片名>
# 聽寫成片 mp4 本身 → out/narration-report.json（含 master_sha／narration_sha，precheck 驗旁白真的混進成片）
```

## 常見失敗

| 症狀 | 根因 | 處置 |
|---|---|---|
| `voice.py` exit 1 | 單句三次核稿 < 0.9 | 看 `heard`：多半是繁簡、標點、數字讀法或生僻詞。改稿讓它好念，不調門檻 |
| 某句音色錯但沒報錯 | `cast.json` 句子與斷句結果不完全相等 | 逐字比對含標點 |
| 改一句卻全片重念 | 改了音色範本或 tempo | 預期行為 |
| Metal kernel 載入失敗（啟動幾秒內掛） | 記憶體不足 | 關掉其他程式重跑 |
| 成片沒聲音 | `mux.sh` 沒吃到 `out/mix.wav` | 查 `mix.py` 輸出路徑與 `build.sh` 合軌步 |
| 新視覺事件沒聲音 | `mix.py` 沒有該 type | 補 `mix.py` |
