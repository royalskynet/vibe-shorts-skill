// 藏字檢查：把畫布上的字全部藏掉，看每張卡還剩多少畫面。字一藏就只剩底紙的卡，代表那張卡只在換字。
// 用法：node scripts/textless_check.mjs films/<name> [--size 1080x1920] [--min 0.03] [--warn 0.05] [--stills]
// 結果寫到 films/<name>/out/textless-report.json，precheck.py 讀它。退出碼 0＝通過。
//
// 出處：claude-motion SKILL.md「临时隐藏标题」與 direction.md §7（見 docs/RESEARCH-claude-motion.md）。
// 作法：攔截 fillText／strokeText 讓字不畫，取每張卡中段幀，標出「跟底色差很多的像素」。
// 底色取該幀亮度中位數，所以底紙顏色換了也不用改門檻。
// 每張卡都有的像素（空字幕底條、HUD 外框）先扣掉，只算這張卡自己畫的東西，否則外框會把每張卡都灌到過關。
// 兩段門檻：< --min 判失敗（只剩外框），< --warn 只警告（有畫面但很薄）。
// ponytail: 門檻只用 flt-11days 校準：卡 3（藏字後只剩刻度尺）0.016、卡 5（眼睛＋勾選格）0.060，取中間 0.03。做完第三支片拿實際觀感回頭調。
// ponytail: 只藏 canvas 字，DOM 字（<div> 疊在畫布上）不會被藏；我們的片全是 canvas 字。
import fs from 'fs'; import path from 'path';
const LIB = process.env.LIB || path.join(process.env.HOME, 'dev/lemo-opuscar');
const { openDemo, closeServer, takeSize } = await import(path.join(LIB, 'core/render/page.mjs'));

const args = process.argv.slice(2), { w: W, h: H } = takeSize(args.includes('--size') ? args : [...args, '--size', '1080x1920']);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? +args[i + 1] : d; };
const dir = args[0], MIN = opt('--min', 0.03), WARN = opt('--warn', 0.05), STILLS = args.includes('--stills');

const { browser, page } = await openDemo(dir, { w: W, h: H });
await page.evaluate(() => {
  const P = CanvasRenderingContext2D.prototype, fill = P.fillText, stroke = P.strokeText;
  P.fillText = function (...a) { if (!window.__NOTEXT) fill.apply(this, a); };
  P.strokeText = function (...a) { if (!window.__NOTEXT) stroke.apply(this, a); };
});
// 卡片切點：有 window.CUES（lemo 字幕契約）就用每條字幕的中點，沒有就每 4 秒取一格
const times = await page.evaluate(() => window.CUES?.length
  ? window.CUES.map(c => (c.t0 + c.t1) / 2)
  : Array.from({ length: Math.floor(window.DUR / 4) }, (_, i) => i * 4 + 2));

// 回傳兩個東西：ink 佔比，以及取樣點的遮罩字串（'1'＝有墨），之後拿來算跨卡交集
const ink = (t, notext) => page.evaluate(([t, notext]) => {
  window.__NOTEXT = notext; window.render(t); window.__NOTEXT = false;
  // 所有畫布照 DOM 疊放順序合成一張再讀：3D 片是 WebGL 底＋2D 字幕層，WebGL 畫布拿不到 2D context
  const cs = [...document.querySelectorAll('canvas')], big = cs.reduce((a, b) => b.width * b.height > a.width * a.height ? b : a);
  const c = document.createElement('canvas'); c.width = big.width; c.height = big.height;
  const x = c.getContext('2d'); for (const s of cs) x.drawImage(s, 0, 0, c.width, c.height);
  const d = x.getImageData(0, 0, c.width, c.height).data, L = [];
  for (let i = 0; i < d.length; i += 4 * 7) L.push(0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]);
  const med = L.slice().sort((a, b) => a - b)[L.length >> 1];
  return L.map(v => Math.abs(v - med) > 40 ? '1' : '0').join('');
}, [t, notext]);
const frac = m => m.split('1').length / m.length - 1 / m.length;

const masks = [];
for (const [i, t] of times.entries()) {
  masks.push({ t, full: await ink(t, false), bare: await ink(t, true) });
  if (STILLS) {
    fs.mkdirSync(path.join(dir, 'out', 'textless'), { recursive: true });
    await page.evaluate(t => { window.__NOTEXT = true; window.render(t); window.__NOTEXT = false; }, t);
    await page.screenshot({ path: path.join(dir, 'out', 'textless', `card${String(i + 1).padStart(2, '0')}.jpg`), type: 'jpeg', quality: 85 });
  }
}
// 外框＝每張卡藏字後都有墨的點。只有一張卡時沒有交集可言，不扣。
const n = masks[0]?.bare.length || 0, common = new Uint8Array(n);
if (masks.length > 1) for (let j = 0; j < n; j++) common[j] = masks.every(m => m.bare[j] === '1') ? 1 : 0;
const own = m => { let k = 0; for (let j = 0; j < n; j++) if (m[j] === '1' && !common[j]) k++; return k / n; };
const cards = masks.map((m, i) => {
  const v = own(m.bare);
  return { card: i + 1, t: +m.t.toFixed(2), textless: +v.toFixed(3), withText: +own(m.full).toFixed(3),
    level: v < MIN ? 'fail' : v < WARN ? 'warn' : 'ok' };
});
const chrome = +(common.reduce((a, b) => a + b, 0) / (n || 1)).toFixed(3);
await browser.close(); closeServer();

const ok = cards.length > 0 && cards.every(c => c.level !== 'fail');
fs.mkdirSync(path.join(dir, 'out'), { recursive: true });
fs.writeFileSync(path.join(dir, 'out', 'textless-report.json'), JSON.stringify({ ok, min: MIN, warn: WARN, chrome, size: `${W}x${H}`, cards }, null, 2));
const tag = { ok: 'OK  ', warn: 'WARN', fail: 'FAIL' };
for (const c of cards) console.log(`${tag[c.level]} 卡 ${String(c.card).padStart(2)}（${c.t}s） 藏字後 ${c.textless}  有字 ${c.withText}`);
console.log(`外框（每張卡都有）${chrome}，已扣除`);
console.log(ok ? `藏字後每張卡自己的畫面 ≥ ${MIN}` : `有卡藏字後自己的畫面 < ${MIN}，那張卡只靠字`);
process.exit(ok ? 0 : 1);
