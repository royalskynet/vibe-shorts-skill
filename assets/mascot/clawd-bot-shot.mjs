// Clawd Bot 的決定性姿態層：同一個 t 一定得到同一個 pose，不看呼叫順序。
// 為什麼不直接用設計正本 clawd-bot/clawd-bot-rig.js：它的 smoothLook / pokeAmount 是每呼叫一次就乘一次的累積狀態，
// 而 core/render/video.mjs 會多 worker 各從自己的起始 frame 跑、還會先預熱幾張卡，累積狀態在那裡會漂，seek_check.mjs 會抓到不一致。
// 公式、座標、色票全部照 clawd-bot/README.md §4；差別只是把阻尼寫成 t 的封閉式。
export const STATES = ['idle', 'thinking', 'happy', 'sleep'];

const SPEED = { idle: 1.0, thinking: 2.2, happy: 2.8, sleep: 0.5 };
const LOOK_DAMP = 0.12;   // 原 rig 每幀的插值係數
const POKE_DECAY = 0.88;  // 原 rig 每幀的衰減係數

const at = (cues, t) => {
  let cur = cues[0];
  for (const c of cues) if (t >= c.t) cur = c; else break;
  return cur;
};

// 一串 {t, x, y} 視線目標，算出 t 時刻平滑後的視線。
// 原 rig：每幀 v += (target - v) * 0.12 → 一段時間後 v = target + (v0 - target) * (1-0.12)^(幀數)。
function lookAt(cues, t, fps) {
  let v = { x: cues[0].x ?? 0, y: cues[0].y ?? 0 };
  for (let i = 0; i < cues.length; i++) {
    const c = cues[i], next = cues[i + 1];
    if (t < c.t) break;
    const span = Math.min(t, next ? next.t : t) - c.t;
    const k = Math.pow(1 - LOOK_DAMP, Math.max(0, span) * fps);
    v = { x: c.x + (v.x - c.x) * k, y: c.y + (v.y - c.y) * k };
  }
  return { x: Math.max(-1, Math.min(1, v.x)), y: Math.max(-1, Math.min(1, v.y)) };
}

function pokeAt(pokes, t, fps) {
  let a = 0;
  for (const p of pokes) {
    if (t < p) continue;
    const v = Math.pow(POKE_DECAY, (t - p) * fps);
    if (v > a) a = v;
  }
  return a < 0.01 ? 0 : Math.min(1, a);
}

/**
 * @param {number} t 秒
 * @param {object} track {states:[{t,state}], looks:[{t,x,y}], pokes:[t], fps}
 */
export function poseAt(t, track = {}) {
  const fps = track.fps || 30;
  const states = track.states?.length ? track.states : [{ t: 0, state: 'idle' }];
  const state = at(states, t).state;
  if (!STATES.includes(state)) throw new Error(`unknown mascot state: ${state}`);
  const look = lookAt(track.looks?.length ? track.looks : [{ t: 0, x: 0, y: 0 }], t, fps);
  const poke = pokeAt(track.pokes || [], t, fps);

  const speed = SPEED[state];
  const phase = t * 2.5 * speed;
  let bobY = Math.sin(phase) * 4.5;
  if (state === 'happy') bobY = -Math.abs(Math.sin(t * 7)) * 15;
  else if (state === 'sleep') bobY = 5 + Math.sin(t * 1.4) * 1.8;

  const squish = Math.sin(phase) * 0.03;
  const kick = Math.sin(poke * Math.PI * 3) * poke;
  const pose = {
    state,
    bobY,
    scaleX: 1 + squish + kick * 0.25,
    scaleY: 1 - squish - kick * 0.22,
    shadowRx: 50 - bobY * 0.35,
    face: { x: state === 'sleep' ? 0 : look.x * 7, y: state === 'sleep' ? 1.5 : look.y * 4.5 },
    sparkRot: t * 90 * speed,
  };

  if (state === 'thinking') {
    pose.clawL = { x: -58, y: 2 + Math.sin(t * 24) * 6, rot: 15 };
    pose.clawR = { x: 58, y: 2 + Math.cos(t * 24) * 6, rot: -15 };
  } else if (state === 'happy') {
    const cheer = Math.sin(t * 14) * 18;
    pose.clawL = { x: -64, y: -10, rot: 25 + cheer };
    pose.clawR = { x: 64, y: -10, rot: -25 - cheer };
  } else if (state === 'sleep') {
    pose.clawL = { x: -54, y: 10, rot: -12 };
    pose.clawR = { x: 54, y: 10, rot: 12 };
  } else {
    const hover = Math.sin(t * 3) * 4, tilt = Math.sin(t * 2) * 6;
    pose.clawL = { x: -66, y: 2 + hover, rot: tilt };
    pose.clawR = { x: 66, y: 2 + hover, rot: -tilt };
  }
  return pose;
}

