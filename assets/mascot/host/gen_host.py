#!/usr/bin/env python3
"""主持人（2D 動漫少女）造型生成器 — 產出候選 SVG 給使用者挑。

為什麼用生成器不手寫三份 SVG：三款只差髮型與服裝，骨架（臉、眼、身）要一模一樣才比得出髮型差別；
骨架改一次三款同步，手寫三份會漂。選定一款之後，那一款的 SVG 就是正本，動畫層照 id 驅動。

跑：python3 assets/mascot/host/gen_host.py
出：assets/mascot/host/host-{a,b,c}.svg
"""
import pathlib

OUT = pathlib.Path(__file__).resolve().parent

# 色票：延用 Clawd Bot（assets/mascot/clawd-bot/README.md §2），讓主持人與吉祥物同一個世界觀
INK = "#252422"          # 描邊
HAIR_LIT = "#F29172"     # 髮亮部
HAIR = "#D97757"         # 髮主色（Claude 陶土橘）
HAIR_DARK = "#BC5C3E"    # 髮暗部
SKIN = "#F8E2D2"
SKIN_SHADE = "#EFCBB6"
EYE = "#3A3632"
LED = "#68E399"          # 眼高光／服裝點綴，呼應吉祥物面罩 LED
GOLD = "#F6B966"
BLUSH = "#FF856D"
CLOTH_DARK = "#2B2825"
LINE = 3.2

HEAD = """
  <!-- 頸與肩的交界先畫，避免描邊疊在臉上 -->
  <path id="neck" d="M-13,-18 L-13,6 Q0,14 13,6 L13,-18 Z" fill="%(skin_shade)s" stroke="%(ink)s" stroke-width="%(line)s" stroke-linejoin="round"/>
  <g id="head">
    <path id="face" d="M0,-96 C34,-96 50,-72 50,-44 C50,-12 30,10 0,10 C-30,10 -50,-12 -50,-44 C-50,-72 -34,-96 0,-96 Z"
          fill="%(skin)s" stroke="%(ink)s" stroke-width="%(line)s" stroke-linejoin="round"/>
    <!-- 耳 -->
    <path d="M-50,-50 C-58,-50 -60,-38 -52,-34" fill="%(skin)s" stroke="%(ink)s" stroke-width="2.4"/>
    <path d="M50,-50 C58,-50 60,-38 52,-34" fill="%(skin)s" stroke="%(ink)s" stroke-width="2.4"/>
    <g id="face-parts">
      <!-- 腮紅 -->
      <ellipse cx="-28" cy="-34" rx="9" ry="4.5" fill="%(blush)s" opacity="0.55"/>
      <ellipse cx="28" cy="-34" rx="9" ry="4.5" fill="%(blush)s" opacity="0.55"/>
      <!-- 眉 -->
      <g id="brows" stroke="%(hair_dark)s" stroke-width="3.4" stroke-linecap="round" fill="none">
        <path d="M-30,-58 Q-21,-62 -12,-59"/>
        <path d="M12,-59 Q21,-62 30,-58"/>
      </g>
      <!-- 睜眼（預設） -->
      <g id="eyes-open">
        <g>
          <ellipse cx="-21" cy="-44" rx="10" ry="12.5" fill="%(eye)s"/>
          <circle cx="-24" cy="-49" r="3.6" fill="#FFFFFF"/>
          <circle cx="-18" cy="-39" r="2.2" fill="%(led)s"/>
          <path d="M-32,-54 Q-21,-60 -10,-54" stroke="%(ink)s" stroke-width="3.6" fill="none" stroke-linecap="round"/>
        </g>
        <g>
          <ellipse cx="21" cy="-44" rx="10" ry="12.5" fill="%(eye)s"/>
          <circle cx="18" cy="-49" r="3.6" fill="#FFFFFF"/>
          <circle cx="24" cy="-39" r="2.2" fill="%(led)s"/>
          <path d="M10,-54 Q21,-60 32,-54" stroke="%(ink)s" stroke-width="3.6" fill="none" stroke-linecap="round"/>
        </g>
      </g>
      <!-- 半閉與閉眼：眨眼與思考用，動畫層切 display -->
      <g id="eyes-half" style="display:none" stroke="%(ink)s" stroke-width="3.6" fill="none" stroke-linecap="round">
        <path d="M-32,-48 Q-21,-54 -10,-48"/>
        <path d="M10,-48 Q21,-54 32,-48"/>
        <path d="M-30,-44 Q-21,-40 -12,-44" stroke="%(eye)s" stroke-width="5"/>
        <path d="M12,-44 Q21,-40 30,-44" stroke="%(eye)s" stroke-width="5"/>
      </g>
      <g id="eyes-closed" style="display:none" stroke="%(ink)s" stroke-width="3.6" fill="none" stroke-linecap="round">
        <path d="M-31,-45 Q-21,-38 -11,-45"/>
        <path d="M11,-45 Q21,-38 31,-45"/>
      </g>
      <!-- 鼻與嘴（嘴由動畫層換 d，對口型） -->
      <path d="M0,-34 L3,-30" stroke="%(ink)s" stroke-width="2.2" fill="none" stroke-linecap="round"/>
      <path id="mouth" d="M-7,-22 Q0,-16 7,-22" stroke="%(ink)s" stroke-width="3" fill="none" stroke-linecap="round"/>
    </g>
  </g>
"""

