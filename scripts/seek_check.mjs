// 渲染守衛：在每個 worker 交界幀檢查「冷啟動畫」與「接續畫」是否位元組相同，並擋外部網路請求。
// 用法：node scripts/seek_check.mjs films/<name> [--fps 30] [--workers 6] [--size 1080x1920]
// 結果寫到 films/<name>/out/seek-report.json，precheck.py 讀它。退出碼 0＝通過。
//
// 為什麼要這支：lemo 的 video.mjs 開 N 個 worker，每個從自己的起始幀冷啟動。
// 頁面只要有任何依賴「上一幀」的狀態（累積粒子、沒固定種子的亂數），交界處就會跳格，
// 而 page.mjs 只擋 pageerror 和 404，抓不到這種錯。做法借自 claude-motion render.mjs 的重複尋幀檢查
// （見 docs/RESEARCH-claude-motion.md），改成對準 worker 交界。
import fs from 'fs'; import path from 'path';
const LIB = process.env.LIB || path.join(process.env.HOME, 'dev/lemo-opuscar');
const { openDemo, closeServer, takeSize } = await import(path.join(LIB, 'core/render/page.mjs'));

const args = process.argv.slice(2), { w: W, h: H } = takeSize(args.includes('--size') ? args : [...args, '--size', '1080x1920']);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? +args[i + 1] : d; };
const dir = args[0], FPS = opt('--fps', 30), WK = opt('--workers', 6);

const { browser, page } = await openDemo(dir, { w: W, h: H });
const external = [];
page.on('request', r => { const u = new URL(r.url()); if (!/^(127\.0\.0\.1|localhost)$/.test(u.hostname) && u.protocol.startsWith('http')) external.push(r.url()); });
// openDemo 回傳時頁面已載完，載入期間的請求聽不到，所以掛好監聽再重載一次
await page.reload(); await page.waitForFunction(() => window.READY === true, null, { timeout: 180000 });

const DUR = await page.evaluate(() => window.DUR), TOTAL = Math.round(DUR * FPS), per = Math.ceil(TOTAL / WK);
const shot = async f => { await page.evaluate(t => window.render(t), f / FPS); return page.screenshot({ type: 'png' }); };
const frames = [];
for (let w = 1; w < WK; w++) {
  const f = w * per; if (f >= TOTAL) break;
  const cold = await shot(f);           // 跳到交界幀直接畫：worker w 看到的樣子
  await shot(Math.min(TOTAL - 1, f + Math.round(FPS * 3)));   // 先跳走，避免頁面快取上一張
  for (let k = Math.max(0, f - 3); k < f; k++) await shot(k);  // 從前幾幀接續畫過來：worker w-1 看到的樣子
  const warm = await shot(f);
  frames.push({ frame: f, t: +(f / FPS).toFixed(3), identical: cold.equals(warm) });
}
// 鏡頭震動要對到事件表（docs/WRITING.md 規則 2）：頁面匯出 window.SHAKES 時，每個震動時間都要等於某筆 EV 的 t（差不到半幀）。
// 沒匯出就跳過不擋：舊片頁面改一行就得重渲染，不值得。
const { shakes, evts } = await page.evaluate(() => ({ shakes: window.SHAKES ?? null, evts: (window.EV || []).map(e => e.t) }));
const orphan = shakes ? shakes.filter(s => !evts.some(t => Math.abs(t - s) < 0.5 / FPS)) : [];
await browser.close(); closeServer();

const ok = frames.every(x => x.identical) && !external.length && !orphan.length;
const report = { ok, dur: DUR, fps: FPS, workers: WK, size: `${W}x${H}`, frames, external, shakes, orphanShakes: orphan };
fs.mkdirSync(path.join(dir, 'out'), { recursive: true });
fs.writeFileSync(path.join(dir, 'out', 'seek-report.json'), JSON.stringify(report, null, 2));
for (const x of frames) console.log(`${x.identical ? 'OK  ' : 'FAIL'} 交界幀 ${x.frame}（${x.t}s）`);
if (external.length) console.log(`FAIL 外部請求 ${external.length} 筆：${external.slice(0, 3).join(' ')}`);
console.log(shakes ? (orphan.length ? `FAIL 震動 ${orphan.join(', ')}s 對不到事件表` : `OK   震動 ${shakes.length} 個都對到事件表`) : 'SKIP 頁面沒匯出 window.SHAKES，震動對時沒檢查');
console.log(ok ? '尋幀一致' : '尋幀不一致、有外部請求或震動對不到事件');
process.exit(ok ? 0 : 1);
