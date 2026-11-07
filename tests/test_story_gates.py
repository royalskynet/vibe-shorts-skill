#!/usr/bin/env python3
"""故事閘門（precheck.py 13、14）的最小自檢。不跑 Whisper，用假聽寫。

好稿要過；每一種壞法各改一處，都要被擋。改壞判準時這支要 fail。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

import precheck as pc  # noqa: E402
import verify_tts as vt  # noqa: E402

fails = []
total = 0


def check(name, ok):
    global total
    total += 1
    if not ok:
        fails.append(name)


GOOD = """# 旁白稿
## 鉤子
滑 IG 的時候，你是不是總覺得大家都過得比你好？
## 機制
人緣好的人出現在很多人的名單上，被重複算了很多次。
## 轉折
但問題是，你等的那班公車，早就改了路線。
## 落點
你看到的別人，是被人多的地方挑過的樣本。
"""


def words_of(text, start=0.2, step=0.25):
    """一字一詞的假聽寫，時間從 start 起每字 step 秒。"""
    chars = pc.norm(text)
    return [{"w": c, "t0": round(start + i * step, 2), "t1": round(start + (i + 1) * step, 2)}
            for i, c in enumerate(chars)]


def secs(text):
    return pc.parse_narration(text)


good = secs(GOOD)
spoken = "".join(b for _, b in good)
rep = {"words": words_of(spoken)}
dur = rep["words"][-1]["t1"] + 2

# 好稿全過
check("好稿結構過", pc.story_problems(good) == [])
check("好稿聽寫過", pc.asr_problems(good, rep, dur) == [])

# 結構：缺段、順序、空段、鉤子太長、鉤子跟觀眾無關
check("單行超過 35 字擋", pc.story_problems(secs(GOOD.replace("## 機制\n", "## 機制\n" + "一" * 36 + "。\n"))) != [])
check("一行兩個句號擋", pc.story_problems(secs(GOOD.replace("## 機制\n", "## 機制\n好笑嗎？他當年也沒靠政變。\n"))) != [])
TAIL = GOOD + "## 收尾\n不是有選舉就叫民主，是我們一起守住規則，它才算數。\n"
check("落點後面多一段收尾擋", pc.story_problems(secs(TAIL)) != [])
check("轉折沒有連詞擋", pc.story_problems(secs(GOOD.replace("但問題是，", "這件事，"))) != [])
check("落點總結詞擋", any("總結詞" in x for x in pc.story_problems(secs(GOOD.replace("## 落點\n", "## 落點\n總之，這件事很重要。\n")))))
check("轉折用「再看」開頭擋", pc.story_problems(secs(GOOD.replace("但問題是，", "再看，"))) != [])
check("整篇沒有「你」也沒有問句擋", pc.story_problems(secs(GOOD.replace("你", "大家").replace("？", "。"))) != [])
check("缺落點擋", pc.story_problems(secs(GOOD.replace("## 落點", "## 其他"))) != [])
swapped = GOOD.replace("## 轉折", "## X").replace("## 落點", "## 轉折").replace("## X", "## 落點")
check("段落順序錯擋", pc.story_problems(secs(swapped)) != [])
check("空段擋", pc.story_problems(secs(GOOD.replace("你看到的別人，是被人多的地方挑過的樣本。", ""))) != [])
check("鉤子太長擋", pc.story_problems(secs(GOOD.replace(
    "滑 IG 的時候，你是不是總覺得大家都過得比你好？",
    "在這支影片裡我們要用一個很長很長很長很長的開場來介紹今天的主題。"))) != [])
check("鉤子無關擋", pc.story_problems(secs(GOOD.replace(
    "滑 IG 的時候，你是不是總覺得大家都過得比你好？", "1637 年的一個夏天。"))) != [])
check("對談格式免鉤子觀眾門", pc.story_problems(secs(GOOD.replace(
    "滑 IG 的時候，你是不是總覺得大家都過得比你好？", "1637 年的一個夏天。")), dialogue=True) == [])
check("對談格式鉤子太長仍擋", pc.story_problems(secs(GOOD.replace(
    "滑 IG 的時候，你是不是總覺得大家都過得比你好？",
    "在這支影片裡我們要用一個很長很長很長很長的開場來介紹今天的主題。")), dialogue=True) != [])

# 聽寫：沒旁白、吃字、開場空白
check("沒旁白擋", pc.asr_problems(good, {"words": []}, dur) != [])
half = rep["words"][: len(rep["words"]) // 2]
check("吃掉一半擋", pc.asr_problems(good, {"words": half}, dur) != [])
check("開場空白擋", pc.asr_problems(good, {"words": words_of(spoken, start=2.0)}, dur + 2) != [])
# 中段吃字：頭尾都在，只有相似度門擋得到
mid = [w for w in rep["words"] if not (5 <= w["t0"] < 18)]
check("中段吃字擋", pc.asr_problems(good, {"words": mid}, dur) != [])
# Whisper 中文常整段吐簡體：要轉繁後比對，不能因為字形不同就判失敗
simp_text = subprocess.run(["opencc", "-c", "t2s"], input="\n".join(w["w"] for w in rep["words"]),
                           capture_output=True, text=True, check=True).stdout.split("\n")
simp = {"words": [dict(w, w=s) for w, s in zip(rep["words"], simp_text)]}
check("簡體聽寫仍過", pc.asr_problems(good, simp, dur) == [])
# 片尾音樂上的 Whisper 幻聽不能害好片被擋
ghost = [{"w": c, "t0": dur, "t1": dur} for c in "请不吝点赞订阅转发打赏支持明镜与点点栏目"]
check("片尾幻聽仍過", pc.asr_problems(good, {"words": rep["words"] + ghost}, dur) == [])

# 聽寫正規化（10-30 pedestrian-hell）：數字寫法、台灣用字不算念錯；真的念錯的數字還是不同
check("聽寫阿拉伯數字＝稿上中文數字", pc.asr_norm("二〇二四年，全台有三百六十六個行人") == pc.asr_norm("2024年全臺有366個行人"))
check("簡體为里轉台灣用字", pc.to_trad("为里").strip() == "為裡")
check("念錯的數字不能算對", pc.asr_norm("三百六十六") != pc.asr_norm("336"))
check("念錯的年份不能算對", pc.asr_norm("二〇二二年") != pc.asr_norm("2023年"))
check("聽寫 97% ＝稿上百分之九十七", pc.asr_norm("有百分之九十七是百分之十的人") == pc.asr_norm("有97%是10%的人"))
check("念錯的百分比不能算對", pc.asr_norm("百分之九十七") != pc.asr_norm("79%"))
check("單句核稿 97% ＝百分之九十七", vt.norm("有百分之九十七是") == vt.norm("有97%是"))

# 爆款證據閘（12a）
V = "# 題\n\n爆款證據：YT｜56.3萬｜某片｜https://www.youtube.com/shorts/x\n"
check("爆款證據過", pc.viral_problems(V) == [])
check("1.7億過", pc.viral_problems(V.replace("56.3萬", "1.7億")) == [])
check("沒證據行擋", pc.viral_problems("# 題\n") != [])
check("沒連結擋", pc.viral_problems(V.replace("https://www.youtube.com/shorts/x", "")) != [])
check("不到10萬擋", pc.viral_problems(V.replace("56.3萬", "5萬")) != [])

# 提問只放說明欄（使用者 11-03 定）
import re as _re, tempfile as _tf
from pathlib import Path as _P
check("正片有提問段擋", any("說明欄" in x for x in pc.story_problems(secs(GOOD + "## 提問\n你在哪裡看到的？\n"))))
check("落點後多一段收尾擋", pc.story_problems(secs(GOOD + "## 收尾\n真正算數的是那一票。\n")) != [])
check("缺落點擋", pc.story_problems(secs(GOOD.replace("## 落點", "## 其他"))) != [])

# 稿子核准門（11-01）
import hashlib as _h, subprocess as _sp
with _tf.TemporaryDirectory() as d:
    f = _P(d); (f / "narration.md").write_text(GOOD, encoding="utf-8")
    check("沒核准檔擋", pc.approval_problems(f) != [])
    r = _sp.run([sys.executable, str(_P(__file__).resolve().parent.parent / "scripts" / "approve.py"), d, "稿子通過"], capture_output=True)
    check("approve.py 寫完過", r.returncode == 0 and pc.approval_problems(f) == [])
    (f / "narration.md").write_text(GOOD + "多一句。\n", encoding="utf-8")
    check("核准後改稿擋", pc.approval_problems(f) != [])
    sha = _h.sha256((f / "narration.md").read_bytes()).hexdigest()
    (f / "audit" / "approved.md").write_text(f"narration_sha: {sha}\n核准：\n", encoding="utf-8")
    check("沒寫使用者原話擋", pc.approval_problems(f) != [])
    r = _sp.run([sys.executable, str(_P(__file__).resolve().parent.parent / "scripts" / "approve.py"), d, "  "], capture_output=True)
    check("approve.py 空原話拒絕", r.returncode != 0)

if fails:
    print("FAIL\n  " + "\n  ".join(fails))
    sys.exit(1)
print(f"OK 故事閘門自檢 {total}/{total}")
