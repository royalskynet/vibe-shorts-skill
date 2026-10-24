#!/usr/bin/env python3
"""precheck 反方稽核門的最小自檢。判準改鬆這支要 fail。"""
import hashlib
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from precheck import audit_problems  # noqa: E402

PACK = """# Devil's Advocate Evidence Pack

Report: /x/audit/claims.md

## 爭點 1
FLAG: single-source
TARGET: 答案是新竹市。
OBJECTION: 某反證
EVIDENCE:
- URL: https://example.org/a
  DATE: 未標示
  EXCERPT: 原文摘錄
IMPACT: narrow

## 爭點 2
FLAG: inference
OBJECTION: NO_EVIDENCE_BACKED_OBJECTION
IMPACT: retain
"""


def film(pack=PACK, verdicts=None, narration="## 鉤子\n你猜？\n"):
    d = Path(tempfile.mkdtemp())
    (d / "narration.md").write_text(narration, encoding="utf-8")
    (d / "SOURCES.md").write_text("來源\n", encoding="utf-8")
    (d / "audit").mkdir()
    if pack is not None:
        (d / "audit" / "devils-advocate.md").write_text(pack, encoding="utf-8")
    if verdicts is not None:
        sha = lambda f: hashlib.sha256((d / f).read_bytes()).hexdigest()  # noqa: E731
        (d / "audit" / "verdicts.md").write_text(
            verdicts.format(n=sha("narration.md"), s=sha("SOURCES.md")), encoding="utf-8")
    return d


GOOD = ("engine=codex\nnarration_sha: {n}\nsources_sha: {s}\n\n## 爭點 1\nVERDICT: SPLIT\nREASON: 加限定語\n"
        "\n## 爭點 2\nVERDICT: PRO_WINS\nREASON: 無實據\n")
fails = []
if audit_problems(film(verdicts=GOOD)):
    fails.append(f"合格的稽核被擋：{audit_problems(film(verdicts=GOOD))}")
if not audit_problems(film(pack=None)):
    fails.append("沒有證據包要擋")
if not audit_problems(film()):
    fails.append("沒有裁決要擋")
if not audit_problems(film(verdicts=GOOD.split("\n## 爭點 2")[0])):
    fails.append("爭點沒裁完要擋")
if not audit_problems(film(pack=PACK.replace("  EXCERPT: 原文摘錄\n", ""), verdicts=GOOD)):
    fails.append("反證缺摘錄要擋")
if not audit_problems(film(verdicts=GOOD.replace("SPLIT", "MAYBE"))):
    fails.append("不認得的裁決要擋")
d = film(verdicts=GOOD)
(d / "narration.md").write_text("## 鉤子\n稽核後偷改？\n", encoding="utf-8")
if not audit_problems(d):
    fails.append("稽核後改稿要擋")

if fails:
    print("FAIL\n  " + "\n  ".join(fails))
    sys.exit(1)
print("OK 反方稽核門自檢 7/7")
