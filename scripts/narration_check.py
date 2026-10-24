#!/usr/bin/env python3
"""旁白證據：把成片的聲音跑 Whisper，存逐字稿與字級時間戳，給 precheck 的故事閘門判。

  .venv/bin/python scripts/narration_check.py films/<片>

只產證據，不下判斷。判準（相似度門檻、開場空白、提問位置）寫在 precheck.py，
片子這邊改不到（防假成功：評分器移出受評者可及範圍，fix 10368）。
報告記下成片與旁白稿的 sha256，precheck 對不上就判舊報告，不靠檔案時間。

聽的是成片本身，不是旁白音檔：旁白有沒有真的混進成片、有沒有吃字，只有成片說了算。
"""
import hashlib
import json
import sys
from pathlib import Path

MODEL = "mlx-community/whisper-large-v3-turbo"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    film = Path(sys.argv[1]).resolve()
    master = film / f"{film.name}.mp4"
    script = film / "narration.md"
    if not master.is_file():
        raise SystemExit(f"找不到成片 {master}")

    import mlx_whisper

    # temperature 只給 0：關掉 Whisper 的重抽退路，同一支片每次逐字稿一樣，閘門才可重現。
    # hallucination_silence_threshold：純音樂段落不要幻聽出字（沒旁白的片要乾淨地判失敗）。
    r = mlx_whisper.transcribe(str(master), path_or_hf_repo=MODEL, language="zh",
                               word_timestamps=True, temperature=0.0,
                               condition_on_previous_text=False,
                               hallucination_silence_threshold=2.0)
    words = [{"w": w["word"], "t0": round(w["start"], 2), "t1": round(w["end"], 2)}
             for s in r["segments"] for w in s.get("words", [])]
    rep = {
        "master_sha": sha(master),
        "narration_sha": sha(script) if script.is_file() else None,
        "model": MODEL,
        "text": r["text"],
        "words": words,
    }
    out = film / "out" / "narration-report.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out}：{len(words)} 個字詞，首字 {words[0]['t0'] if words else '—'}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