HAIR_BACK = {
    # 短鮑伯：後髮貼頭，外輪廓俐落
    "a": """<path d="M0,-108 C40,-108 62,-82 62,-46 C62,-18 56,2 52,14 L34,8 C40,-10 42,-28 40,-44 C30,-36 -30,-36 -40,-44 C-42,-28 -40,-10 -34,8 L-52,14 C-56,2 -62,-18 -62,-46 C-62,-82 -40,-108 0,-108 Z" fill="%(hair)s" stroke="%(ink)s" stroke-width="%(line)s" stroke-linejoin="round"/>""",
    # 長直髮：垂到胸線，主播感
    "b": """<path d="M0,-110 C42,-110 64,-84 64,-46 C64,-6 60,34 58,62 L36,62 C40,26 42,-10 40,-44 C30,-36 -30,-36 -40,-44 C-42,-10 -40,26 -36,62 L-58,62 C-60,34 -64,-6 -64,-46 C-64,-84 -42,-110 0,-110 Z" fill="%(hair)s" stroke="%(ink)s" stroke-width="%(line)s" stroke-linejoin="round"/>""",
    # 雙馬尾：後髮短，兩束另畫
    "c": """<path d="M0,-108 C40,-108 60,-84 60,-46 C60,-24 56,-8 52,2 L34,-4 C40,-18 42,-30 40,-44 C30,-36 -30,-36 -40,-44 C-42,-30 -40,-18 -34,-4 L-52,2 C-56,-8 -60,-24 -60,-46 C-60,-84 -40,-108 0,-108 Z" fill="%(hair)s" stroke="%(ink)s" stroke-width="%(line)s" stroke-linejoin="round"/>""",
}

# 會飄的那幾束：動畫層對 #hair-sway-* 做小角度擺動
HAIR_SWAY = {
    "a": """<g id="hair-sway-l" transform="translate(-52,-52)"><path d="M0,0 C-8,10 -10,22 -6,32 L6,28 C2,18 2,8 8,-2 Z" fill="%(hair_dark)s" stroke="%(ink)s" stroke-width="2.6" stroke-linejoin="round"/></g>
       <g id="hair-sway-r" transform="translate(52,-52)"><path d="M0,0 C8,10 10,22 6,32 L-6,28 C-2,18 -2,8 -8,-2 Z" fill="%(hair_dark)s" stroke="%(ink)s" stroke-width="2.6" stroke-linejoin="round"/></g>""",
    "b": """<g id="hair-sway-l" transform="translate(-58,-10)"><path d="M0,0 C-10,24 -10,52 -4,74 L10,70 C4,48 4,22 10,-2 Z" fill="%(hair_dark)s" stroke="%(ink)s" stroke-width="2.6" stroke-linejoin="round"/></g>
       <g id="hair-sway-r" transform="translate(58,-10)"><path d="M0,0 C10,24 10,52 4,74 L-10,70 C-4,48 -4,22 -10,-2 Z" fill="%(hair_dark)s" stroke="%(ink)s" stroke-width="2.6" stroke-linejoin="round"/></g>""",
    "c": """<g id="hair-sway-l" transform="translate(-58,-62)"><path d="M0,0 C-20,8 -32,28 -30,54 C-29,66 -22,74 -12,74 C-18,56 -14,30 2,14 Z" fill="%(hair)s" stroke="%(ink)s" stroke-width="%(line)s" stroke-linejoin="round"/><circle cx="-4" cy="4" r="7" fill="%(gold)s" stroke="%(ink)s" stroke-width="2.4"/></g>
       <g id="hair-sway-r" transform="translate(58,-62)"><path d="M0,0 C20,8 32,28 30,54 C29,66 22,74 12,74 C18,56 14,30 -2,14 Z" fill="%(hair)s" stroke="%(ink)s" stroke-width="%(line)s" stroke-linejoin="round"/><circle cx="4" cy="4" r="7" fill="%(gold)s" stroke="%(ink)s" stroke-width="2.4"/></g>""",
}

