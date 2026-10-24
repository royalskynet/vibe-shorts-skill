#!/usr/bin/env python3
"""precheck 抄襲閘自檢：直譯照搬要擋、改寫要過、短口語與圈內梗不算。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from precheck import copy_problems  # noqa: E402

ORIG = """## A｜x
1. 女：Claude, the client said it's great.｜Claude，客戶說很棒。
2. C：I wrote 4,000 lines. You deleted 3,000.｜我寫了四千行，妳刪了三千行。
3. C：I say, you're absolutely right.｜我只會說「妳說得完全正確」。
"""

assert len(copy_problems("## 鉤子\nClaude，客戶說很棒。\n我寫了四千行，妳刪了三千行。\n", ORIG)) == 2
assert copy_problems("## 鉤子\n欸，老闆說 OK 了！\n「再改一下」，妳今天講了四十七次。\n", ORIG) == []
assert copy_problems("## 鉤子\n好啦。\n對，妳說得完全正確。\n", ORIG) == []
assert copy_problems("## 鉤子\n欸，老闆說 OK 了！\n", "沒有直譯句")
print("ok")
