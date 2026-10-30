#!/usr/bin/env python3
"""節奏對照：量自己的成片，跟爆款逆向規範的實測數字比。

基準來自 refs/vkv/style-guide.md，那份規範逆向自 8 條抖音知識爆款、逐秒分析：
  相鄰幀亮度差異均值 3.97；靜止秒 29/130（22%）；靜止不得連續超過 4 秒。
原片是 1920x1080 橫屏、119–166 秒；我們的片是直式短片，所以只比「動不動」這三項，
解析度與長度不比（見 DECISIONS.md 的平台裁決）。

地圖格式（衛星地圖連續平移縮放，對標四處觀察、四方異聞）另有一組基準 map：
同一支腳本量 6 支頭部片（2026-10-14，277–457 萬播放），靜止秒 38.6–61.1%、
最長連續靜止 5–12 秒，6 支全過不了上面的 vkv 基準，可見這兩項跟此格式的流量無關。
map 基準取 靜止秒 ≤ 62%、最長連續靜止 ≤ 8 秒（使用者 2026-10-14 核准）。
同日第二次放寬（使用者目視 scam-map 衛星版後核准）：map 靜止秒 ≤ 75%、亮度差異均值 ≥ 0.95。
這組數字低於 6 支頭部片全部（亮度 1.72–2.74），依據是使用者目視，不是對標實測；
原因推測是我們海面為深色平色、縮到 64x36 後鏡頭移動的亮度變化小，證據不足，待觀眾數據回來再校。

資料卡格式（平塗、不閃、換卡直切、每句後停 1 秒）另有一組基準 card：
dating-bill v3 實測靜止秒 83.6%、最長連續靜止 8 秒、亮度差異均值 0.57，
使用者 2026-10-15 看過 YT 私人版後核准；同日試過每逗號跳切加快（v4，靜止 39%），使用者看了嫌閃爍跳躍，退回 v3。
依據是使用者目視，沒有對標實測，待觀眾數據回來再校。

對談格式（深夜對談：兩個角色一句一鏡正反打，對標 IG @agentmorphy／@canwebuildthis／@agentcinder）另有一組基準 dialogue：
同一支腳本量 10 支同格式爆款（2026-10-17，IG 讚數 0.86–6.7 萬），亮度差異均值 0.93–2.49、
靜止秒 0–63.6%、最長連續靜止 0–9 秒，10 支全過不了 vkv。dialogue 取 10 支全過的邊界：
靜止秒 ≤ 64%、最長連續靜止 ≤ 9 秒、亮度差異均值 ≥ 0.90（使用者 2026-10-17 核准照此訂）。

靜態科普格式（奶油底或深底固定舞台、換卡原地交叉淡化、不滑入不硬切、不放換卡音效）另有一組基準 calm：
對標 IG @boundless__explorer「對方不是你想的那樣」第 3 集 https://www.instagram.com/reel/DemDuhNk1ZR/（161 讚、無播放數）
用同一支腳本量：亮度差異均值 0.21、靜止秒 100%、最長連續靜止 67 秒（全片 0 次硬切）。
pedestrian-hell 第三版實測 0.31／97.6%／59 秒，使用者 2026-10-30 看過 YT 私人版後核准。
calm 只剩亮度下限 ≥ 0.20 真的會擋（抓整片凍住的壞渲染）；靜止比例與最長靜止實質不管，
因為這個格式本來就靠旁白撐、畫面少動（使用者 10-30：轉場太多太頻繁、滑入眼睛不舒服）。
ponytail: 只有 1 支對標＋1 支自製，待第二支 calm 片的觀眾數據回來再校。

成片同目錄有 rhythm-profile 檔（內容一行，例如 map）就用那組基準，沒有就用 vkv。

用法：scripts/rhythm_check.py <成片.mp4>
退出碼 0 = 三項全過，1 = 有項目沒過，2 = 讀不到畫面或不認得的基準。
"""
import subprocess
import sys
from pathlib import Path

W, H = 64, 36                 # 縮到這個尺寸再比，量的是整體畫面變化，不是細節
STILL_THRESHOLD = 1.0         # 一秒內平均幀差低於這個值就算靜止秒
BENCH_MEAN = 3.97             # 爆款實測：相鄰幀亮度差異均值
# 基準名 → (靜止秒比例上限, 最長連續靜止秒數上限, 出處, 亮度差異均值下限)
PROFILES = {
    "vkv": (0.223, 4.0, "爆款 29/130", BENCH_MEAN * 0.6),   # refs/vkv/style-guide.md
    "map": (0.75, 8.0, "使用者目視核准", 0.95),            # 見檔頭
    "card": (0.85, 8.0, "使用者目視核准", 0.5),            # 見檔頭
    "dialogue": (0.64, 9.0, "IG 對談爆款 10 支全過", 0.90),  # 見檔頭
    "calm": (1.0, 70.0, "對標 DemDuhNk1ZR＋使用者目視核准", 0.20),  # 見檔頭
}


def profile_of(path: Path) -> str:
    f = path.resolve().parent / "rhythm-profile"
    return f.read_text(encoding="utf-8").strip() if f.is_file() else "vkv"


def frame_diffs(path: Path):
    """回傳 (fps, 每對相鄰幀的平均亮度差)。"""
    fps = float(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True).stdout.strip().split("/")[0])
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path),
         "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
        capture_output=True, check=True).stdout
    n = W * H
    frames = [raw[i:i + n] for i in range(0, len(raw) - n + 1, n)]
    diffs = []
    for a, b in zip(frames, frames[1:]):
        diffs.append(sum(abs(x - y) for x, y in zip(a, b)) / n)
    return fps, diffs


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = Path(sys.argv[1])
    prof = profile_of(path)
    if prof not in PROFILES:
        print(f"不認得的基準 {prof!r}，只能是 {sorted(PROFILES)}")
        return 2
    still_max, run_max, src, mean_min = PROFILES[prof]
    fps, diffs = frame_diffs(path)
    if not diffs:
        print("讀不到畫面")
        return 2

    per_sec = []
    step = int(round(fps))
    for i in range(0, len(diffs), step):
        chunk = diffs[i:i + step]
        per_sec.append(sum(chunk) / len(chunk))

    mean = sum(diffs) / len(diffs)
    still = [s for s in per_sec if s < STILL_THRESHOLD]
    ratio = len(still) / len(per_sec)

    run = best = 0
    for s in per_sec:
        run = run + 1 if s < STILL_THRESHOLD else 0
        best = max(best, run)

    rows = [
        ("相鄰幀亮度差異均值", f"{mean:.2f}", f"≥ {mean_min:.2f}（爆款 {BENCH_MEAN}）",
         mean >= mean_min),
        ("靜止秒比例", f"{ratio:.1%}", f"≤ {still_max:.1%}（{src}）", ratio <= still_max),
        ("最長連續靜止", f"{best:.0f}s", f"≤ {run_max:.0f}s", best <= run_max),
    ]
    print(f"{path.name}  {len(per_sec)}s  {fps:.0f}fps  基準 {prof}")
    bad = 0
    for name, got, want, ok in rows:
        print(f"  {'OK ' if ok else 'BAD'} {name:<12} {got:>8}   基準 {want}")
        bad += not ok
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
