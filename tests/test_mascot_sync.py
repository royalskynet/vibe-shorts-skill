#!/usr/bin/env python3
"""片子目錄裡的 Clawd Bot 副本要跟 assets/mascot 正本一致。

片子只能讀自己目錄裡的檔（core/render/serve.mjs 的掛載根），所以角色是 cp 進去的；
正本改了而片子沒重跑 scripts/mascot_install.sh，就會出現兩個版本的角色，這支測試擋住它。
"""
import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = {
    "clawd-bot-shot.mjs": ROOT / "assets/mascot/clawd-bot-shot.mjs",
    "clawd-bot.svg": ROOT / "assets/mascot/clawd-bot/clawd-bot.svg",
}


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    for name, p in SRC.items():
        if not p.exists():
            print(f"FAIL 正本不見了：{p}")
            return 1

    bad = []
    for film in sorted((ROOT / "films").glob("*/mascot")):
        for name, src in SRC.items():
            copy = film / name
            if not copy.exists():
                bad.append(f"{copy} 不存在（跑 scripts/mascot_install.sh {film.parent.relative_to(ROOT)}）")
            elif digest(copy) != digest(src):
                bad.append(f"{copy.relative_to(ROOT)} 與正本不一致（重跑 scripts/mascot_install.sh {film.parent.relative_to(ROOT)}）")

    if bad:
        print("FAIL 吉祥物副本沒同步：")
        for b in bad:
            print("  -", b)
        return 1
    print("ok test_mascot_sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
