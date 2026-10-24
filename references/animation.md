# 產動畫：無狀態姿態與尋幀一致

動畫沒有時間軸編輯器。每個會動的東西都是「給我秒數 `t`，我回傳那一刻的姿態」的純函數。這是被渲染器逼出來的設計，不是風格選擇。

## 為什麼必須無狀態

`video.mjs --workers 6` 把片子切成 6 段，各 worker 從自己那段的起始幀**冷啟動**往下渲。如果姿態是累積出來的（每幀 `v += (target - v) * 0.12`），那同一個 `t` 在「冷啟動」和「從前面接續」兩種路徑下會得到不同結果 → 接縫處畫面跳動。

所以上游的 `clawd-bot-rig.js` **不能用**：它的 `smoothLook`、`pokeAmount` 是逐幀累積的狀態變數。

## poseAt(t) 契約

`assets/mascot/clawd-bot-shot.mjs`（用 `scripts/mascot_install.sh <片目錄>` 複製進片子）：

```js
export function poseAt(t, track = {})
// track: {fps: 30, states: [{t, state}], looks: [{t, x, y}], pokes: [t, ...]}
// 回傳: {state, bobY, scaleX, scaleY, shadowRx, face, sparkRot, clawL, clawR, ...}
```

指數平滑改寫成 `t` 的封閉式，不靠迭代：

```js
const k = Math.pow(1 - LOOK_DAMP, span * fps);   // LOOK_DAMP = 0.12
v = c.x + (v.x - c.x) * k;                        // POKE_DECAY = 0.88
```

規則：`poseAt` 同一個 `t` 不論呼叫順序、呼叫幾次，結果必須一致（誤差 < 1e-6）。`tests/test_mascot_pose.mjs` 亂序呼叫驗這件事。

對談片的鏡頭與表情同理：`films/nerf/index.html` 的 `poseHost(t)` 用 `lineAt(t)` 查當下是第幾句，再用 `track(t, fn)` 在一秒內平滑過渡到該句的目標值，全部由 `t` 推導。

## 轉場寫法

卡片／文字進場用 easing 函數吃「卡內相對秒數」，不吃全域狀態：

```js
say(cd.head, 60, 520 + big * 0.86, big, CREAM, inv(0.05, 0.6, lt), { id: 'head1' });
// lt = 這張卡內的相對時間；inv(start, dur, lt) 回傳 0→1 的透明度
```

## 驗收

```bash
LIB=$LIB node scripts/seek_check.mjs . --fps 30 --workers 6 --size 1080x1920
```

三道門：

1. **尋幀一致**：在 worker 交界幀，比對「冷啟動畫的 PNG」與「從前 3 幀接續後再畫的 PNG」，位元組必須相同。不同就是有人藏了狀態。
2. **無外部請求**：攔 page 的 request，hostname 只准 `127.0.0.1` / `localhost`。線上字體、CDN 會讓渲染不可復現。
3. **震動對時**：`window.SHAKES` 每個時間點都要對應到 `EV` 的某個事件（誤差 < 0.5 幀）。

不過就修 `index.html`，不要調閘門。`build.sh` 把 `seek_check` 排在渲染之前，就是為了在花 8 分鐘渲圖前先擋下來。

## 節奏基準

`scripts/rhythm_check.py <成片.mp4>` 量動態。基準按**成片同目錄的 `rhythm-profile` 檔**（內容一行）選，沒這個檔就用預設 `vkv`：

| profile | 靜止秒比例 | 最長連續靜止 | 亮度差均值 | 依據 |
|---|---|---|---|---|
| `vkv`（預設） | ≤ 22.3% | ≤ 4 秒 | ≥ 基準均值 ×0.6 | 8 條抖音知識爆款逆向（`refs/vkv/style-guide.md`） |
| `dialogue`（對談片） | ≤ 64% | ≤ 9 秒 | ≥ 0.90 | IG 對談爆款 10 支全過的邊界 |
| `map`（衛星地圖） | ≤ 75% | ≤ 8 秒 | ≥ 0.95 | 使用者目視核准（2026-10-14 兩次放寬） |

「靜止秒」＝該秒平均幀差 < `STILL_THRESHOLD = 1.0`。

對談片與地圖片各自有基準，是因為它們在 vkv 基準下全軍覆沒，而對標爆款本身也過不了 —— 可見這兩項對該格式的流量無關。**新增或放寬 profile 要使用者目視核准**，不准為了過門自己調。

## 文件

`docs/MASCOT.md` 是角色動作的正本；`docs/RESEARCH-claude-motion.md` 記了上游 rig 為何被淘汰。
