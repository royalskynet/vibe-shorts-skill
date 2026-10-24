#!/usr/bin/env python3
"""precheck「封面有字」判準的最小自檢。判準改錯這支要 fail。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import precheck as pc  # noqa: E402

HEAD = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"


def tsv(*words):
    return "\n".join([HEAD] + [f"5\t1\t1\t1\t1\t1\t0\t0\t10\t{h}\t{c}\t{t}" for h, c, t in words])


fails = []
if pc.cover_big_text(tsv((111, 94, "2,397"), (61, 97, "人")), 1920) != "2397":
    fails.append("110px 大標要算，61px 小字不算，逗號不算")
if pc.cover_big_text(tsv((28, 96, "法國動亂懶人包"), (46, 90, "人")), 1920):
    fails.append("角落小字（≤46px）不能算封面大字")
if pc.cover_big_text(tsv((111, 94, "A"), (108, 47, "三股")), 1920):
    fails.append("拉丁字母雜訊與低把握（conf<60）的字不能算")
if pc.cover_big_text(tsv((80, 70, "三股力量")), 1920) != "三股力量":
    fails.append("字高 ≥ 畫面 4%、conf ≥ 60 的中文字要算")
if pc.cover_big_text(HEAD + "\n4\t1\t1\t1\t1\t0\t0\t0\t10\t200\t-1\t", 1920):
    fails.append("空字列不能算")
if len(pc.cover_big_text(tsv((111, 94, "A1")), 1920)) >= pc.COVER_TEXT_MIN:
    fails.append("只有 1 個數字不夠當封面字")

if fails:
    print("FAIL", *fails, sep="\n  ")
    sys.exit(1)
print("OK 封面有字判準自檢")
