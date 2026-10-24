#!/usr/bin/env python3
"""precheck 目視自評門與禁止清單門的最小自檢：缺項、sha 不符、某項 7 分、空清單都要擋。"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from precheck import REVIEW_ITEMS, forbid_problems, review_problems  # noqa: E402

SHA = "a" * 64


def log(d, first, scores):
    p = Path(d) / "review_log.md"
    p.write_text(first + "\n" + "".join(f"- {k}：{v} — 看了第 3 格\n" for k, v in scores.items()),
                 encoding="utf-8")
    return p


good = {k: 9 for k in REVIEW_ITEMS}
with tempfile.TemporaryDirectory() as d:
    assert review_problems(Path(d) / "none.md", SHA)
    assert review_problems(log(d, f"video_sha: {SHA}", good), SHA) == []
    assert review_problems(log(d, f"video_sha: {SHA}", good), "b" * 64)
    assert review_problems(log(d, "sha: x", good), SHA)
    assert review_problems(log(d, f"video_sha: {SHA}", {**good, "構圖": 7}), SHA)
    missing = dict(good)
    missing.pop("聲畫同步")
    assert review_problems(log(d, f"video_sha: {SHA}", missing), SHA)
    p = Path(d) / "review_log.md"
    p.write_text(f"video_sha: {SHA}\n" + "".join(f"- {k}：9\n" for k in REVIEW_ITEMS), encoding="utf-8")
    assert review_problems(p, SHA), "沒寫理由要擋"

assert forbid_problems("# x\n## 禁止清單\n- 每句硬切\n## 分鏡\n") == []
assert forbid_problems("# x\n## 禁止清單\n\n## 分鏡\n- a\n")
assert forbid_problems("# x\n## 分鏡\n- a\n")
print("ok")
