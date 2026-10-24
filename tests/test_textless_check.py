#!/usr/bin/env python3
"""textless_check.mjs 的最小自檢。用兩個三張卡的假頁面，不碰真片。

只測兩件事，漏掉任一件這道檢查就沒意義：
  1. 每張卡都有自己的圖形 → 過（藏字不能把圖形也藏掉）
  2. 有一張卡只有字、只剩每張卡共用的外框 → 擋（外框要被扣掉，字要真的藏掉，否則都會誤過）
"""
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="vibe-textless-test-"))

# 200x200 畫布，三張卡各 2 秒。每張卡都有：米色底、底部深色外框條、一排實心方塊字。
# 方塊字每張卡放不同高度，不會被當成外框扣掉；所以字沒藏好的話，只有字的那張卡會誤過。
# draw[i] 是第 i 張卡自己的圖形；null 代表那張卡只有字。
PAGE = """<!doctype html><meta charset="utf-8"><canvas id="c" width="200" height="200"></canvas><script>
const g=c.getContext('2d'),DRAW=%s;
window.DUR=6;window.CUES=[0,1,2].map(i=>({t0:i*2,t1:i*2+2,text:'x'}));
window.render=t=>{const i=Math.min(2,Math.floor(t/2));
g.fillStyle='#e8dcc0';g.fillRect(0,0,200,200);g.fillStyle='#152';g.fillRect(10,170,180,20);
g.font='900 50px sans-serif';g.fillText('█████',10,[50,105,155][i]);
const d=DRAW[i];if(d){g.fillStyle='#c33';g.fillRect(d[0],d[1],d[2],d[3]);}};
window.READY=true;</script>"""
CASES = {
    "drawn": ("[[20,100,80,60],[100,90,80,70],[40,110,120,40]]", 0),
    "textonly": ("[[20,100,80,60],null,[40,110,120,40]]", 1),
}

fails = []
for name, (draw, want) in CASES.items():
    d = TMP / name
    d.mkdir()
    (d / "index.html").write_text(PAGE % draw)
    r = subprocess.run(["node", str(ROOT / "scripts/textless_check.mjs"), str(d), "--size", "200x200"],
                       capture_output=True, text=True)
    if r.returncode != want:
        fails.append(f"{name}: exit {r.returncode}，預期 {want}\n{r.stdout}{r.stderr}")

print("\n".join(fails) if fails else "OK 2/2")
raise SystemExit(1 if fails else 0)
