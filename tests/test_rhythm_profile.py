#!/usr/bin/env python3
"""rhythm_check 基準切換的最小自檢。判準改錯這支要 fail。"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import rhythm_check as r  # noqa: E402

fails = []
v, m = r.PROFILES["vkv"], r.PROFILES["map"]
if (v[0], v[1], round(v[3], 3)) != (0.223, 4.0, round(3.97 * 0.6, 3)):
    fails.append(f"vkv 基準被改了：{v}")
if (m[0], m[1], m[3]) != (0.75, 8.0, 0.95):
    fails.append(f"map 基準要是使用者 2026-10-14 核准的 ≤75%、≤8 秒、≥0.95：{m}")
dl = r.PROFILES["dialogue"]
if (dl[0], dl[1], dl[3]) != (0.64, 9.0, 0.90):
    fails.append(f"dialogue 基準要是 10 支 IG 對談爆款全過的邊界 ≤64%、≤9 秒、≥0.90：{dl}")
ca = r.PROFILES["calm"]
if (ca[0], ca[1], ca[3]) != (1.0, 70.0, 0.20):
    fails.append(f"calm 基準要是使用者 2026-10-30 核准的 ≤100%、≤70 秒、≥0.20：{ca}")
with tempfile.TemporaryDirectory() as d:
    mp4 = Path(d) / "x.mp4"
    if r.profile_of(mp4) != "vkv":
        fails.append("沒有 rhythm-profile 時要用 vkv")
    (Path(d) / "rhythm-profile").write_text("map\n", encoding="utf-8")
    if r.profile_of(mp4) != "map":
        fails.append("rhythm-profile 寫 map 要用 map")
    (Path(d) / "rhythm-profile").write_text("loose\n", encoding="utf-8")
    sys.argv = ["rhythm_check.py", str(mp4)]
    if r.main() != 2:
        fails.append("不認得的基準要退出碼 2，不能默默過")

import precheck as pc  # noqa: E402

with tempfile.TemporaryDirectory() as d:
    if pc.shot_grid_exempt(Path(d)) is not None:
        fails.append("沒有 rhythm-profile 的片要比鏡頭格線")
    (Path(d) / "rhythm-profile").write_text("vkv\n", encoding="utf-8")
    if pc.shot_grid_exempt(Path(d)) is not None:
        fails.append("vkv 格式要比鏡頭格線")
    (Path(d) / "rhythm-profile").write_text("map\n", encoding="utf-8")
    if not pc.shot_grid_exempt(Path(d)):
        fails.append("map 格式要略過鏡頭格線")
    (Path(d) / "rhythm-profile").write_text("calm\n", encoding="utf-8")
    if not pc.shot_grid_exempt(Path(d)):
        fails.append("calm 格式要略過鏡頭格線")
    (Path(d) / "rhythm-profile").write_text("dialogue\n", encoding="utf-8")
    if not pc.shot_grid_exempt(Path(d)):
        fails.append("dialogue 格式要略過鏡頭格線")
    (Path(d) / "narration.md").write_text("## 鉤子\n它把專案取名最終版2。\n", encoding="utf-8")
    if not pc.facts_exempt(Path(d)):
        fails.append("dialogue 稿沒有三位數以上數字要免 facts.md")
    (Path(d) / "narration.md").write_text("## 鉤子\n2025 年每十萬人有 881 件。\n", encoding="utf-8")
    if pc.facts_exempt(Path(d)):
        fails.append("dialogue 稿有三位數以上數字仍要 facts.md")
    (Path(d) / "rhythm-profile").write_text("map\n", encoding="utf-8")
    (Path(d) / "narration.md").write_text("## 鉤子\n沒有數字。\n", encoding="utf-8")
    if pc.facts_exempt(Path(d)):
        fails.append("非 dialogue 格式不能免 facts.md")

tl = [{"t0": 0.3, "t1": 3.5}, {"t0": 3.9, "t1": 9.0}, {"t0": 9.4, "t1": 14.0}]
if pc.cut_boundary_problems([3.7, 9.2], tl):
    fails.append("切點在句間空檔內要過")
if pc.cut_boundary_problems([3.25, 9.6], tl):
    fails.append("切點離空檔 ≤0.3 秒要過")
if not pc.cut_boundary_problems([6.0], tl):
    fails.append("切點落在句子中間要擋")
if not pc.cut_boundary_problems([3.7, 11.5], tl):
    fails.append("有一刀落在句中就要擋")
if not pc.cut_boundary_problems([], tl):
    fails.append("偵測不到切點不能默默過")

if fails:
    print("FAIL", *fails, sep="\n  ")
    sys.exit(1)
print("OK rhythm_check 基準切換自檢")
