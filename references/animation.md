# 產動畫：無狀態姿態與尋幀一致

**純函數規則**：每個會動的東西都是「給秒數 `t`，回傳那一刻姿態」的純函數。`video.mjs --workers 6` 讓各 worker 從自己那段起始幀冷啟動，逐幀累積的值（`v += (target - v) * 0.12`）在接縫處會跳。上游 `clawd-bot-rig.js` 的 `smoothLook`、`pokeAmount` 是累積狀態，**不能用**。

## poseAt(t) 契約

`assets/mascot/clawd-bot-shot.mjs`（`scripts/mascot_install.sh <片目錄>` 複製進片子）：

```js
export function poseAt(t, track = {})
// track: {fps: 30, states: [{t, state}], looks: [{t, x, y}], pokes: [t, ...]}
// 回傳: {state, bobY, scaleX, scaleY, shadowRx, face, sparkRot, clawL, clawR, ...}
```

指數平滑寫成 `t` 的封閉式，不迭代：

```js
const k = Math.pow(1 - LOOK_DAMP, span * fps);   // LOOK_DAMP = 0.12
v = c.x + (v.x - c.x) * k;                        // POKE_DECAY = 0.88
```

同一個 `t` 不論呼叫順序與次數，結果一致（誤差 < 1e-6）；`tests/test_mascot_pose.mjs` 亂序呼叫驗。

對談片鏡頭與表情同理：`films/nerf/index.html` 的 `poseHost(t)` 用 `lineAt(t)` 查當下第幾句，`track(t, fn)` 在一秒內平滑過渡到該句目標值。

## 轉場

進場 easing 吃「卡內相對秒數」：

```js
say(cd.head, 60, 520 + big * 0.86, big, CREAM, inv(0.05, 0.6, lt), { id: 'head1' });
// lt = 卡內相對時間；inv(start, dur, lt) 回傳 0→1 透明度
```

## 驗收：seek_check

```bash
LIB=$LIB node scripts/seek_check.mjs . --fps 30 --workers 6 --size 1080x1920
```

1. **尋幀一致**：worker 交界幀「冷啟動」與「前 3 幀接續」畫出的 PNG 位元組相同；不同就是有隱藏狀態。
2. **無外部請求**：hostname 只准 `127.0.0.1`／`localhost`（線上字體、CDN 不可復現）。
3. **震動對時**：`window.SHAKES` 每點對得上 `EV` 某事件（誤差 < 0.5 幀）。

不過就修 `index.html`。

## 節奏基準

`scripts/rhythm_check.py <成片.mp4>`，基準按成片同目錄 `rhythm-profile` 檔（一行）選，沒有就用 `vkv`：

| profile | 靜止秒比例 | 最長連續靜止 | 亮度差均值 |
|---|---|---|---|
| `vkv`（預設） | ≤ 22.3% | ≤ 4 秒 | ≥ 基準均值 ×0.6 |
| `dialogue`（對談） | ≤ 64% | ≤ 9 秒 | ≥ 0.90 |
| `map`（衛星地圖） | ≤ 75% | ≤ 8 秒 | ≥ 0.95 |

「靜止秒」＝該秒平均幀差 < `STILL_THRESHOLD = 1.0`。各基準依據寫在 `rhythm_check.py` 檔頭。新增或放寬 profile 要使用者目視核准。

角色動作正本 `docs/MASCOT.md`。
