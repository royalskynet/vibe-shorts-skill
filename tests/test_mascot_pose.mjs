// Clawd Bot 姿態層：同 t 必同 pose（video.mjs 多 worker 亂序跑的前提），且阻尼公式要跟逐幀迭代算出來的一樣。
// 跑：node tests/test_mascot_pose.mjs
import assert from 'node:assert/strict';
import { poseAt } from '../assets/mascot/clawd-bot-shot.mjs';

const FPS = 30;
const track = {
  fps: FPS,
  states: [{ t: 0, state: 'idle' }, { t: 2, state: 'thinking' }, { t: 4, state: 'happy' }, { t: 6, state: 'sleep' }],
  looks: [{ t: 0, x: 0, y: 0 }, { t: 1, x: 1, y: -0.5 }, { t: 3, x: -0.8, y: 0.3 }],
  pokes: [2.5],
};
const frames = [...Array(240)].map((_, f) => f / FPS);

// 1) 亂序、重複呼叫都要拿到同一個 pose
const inOrder = frames.map(t => JSON.stringify(poseAt(t, track)));
const shuffled = [...frames.keys()].sort((a, b) => Math.sin(a * 7.1) - Math.sin(b * 7.1));
for (const i of shuffled) {
  assert.equal(JSON.stringify(poseAt(frames[i], track)), inOrder[i], `frame ${i} 的 pose 看呼叫順序`);
}

// 2) 視線阻尼的封閉式 == 原 rig 逐幀 v += (target - v) * 0.12
let ref = { x: 0, y: 0 };
for (let f = 0; f < frames.length; f++) {
  const t = frames[f];
  let tgt = track.looks[0];
  for (const c of track.looks) if (t >= c.t) tgt = c;
  const pose = poseAt(t, track);
  if (pose.state !== 'sleep') {
    assert.ok(Math.abs(pose.face.x - ref.x * 7) < 1e-6, `frame ${f} 視線 x 與逐幀迭代不符`);
    assert.ok(Math.abs(pose.face.y - ref.y * 4.5) < 1e-6, `frame ${f} 視線 y 與逐幀迭代不符`);
  }
  ref = { x: ref.x + (tgt.x - ref.x) * 0.12, y: ref.y + (tgt.y - ref.y) * 0.12 };
}

// 3) 狀態軌要真的切到對應的狀態與雙螯位置（README §4）
assert.equal(poseAt(1.5, track).state, 'idle');
assert.equal(poseAt(3, track).state, 'thinking');
assert.equal(poseAt(3, track).clawL.x, -58);
assert.equal(poseAt(5, track).state, 'happy');
assert.equal(poseAt(5, track).clawL.y, -10);
assert.equal(poseAt(7, track).state, 'sleep');
assert.deepEqual(poseAt(7, track).clawR, { x: 54, y: 10, rot: 12 });

// 4) poke 的彈性要衰減掉，不是永遠黏著
const kickAt = t => Math.abs(poseAt(t, track).scaleX - poseAt(t, { ...track, pokes: [] }).scaleX);
assert.ok(kickAt(2.55) > 0.02, 'poke 當下沒有果凍縮放');
assert.ok(kickAt(4.5) === 0, 'poke 的效果沒有衰減到 0');

// 5) 沒給軌道也要能跑，未知狀態要炸
assert.equal(poseAt(0.4).state, 'idle');
assert.throws(() => poseAt(0, { states: [{ t: 0, state: 'angry' }] }), /unknown mascot state/);

console.log('ok test_mascot_pose');
