# 來源：每段敘述對應的實作檔

技能包文字取自下列檔案，**衝突時以這些檔案為準**。路徑相對流水線根目錄（公開版＝技能包根目錄，`scripts/`、`tests/`、`films/nerf/`、`assets/mascot/` 都在裡面）；標「私有端」的留在流水線正本（綁帳號或是內容資產），技能包不帶。

## 上游（公開 repo，自己 clone）

| 什麼 | repo | 授權 | 技能包裡誰用 |
|---|---|---|---|
| 渲染器 `$LIB`：`core/render/{video,events,readcheck,still,serve,slot,page,browser}.mjs`、`mux.sh`、`core/audio/`、`core/tts/` | [lemomo-ai/lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar) | MIT | `films/nerf/build.sh`、`mix.py` |
| 匯出 preset `export.py`／`check.py` | [kajisho5/ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill) | MIT | `scripts/deliver.sh` |
| `video-scrub.mjs` 清元資料 | [eternityspring/reelbench-skills](https://github.com/eternityspring/reelbench-skills) | Apache-2.0 | `scripts/deliver.sh` |
| 本機 TTS `mlx-audio`＋Qwen3-TTS-12Hz-1.7B-Base | [Blaizzy/mlx-audio](https://github.com/Blaizzy/mlx-audio)、[QwenLM](https://huggingface.co/Qwen) | MIT／Apache-2.0 | `scripts/voice.py` |
| 核稿 ASR Whisper large-v3-turbo | [mlx-community](https://huggingface.co/mlx-community/whisper-large-v3-turbo) | MIT | `scripts/verify_tts.py` |

## setup.md

- `scripts/mascot_install.sh` 為何要複製不能引用（`serve.mjs` 把片目錄當掛載根）
- `assets/mascot/` 角色素材；聲紋參考音要自備（本 repo 不帶）
- 發布憑證與 `scripts/publish/`：私有端（綁帳號）

## graphics.md

- `films/nerf/build.sh` 渲染鏈與各步指令（`$LIB` 的四支腳本都在這裡被呼叫）
- `films/nerf/index.html` 對談片範本，`window.DUR`／`render`／`TEXTS`／`EV`／`CUES`／`SHAKES` 契約
- `films/nerf/events.json`、`pace.json`、`cast.json`、`rhythm-profile`
- 資料卡型範本（字體、安全邊界、easing 另一種寫法）：私有端 `films/dating-bill/index.html`

## animation.md

- `films/nerf/mascot/clawd-bot-shot.mjs` `poseAt(t)` 與封閉式平滑（`LOOK_DAMP`、`POKE_DECAY`）
- `assets/mascot/clawd-bot/README.md` 角色幾何座標與狀態機；`clawd-bot-rig.js` 是**累積狀態**版本，渲染不要用
- `scripts/seek_check.mjs` 三道門
- `scripts/rhythm_check.py` 三組 profile 基準與 `STILL_THRESHOLD`（檔頭註解寫了每次放寬的理由）
- `scripts/textless_check.mjs`
- `tests/test_mascot_pose.mjs` 亂序呼叫同 t 必同 pose

## audio.md

- `scripts/voice.py` 模型、範本、`SIM_MIN`／`TRIES`／`LEAD`／`GAP_*`／`TAIL`／`TEMPO`、`who_of()` 增量重念
- `scripts/voice_design.py` 音色怎麼生出來的
- `scripts/verify_tts.py` 正規化與同音字表
- `scripts/narration_check.py` 成片聽寫報告
- `films/nerf/mix.py` 增益、側鏈、事件對聲音
- `tests/test_voice.py`、`tests/test_voice_reusable.py`

## gates.md

- `scripts/precheck.py` **閾值正本**（`HOOK_MAX_CHARS`、`LEAD_SILENCE_MAX`、`ASR_SIM_MIN`、`QUESTION_TAIL_S`、`QUESTION_SIM_MIN`、`COVER_LUMA_MIN`、`COVER_TEXT_H`、`COVER_TEXT_MIN`、`REVIEW_MIN`、`COPY_SIM_MAX`、`COPY_MIN_CHARS`、`VIRAL_MIN`）
- `scripts/qa_sheet.sh`、`scripts/devils.sh`
- `tests/` 測試對應表的來源

## deliver-publish.md

- `scripts/deliver.sh` 四步、`--allow-long`、`loudnorm`、容器旗標
- 私有端：`scripts/publish/`（`public_path.py`、`meta_publish.py`、`yt_upload.py`、`tokens.py`、`stats.py`、`postmortem_refresh.py`）、`docs/COMPLIANCE.md` AI 揭露標準句、`docs/DISTRIBUTION.md`

## 選題（另一個 skill）

- [viral-scout](https://github.com/royalskynet/viral-scout-skill)：方法與帳本格式。帳本內容（爆款證據、頻道中位數、拆片表）是資產，留私有端 `refs/`
