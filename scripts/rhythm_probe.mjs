// 節奏探針：不渲影片，直接在頁面裡量相鄰幀差。
// rhythm_check.py 要先有 mp4 才能量，一次全片渲染三分鐘；調動態量時太慢。
// 這支只抽幾個一秒窗口，在瀏覽器裡把畫布縮到 64x36 比，用的判準跟 rhythm_check.py 一樣。
// 用法：node scripts/rhythm_probe.mjs <片子資料夾> [--fps 30] [--at 0,12,25,37,49,58]
import { openDemo, closeServer, requireDemo } from '/Users/you/lemo-opuscar/core/render/page.mjs';

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const dir = args[0];
requireDemo(dir);
const FPS = +opt('--fps', 30);
const AT = opt('--at', '').split(',').filter(Boolean).map(Number);

const { browser, page } = await openDemo(dir, { w: 1080, h: 1920, warnings: true });
const dur = await page.evaluate(() => window.DUR);
const windows = AT.length ? AT : [0, 1, 2, 3, 4, 5].map(i => +(dur * (i + 0.4) / 6).toFixed(2));

const rows = [];
for (const t0 of windows) {
  const r = await page.evaluate(async ({ t0, fps }) => {
    const W = 64, H = 36;
    const sc = document.createElement('canvas'); sc.width = W; sc.height = H;
    const sg = sc.getContext('2d', { willReadFrequently: true });
    const src = document.querySelector('canvas');
    const grab = () => {
      sg.drawImage(src, 0, 0, W, H);
      const d = sg.getImageData(0, 0, W, H).data;
      const g = new Float32Array(W * H);
      for (let i = 0; i < W * H; i++) g[i] = 0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2];
      return g;
    };
    const diffs = [];
    window.render(t0); let prev = grab();
    for (let f = 1; f <= fps; f++) {
      window.render(t0 + f / fps);
      const cur = grab();
      let s = 0; for (let i = 0; i < cur.length; i++) s += Math.abs(cur[i] - prev[i]);
      diffs.push(s / cur.length); prev = cur;
    }
    return diffs;
  }, { t0, fps: FPS });
  const mean = r.reduce((a, b) => a + b, 0) / r.length;
  rows.push({ t0, mean, still: mean < 1.0 });
  console.log(`t=${String(t0).padStart(6)}s  幀差均值 ${mean.toFixed(2)}${mean < 1.0 ? '   ← 這秒算靜止' : ''}`);
}

const mean = rows.reduce((a, r) => a + r.mean, 0) / rows.length;
const stillRatio = rows.filter(r => r.still).length / rows.length;
console.log(`\n抽樣 ${rows.length} 秒   均值 ${mean.toFixed(2)}（基準 ≥2.38）   靜止 ${(stillRatio * 100).toFixed(0)}%（基準 ≤22%）`);
await browser.close(); closeServer();
process.exit(mean >= 2.38 && stillRatio <= 0.223 ? 0 : 1);
