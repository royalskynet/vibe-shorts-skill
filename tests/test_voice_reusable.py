#!/usr/bin/env python3
"""voice.reusable：換音色的句子要重念，不能沿用舊音檔。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
try:
    from voice import reusable
except ImportError as e:   # voice.py 頂層 import precheck／verify_tts，缺依賴時直接報
    raise SystemExit(f"import voice 失敗：{e}")

ok = {"sim": 0.95, "who": "clawd"}
assert reusable(ok, "甲", {"甲"})
assert not reusable(ok, "甲", set())                 # 這句改回主旁白 → 重念
assert not reusable({"sim": 0.95, "who": "host"}, "甲", {"甲"})
assert not reusable({"sim": 0.80, "who": "host"}, "甲", set())
assert not reusable(None, "甲", set())
assert reusable({"sim": 0.95}, "甲", set())           # 舊 lines.json 沒 who 欄＝主旁白
# 主旁白換範本（cast.json host）→ 舊 host 音檔不沿用，同範本才沿用
assert not reusable({"sim": 0.95, "who": "host"}, "乙", set(), host="host:m24k")
assert reusable({"sim": 0.95, "who": "host:m24k"}, "乙", set(), host="host:m24k")
# 語速倍率改了 → 舊音檔不沿用
import voice
voice.TEMPO = 1.2
assert not reusable({"sim": 0.95, "who": "host:m24k"}, "乙", set(), host="host:m24k")
assert reusable({"sim": 0.95, "who": "host:m24k@1.2"}, "乙", set(), host="host:m24k")
voice.TEMPO = 1.0
print("ok")