// 面罩五官與特效：只看 state，所以切回同一個 state 時畫面一定一樣。
const FACE = {
  idle: { eyes: 'normal', mouth: ['#68E399', 'M-5,7 Q0,11 5,7'] },
  thinking: { eyes: 'normal', mouth: ['#F6B966', 'M-6,8 L6,8'] },
  happy: { eyes: 'happy', mouth: ['#68E399', 'M-5,7 Q0,11 5,7'] },
  sleep: { eyes: 'sleep', mouth: ['#FF8577', 'M-5,9 Q0,5 5,9'] },
};
const FX = {
  idle: '',
  thinking: '<g transform="translate(56, -68)"><circle cx="0" cy="0" r="16" fill="#FFF" stroke="#252422" stroke-width="2.5"/>'
    + '<text x="0" y="6" font-size="16" text-anchor="middle" fill="#D97757">✻</text></g>',
  happy: '<g><text x="-70" y="-54" font-size="20">✨</text><text x="54" y="-56" font-size="18" fill="#D97757">✻</text>'
    + '<text x="0" y="-82" font-size="18" text-anchor="middle" fill="#FF7E79">♥</text></g>',
  sleep: '<text x="48" y="-55" font-size="18" font-weight="bold" fill="#8C857B">Z</text>'
    + '<text x="64" y="-72" font-size="14" font-weight="bold" fill="#A8A096">z</text>'
    + '<text x="76" y="-85" font-size="11" font-weight="bold" fill="#C2B9AE">z</text>',
};

const n = v => (Math.round(v * 100) / 100).toFixed(2);

/** 把 pose 寫到頁面上那棵 SVG（瀏覽器端）。 */
export function applyPose(svgRoot, pose) {
  const q = sel => svgRoot.querySelector(sel);
  q('#actor').setAttribute('transform',
    `translate(0, ${n(pose.bobY)}) scale(${n(pose.scaleX)}, ${n(pose.scaleY)})`);
  q('#shadow').setAttribute('rx', n(pose.shadowRx));
  q('#face').setAttribute('transform', `translate(${n(pose.face.x)}, ${n(pose.face.y)})`);
  q('#crab-spark').setAttribute('transform', `translate(0, -6) rotate(${n(pose.sparkRot)})`);
  q('#claw-l').setAttribute('transform', `translate(${n(pose.clawL.x)}, ${n(pose.clawL.y)}) rotate(${n(pose.clawL.rot)})`);
  q('#claw-r').setAttribute('transform', `translate(${n(pose.clawR.x)}, ${n(pose.clawR.y)}) rotate(${n(pose.clawR.rot)})`);

  const f = FACE[pose.state];
  for (const name of ['normal', 'happy', 'sleep']) {
    q(`#eyes-${name}`).style.display = f.eyes === name ? 'block' : 'none';
  }
  const mouth = q('#mouth');
  mouth.setAttribute('stroke', f.mouth[0]);
  mouth.setAttribute('d', f.mouth[1]);
  const fx = q('#fx');
  if (fx.dataset.state !== pose.state) { fx.innerHTML = FX[pose.state]; fx.dataset.state = pose.state; }
}

/** 一行就能用：mount 回傳的函式放進片子的 render(t) 裡。 */
export function mountMascot(svgRoot, track) {
  return t => { applyPose(svgRoot, poseAt(t, track)); };
}
