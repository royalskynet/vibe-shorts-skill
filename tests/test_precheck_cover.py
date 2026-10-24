#!/usr/bin/env python3
"""precheck 封面幀門的最小自檢：黑起頭的片要擋，亮起頭的片要過。"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from precheck import COVER_LUMA_MIN, first_frame_luma  # noqa: E402


def make(path, first, then):
    # 前 0.2s 一個顏色、之後另一個顏色，模擬「從黑淡入」與「直接開場」
    subprocess.run(["ffmpeg", "-v", "error", "-y",
                    "-f", "lavfi", "-i", f"color={first}:s=64x64:d=0.2:r=30",
                    "-f", "lavfi", "-i", f"color={then}:s=64x64:d=0.5:r=30",
                    "-filter_complex", "concat=n=2:v=1", "-pix_fmt", "yuv420p", path], check=True)


with tempfile.TemporaryDirectory() as d:
    black, lit = os.path.join(d, "black.mp4"), os.path.join(d, "lit.mp4")
    make(black, "black", "gray")
    make(lit, "0x3050a0", "black")
    assert first_frame_luma(black) < COVER_LUMA_MIN, first_frame_luma(black)
    assert first_frame_luma(lit) >= COVER_LUMA_MIN, first_frame_luma(lit)
print("ok")
