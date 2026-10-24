#!/usr/bin/env python3
"""深夜對談場景定格：女主（host-a）＋ Clawd Bot 在深夜房間的桌前對話，9:16。

格式依據 refs/VIRAL-LEDGER.md「人跟 AI 聊天的對話動畫」（2026-10-14）：夜景公寓、暖光、人＋Claude 吉祥物並肩、一句一卡字幕。
角色 SVG 是嵌進來的，id 加前綴（host-／clawd-）避免兩個角色的 #actor、#shadow 撞名；動畫層之後照前綴後的 id 驅動。

跑：python3 assets/mascot/scene/gen_night.py
出：assets/mascot/scene/night.svg
"""
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
MASCOT = HERE.parent
HOST_SVG = MASCOT / "host/host-a.svg"
CLAWD_SVG = MASCOT / "clawd-bot/clawd-bot.svg"

W, H = 1080, 1920


def embed(path, prefix, x, y, size):
    """把角色 SVG 變成一個巢狀 <svg>，所有 id 與 url(#...) 加前綴。"""
    src = path.read_text(encoding="utf-8")
    inner = re.search(r"<svg[^>]*>(.*)</svg>", src, re.S).group(1)
    vb = re.search(r'viewBox="([^"]+)"', src).group(1)
    inner = re.sub(r'id="([^"]+)"', lambda m: f'id="{prefix}{m.group(1)}"', inner)
    inner = re.sub(r"url\(#([^)]+)\)", lambda m: f"url(#{prefix}{m.group(1)})", inner)
    return f'<svg x="{x}" y="{y}" width="{size}" height="{size}" viewBox="{vb}" overflow="visible">{inner}</svg>'


def skyline():
    # 遠景城市：固定的樓高序列（不用亂數，重跑結果一樣）
    heights = [220, 300, 180, 360, 260, 200, 330, 240, 290, 170, 310, 230]
    out, x = [], 120
    for i, h in enumerate(heights):
        w = 60 + (i * 17) % 40
        out.append(f'<rect x="{x}" y="{900 - h}" width="{w}" height="{h}" fill="#232B3D"/>')
        for wy in range(900 - h + 20, 880, 34):
            for wx in range(x + 10, x + w - 10, 20):
                if (wx * 7 + wy * 3 + i) % 5 == 0:
                    out.append(f'<rect x="{wx}" y="{wy}" width="8" height="12" fill="#F6B966" opacity="0.7"/>')
        x += w + 6
    return "\n".join(out)


def build():
    host = embed(HOST_SVG, "host-", 20, 640, 700)
    clawd = embed(CLAWD_SVG, "clawd-", 600, 960, 380)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
  <defs>
    <linearGradient id="wall" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#1A1816"/><stop offset="1" stop-color="#2A2420"/>
    </linearGradient>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#0F1424"/><stop offset="1" stop-color="#1E2A44"/>
    </linearGradient>
    <radialGradient id="lamp" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#F6B966" stop-opacity="0.55"/>
      <stop offset="0.5" stop-color="#D97757" stop-opacity="0.18"/>
      <stop offset="1" stop-color="#D97757" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="screenGlow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#68E399" stop-opacity="0.25"/>
      <stop offset="1" stop-color="#68E399" stop-opacity="0"/>
    </radialGradient>
    <filter id="bokeh"><feGaussianBlur stdDeviation="6"/></filter>
    <clipPath id="pane"><rect x="100" y="200" width="880" height="720" rx="18"/></clipPath>
  </defs>

  <!-- 牆 -->
  <rect width="{W}" height="{H}" fill="url(#wall)"/>

  <!-- 窗：夜空、月、遠景城市（虛焦＝淺景深） -->
  <rect x="100" y="200" width="880" height="720" rx="18" fill="url(#sky)"/>
  <g filter="url(#bokeh)" clip-path="url(#pane)">
    <circle cx="820" cy="330" r="46" fill="#F4EAE2" opacity="0.85"/>
    {skyline()}
  </g>
  <rect x="100" y="200" width="880" height="720" rx="18" fill="none" stroke="#252422" stroke-width="14"/>
  <line x1="540" y1="200" x2="540" y2="920" stroke="#252422" stroke-width="10"/>

  <!-- 檯燈的暖光 -->
  <circle cx="990" cy="1020" r="520" fill="url(#lamp)"/>
  <g transform="translate(90,0)">
    <path d="M880,1250 L900,1060" stroke="#252422" stroke-width="10" stroke-linecap="round"/>
    <path d="M840,1060 L960,1060 L930,990 L870,990 Z" fill="#D97757" stroke="#252422" stroke-width="6" stroke-linejoin="round"/>
    <ellipse cx="880" cy="1252" rx="40" ry="10" fill="#252422"/>
  </g>

  <!-- 女主（桌子後面，半身） -->
  {host}

  <!-- 桌 -->
  <rect x="0" y="1250" width="{W}" height="90" fill="#4A3A30" stroke="#252422" stroke-width="6"/>
  <rect x="0" y="1340" width="{W}" height="580" fill="#201F1D"/>

  <!-- 筆電：螢幕背對鏡頭，透出終端機綠光 -->
  <circle cx="470" cy="1170" r="200" fill="url(#screenGlow)"/>
  <path d="M330,1250 L360,1110 L590,1110 L620,1250 Z" fill="#3A3632" stroke="#252422" stroke-width="6" stroke-linejoin="round"/>
  <path d="M460,1178 l10,-10 l10,10 l-10,10 Z" fill="#D97757"/>

  <!-- Clawd Bot（坐在桌上） -->
  {clawd}

  <!-- 一句一卡字幕：說話者名字用角色色（女主＝橘、Clawd＝LED 綠） -->
  <g>
    <rect x="90" y="1480" width="900" height="210" rx="34" fill="#141312" opacity="0.92" stroke="#3A3632" stroke-width="3"/>
    <text x="140" y="1546" font-family="PingFang TC" font-size="36" font-weight="600" fill="#F29172">她</text>
    <text x="140" y="1630" font-family="PingFang TC" font-size="60" font-weight="600" fill="#F4EAE2">你又忘了我們昨天聊過什麼？</text>
  </g>

  <!-- 時間戳：深夜感 -->
  <text x="540" y="130" text-anchor="middle" font-family="Menlo" font-size="40" fill="#F6B966" opacity="0.85">01:24 AM</text>
</svg>
"""


if __name__ == "__main__":
    out = HERE / "night.svg"
    out.write_text(build(), encoding="utf-8")
    print("寫出", out)
