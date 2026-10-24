#!/usr/bin/env python3
"""voice.py 切句與排時間軸的最小自檢。判準改錯這支要 fail。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import voice as v  # noqa: E402

fails = []
items = v.lines_of([("鉤子", "你猜是哪裡？"), ("揭曉", "答案是新竹。比全國多三成。")])
if [t for _, t in items] != ["你猜是哪裡？", "答案是新竹。", "比全國多三成。"]:
    fails.append(f"切句錯：{items}")
tl, dur = v.layout([("鉤子", "a", 2.0), ("揭曉", "b", 1.0), ("揭曉", "c", 1.0)])
want_t0 = [v.LEAD, v.LEAD + 2.0 + v.GAP_SECTION, v.LEAD + 3.0 + v.GAP_SECTION + v.GAP_LINE]
if [x["t0"] for x in tl] != [round(t, 3) for t in want_t0]:
    fails.append(f"換段與同段停頓錯：{[x['t0'] for x in tl]} 應為 {want_t0}")
if dur != round(tl[-1]["t1"] + v.TAIL, 3):
    fails.append(f"片長錯：{dur}")
if v.LEAD >= 0.5:
    fails.append("開場空白要低於 precheck 的 0.5 秒上限")

from verify_tts import spell  # noqa: E402

want = {149: "一百四十九", 114: "一百一十四", 18: "十八", 21: "二十一", 105: "一百零五",
        1000: "一千", 1010: "一千零一十", 6: "六", 0: "零"}
got = {n: spell(n) for n in want}
if got != want:
    fails.append(f"數字讀法錯：{ {n: g for n, g in got.items() if g != want[n]} }")
if v.similarity("平均每一百四十九個人", "平均每149个人") < 0.99:
    fails.append("Whisper 吐阿拉伯數字時核稿要算念對")
if v.similarity("妳吃飯了嗎？", "你吃饭了吗?") < 0.99 or v.similarity("她說隨便，改得好", "他说随便,改的好") < 0.99:
    fails.append("同音代名詞／助詞（她他、妳你、得的）核稿要算念對")
if v.similarity("蛤，那個很醜欸。", "哈?那个很丑诶") < 0.99 or v.similarity("你有在算喔？", "你有在算哦") < 0.99:
    fails.append("句尾語氣詞（蛤哈、欸诶、喔哦）核稿要算念對")
if v.similarity("改了四十七次。", "改了四十八次") > 0.9:
    fails.append("一般字念錯不能被同音表放過")
if v.similarity("改得好嗎？", "搞得好吗?") > 0.9:
    fails.append("念錯的字（改→搞）核稿不能放過")

if fails:
    print("FAIL\n  " + "\n  ".join(fails))
    sys.exit(1)
print("OK voice 自檢 6/6")

# pace.json 覆寫停頓：同段句距要照傳入值，不是預設 GAP_LINE
tl2, _ = v.layout([("鉤子", "a", 2.0), ("揭曉", "b", 1.0), ("揭曉", "c", 1.0)], 1.0, 1.5)
assert abs(tl2[1]["t0"] - (v.LEAD + 2.0 + 1.5)) < 1e-6, tl2
assert abs(tl2[2]["t0"] - (tl2[1]["t1"] + 1.0)) < 1e-6, tl2

# 聲紋範本缺檔：要在 import 後才檢查，並給補法（公開版不帶聲紋音檔，eager read 會變 traceback）
from pathlib import Path  # noqa: E402

try:
    v.ref_text(Path("/nonexistent/x24k.wav"), Path("/nonexistent/x-script.txt"))
    raise AssertionError("缺聲紋範本應該 SystemExit")
except SystemExit as e:
    assert "cast.json" in str(e) and "24kHz" in str(e), str(e)
