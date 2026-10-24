#!/usr/bin/env python3
"""核稿：把生成的旁白聽回來，跟原稿逐字比，防吃字。

用法：scripts/verify_tts.py <音檔> [稿檔]   稿檔預設 assets/voice/script.txt
退出碼 0 = 一字不差，1 = 有落差（印出缺哪些字）。

比對前先正規化：去標點與空白，再用 opencc t2s 把兩邊都壓成簡體——
Whisper 的中文輸出是簡體且不帶標點，不壓就會整段對不上。
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = "mlx-community/whisper-large-v3-turbo"
PUNCT = re.compile(r"[\s，。！？、；：…—－「」『』（）()《》,.!?;:\"'…　]+")


def to_simplified(s: str) -> str:
    """有 opencc 就用，沒有就原樣回傳（只影響繁簡混比的敏感度）。"""
    try:
        return subprocess.run(
            ["opencc", "-c", "t2s"], input=s, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return s


DIGIT = "零一二三四五六七八九"


def spell(n: int) -> str:
    """阿拉伯數字轉中文讀法：149→一百四十九、114→一百一十四、18→十八、105→一百零五。
    ponytail: 只做 0–9999，更大的原樣留著（稿裡的大數都寫成「十五萬六千」這種，Whisper 只會吐小段數字）。"""
    if not 0 <= n <= 9999:
        return str(n)
    if n == 0:
        return "零"
    out, zero = "", False
    for unit, v in (("千", 1000), ("百", 100), ("十", 10), ("", 1)):
        d, n = divmod(n, v)
        if d:
            if zero:
                out += "零"
            out += DIGIT[d] + unit
            zero = False
        elif out:
            zero = True
    return out[1:] if out.startswith("一十") else out


# 同音字：聲音裡沒有差別，Whisper 只能猜字，猜哪個都不代表念錯。比對前歸成同一個字。
# 2026-10-15 clawd-notes 實跑：「她」聽成「他」、「妳」聽成「你」、「改得好」聽成「改的好」，三句重念 3 次都卡 0.75–0.88。
# 2026-10-16 你說得完全正確稿：句尾語氣詞「啊／喔／蛤／欸」被寫成「呀／哦／哈／诶」，四句重念 3 次都卡 0.80–0.89。
# ponytail: 只收代名詞、結構助詞、語氣詞；之後撞到別的同音字再補，不要收一般字（會把真的念錯放過）。
HOMOPHONE = str.maketrans({"她": "他", "它": "他", "牠": "他", "妳": "你", "得": "的", "地": "的",
                           "呀": "啊", "哦": "喔", "噢": "喔", "哈": "蛤", "诶": "欸", "耶": "欸"})


def norm(s: str) -> str:
    """Whisper 會把念出來的「一百四十九」寫成「149」，比對前轉回中文讀法，不然念對也算錯。"""
    s = re.sub(r"\d+", lambda m: spell(int(m.group())), s)
    return to_simplified(PUNCT.sub("", s)).translate(HOMOPHONE)


def transcribe(audio: Path) -> str:
    import mlx_whisper

    return mlx_whisper.transcribe(
        str(audio), path_or_hf_repo=MODEL, language="zh"
    )["text"]


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    audio = Path(sys.argv[1])
    script = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "assets/voice/script.txt"

    want, got = norm(script.read_text(encoding="utf-8")), norm(transcribe(audio))
    print(f"稿: {want}")
    print(f"聽: {got}")

    if want == got:
        print(f"✅ {audio.name} 一字不差（{len(want)} 字）")
        return 0

    # 逐字對齊找缺字：走一遍 want，got 裡接不上的就是漏掉或念錯的
    missing, j = [], 0
    for ch in want:
        if j < len(got) and got[j] == ch:
            j += 1
        else:
            missing.append(ch)
    print(f"❌ {audio.name} 有落差：稿 {len(want)} 字、聽到 {len(got)} 字")
    print(f"   對不上的字：{''.join(missing) or '(順序不同，不是缺字)'}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