# 劉海
HAIR_FRONT = {
    "a": """<path d="M-44,-58 C-40,-92 -16,-104 0,-104 C18,-104 42,-92 44,-56 C34,-74 20,-82 6,-80 C10,-72 8,-64 4,-58 C-6,-74 -26,-76 -44,-58 Z" fill="%(hair_lit)s" stroke="%(ink)s" stroke-width="%(line)s" stroke-linejoin="round"/>""",
    "b": """<path d="M-46,-56 C-44,-94 -18,-106 0,-106 C20,-106 46,-94 46,-54 C38,-78 22,-86 2,-84 C-16,-86 -34,-76 -46,-56 Z" fill="%(hair_lit)s" stroke="%(ink)s" stroke-width="%(line)s" stroke-linejoin="round"/>
       <path d="M-2,-84 C-4,-72 -2,-62 2,-56" stroke="%(hair_dark)s" stroke-width="2.6" fill="none"/>""",
    "c": """<path d="M-44,-58 C-42,-94 -16,-106 0,-106 C20,-106 44,-92 44,-54 C36,-76 18,-86 0,-84 C4,-74 0,-64 -6,-58 C-14,-72 -30,-72 -44,-58 Z" fill="%(hair_lit)s" stroke="%(ink)s" stroke-width="%(line)s" stroke-linejoin="round"/>""",
}

BODY = {
    # 連帽衫：親切、科技感
    "a": """<g id="body">
    <path d="M-62,86 C-62,40 -34,16 0,16 C34,16 62,40 62,86 Z" fill="%(cloth)s" stroke="%(ink)s" stroke-width="%(line)s" stroke-linejoin="round"/>
    <path d="M-26,18 C-20,34 -10,42 0,42 C10,42 20,34 26,18 L18,14 C12,28 -12,28 -18,14 Z" fill="%(hair_dark)s" stroke="%(ink)s" stroke-width="2.6" stroke-linejoin="round"/>
    <path d="M-8,40 L-10,66" stroke="%(gold)s" stroke-width="3.4" stroke-linecap="round"/>
    <path d="M8,40 L10,66" stroke="%(gold)s" stroke-width="3.4" stroke-linecap="round"/>
    <circle cx="0" cy="62" r="5" fill="%(led)s" stroke="%(ink)s" stroke-width="2.2"/>
  </g>""",
    # 西裝外套：知識型主播
    "b": """<g id="body">
    <path d="M-64,86 C-64,42 -36,16 0,16 C36,16 64,42 64,86 Z" fill="%(cloth)s" stroke="%(ink)s" stroke-width="%(line)s" stroke-linejoin="round"/>
    <path d="M-30,20 L0,52 L30,20 L22,16 L0,38 L-22,16 Z" fill="#F4EAE2" stroke="%(ink)s" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M-30,20 L-14,86 L-2,86 L-10,46 Z" fill="%(hair)s" stroke="%(ink)s" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M30,20 L14,86 L2,86 L10,46 Z" fill="%(hair)s" stroke="%(ink)s" stroke-width="2.4" stroke-linejoin="round"/>
  </g>""",
    # 機甲外套：活潑，肩上留位置給 Clawd Bot
    "c": """<g id="body">
    <path d="M-64,86 C-64,42 -36,16 0,16 C36,16 64,42 64,86 Z" fill="%(cloth)s" stroke="%(ink)s" stroke-width="%(line)s" stroke-linejoin="round"/>
    <path d="M-64,70 C-62,42 -40,20 -24,18 L-20,86 L-64,86 Z" fill="%(hair)s" stroke="%(ink)s" stroke-width="2.6" stroke-linejoin="round"/>
    <path d="M64,70 C62,42 40,20 24,18 L20,86 L64,86 Z" fill="%(hair)s" stroke="%(ink)s" stroke-width="2.6" stroke-linejoin="round"/>
    <rect x="-10" y="34" width="20" height="26" rx="6" fill="%(screen)s" stroke="%(ink)s" stroke-width="2.4"/>
    <path d="M-5,47 L5,47" stroke="%(led)s" stroke-width="3" stroke-linecap="round"/>
  </g>""",
}

NAMES = {"a": "短鮑伯＋連帽衫", "b": "長直髮＋西裝外套", "c": "雙馬尾＋機甲外套"}


def build(key):
    c = dict(ink=INK, hair=HAIR, hair_lit=HAIR_LIT, hair_dark=HAIR_DARK, skin=SKIN,
             skin_shade=SKIN_SHADE, eye=EYE, led=LED, gold=GOLD, blush=BLUSH,
             cloth=CLOTH_DARK, screen="#201F1D", line=LINE)
    parts = "\n".join([
        HAIR_SWAY[key] % c,
        HAIR_BACK[key] % c,
        BODY[key] % c,
        HEAD % c,
        HAIR_FRONT[key] % c,
    ])
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="-120 -140 240 240" width="480" height="480" id="host-{key}-svg">
  <!-- 主持人候選 {key}：{NAMES[key]}。色票與 Clawd Bot 同一套（assets/mascot/clawd-bot/README.md §2） -->
  <ellipse id="shadow" cx="0" cy="92" rx="56" ry="8" fill="rgba(31,30,29,0.12)"/>
  <g id="actor">
{parts}
  </g>
  <g id="fx"></g>
</svg>
"""


if __name__ == "__main__":
    for key in NAMES:
        p = OUT / f"host-{key}.svg"
        p.write_text(build(key), encoding="utf-8")
        print("寫出", p)
