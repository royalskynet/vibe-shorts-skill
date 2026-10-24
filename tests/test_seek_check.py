#!/usr/bin/env python3
"""seek_check.mjs 的最小自檢。用五個假頁面，不碰真片。

只測四件守衛漏掉就會產出壞片的事：
  1. 畫面只依賴 t 的頁面要過
  2. 畫面依賴上一幀狀態的頁面要擋（worker 交界會跳格）
  3. 頁面向外部網址發請求要擋（渲染結果會隨網路變）
  4. 匯出的 SHAKES 對不到 EV 時間要擋；對得到要過（聲音和震動才會一起移動）
"""
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="vibe-seek-test-"))

HEAD = '<!doctype html><meta charset="utf-8"><canvas id="c" width="64" height="64"></canvas><script>'
PAGES = {
    "pure": "const g=c.getContext('2d');window.DUR=4;"
            "window.render=t=>{g.fillStyle='#000';g.fillRect(0,0,64,64);g.fillStyle='#fff';g.fillRect(t*10%64,0,8,8)};",
    "stateful": "const g=c.getContext('2d');window.DUR=4;let n=0;"
                "window.render=t=>{n++;g.fillStyle='#000';g.fillRect(0,0,64,64);g.fillStyle='#fff';g.fillRect(n%64,0,8,8)};",
    "shake_ok": "const g=c.getContext('2d');window.DUR=4;window.EV=[{t:1.5,type:'stamp'}];"
                "window.SHAKES=window.EV.filter(e=>e.type==='stamp').map(e=>e.t);"
                "window.render=t=>{g.fillStyle='#000';g.fillRect(0,0,64,64)};",
    "shake_orphan": "const g=c.getContext('2d');window.DUR=4;window.EV=[{t:1.5,type:'stamp'}];window.SHAKES=[1.8];"
                    "window.render=t=>{g.fillStyle='#000';g.fillRect(0,0,64,64)};",
    "external": "const g=c.getContext('2d');window.DUR=4;new Image().src='http://example.com/x.png';"
                "window.render=t=>{g.fillStyle='#000';g.fillRect(0,0,64,64)};",
}

fails = []
for name, js in PAGES.items():
    d = TMP / name
    d.mkdir()
    (d / "index.html").write_text(HEAD + js + "window.READY=true;</script>")
    r = subprocess.run(["node", str(ROOT / "scripts/seek_check.mjs"), str(d),
                        "--fps", "10", "--workers", "2", "--size", "64x64"],
                       capture_output=True, text=True)
    want = 0 if name in ("pure", "shake_ok") else 1
    if r.returncode != want:
        fails.append(f"{name}: exit {r.returncode}，預期 {want}\n{r.stdout}{r.stderr}")

print("\n".join(fails) if fails else f"OK {len(PAGES)}/{len(PAGES)}")
raise SystemExit(1 if fails else 0)
