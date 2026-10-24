#!/usr/bin/env python3
"""旁白配音：narration.md 逐句念成音檔，排出時間軸給頁面和 mix.py 用。

  .venv/bin/python scripts/voice.py films/<片>

一句一個檔，畫面才能跟著句子切。模型只載一次（單句走 CLI 每次要重載 1–2 分鐘）。
每句念完用 Whisper 聽回來比稿，相似度不到 SIM_MIN 就重念，最多 TRIES 次，留最好的一次；
最好的仍不到門檻就 exit 1，不讓吃字的配音默默進成片。

產出（都在 films/<片>/）：
  out/voice/NN.wav    每句一檔，48k 立體聲，頭尾靜音已去掉
  out/voice/lines.json  每句的稿、核稿相似度、在片中的起訖秒數
  timeline.js         window.TL＝同一份時間軸，給 index.html 用（頁面讀不到 out/ 的 JSON）
稿沒改過的句子不重念（比對 lines.json 裡的稿文）。
"""
import difflib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from precheck import parse_narration, sentences  # noqa: E402
from verify_tts import norm as asr_norm, to_simplified  # noqa: E402

TTS_MODEL = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16"
ASR_MODEL = "mlx-community/whisper-large-v3-turbo"
REF = ROOT / "assets/voice/d24k.wav"
REF_TEXT_FILE = ROOT / "assets/voice/script.txt"
# 主旁白音色可由片子的 cast.json 換掉：{"host": {"ref": "assets/voice/x24k.wav", "text": "assets/voice/x-script.txt"}}（路徑相對 repo 根）。
# 換了音色，lines.json 的 who 會帶範本檔名（host:x24k），舊音色念的檔就不會被沿用。
HOST_WHO = "host"
# 第二個聲音（深夜對談的 Clawd）。片子目錄有 cast.json 時，列在 "clawd" 的句子改用這個範本。
CLAWD_REF = ROOT / "assets/voice/clawd24k.wav"
CLAWD_REF_TEXT_FILE = ROOT / "assets/voice/clawd-script.txt"


def ref_text(wav, txt):
    """讀聲紋範本的逐字稿。缺檔就講清楚怎麼補，不要丟 traceback（這個 repo 不帶聲紋音檔）。"""
    for p in (wav, txt):
        if not p.is_file():
            raise SystemExit(
                f"找不到聲紋範本 {p}。錄一段 8～12 秒的單人乾聲，轉成 24kHz 單聲道 wav 放進 assets/voice/，"
                "逐字稿一字不差寫進同名 -script.txt，再在片子的 cast.json 指過去："
                '{"host": {"ref": "assets/voice/me24k.wav", "text": "assets/voice/me-script.txt"}}'
            )
    return txt.read_text(encoding="utf-8").replace("\n", "")


def voice_for(text, clawd_lines):
    """這句用哪個範本：(ref_audio, ref_text)。"""
    if text in clawd_lines:
        return str(CLAWD_REF), ref_text(CLAWD_REF, CLAWD_REF_TEXT_FILE)
    return str(REF), ref_text(REF, REF_TEXT_FILE)
SIM_MIN = 0.9      # 單句核稿門檻；precheck 對整片是 0.85，單句放鬆就會累積成整片不過
TRIES = 3
LEAD = 0.3         # 第一句開口前的空白；precheck 上限 0.5 秒
GAP_LINE = 0.25    # 同段句子之間
GAP_SECTION = 0.6  # 換段時多停一下，給畫面轉場
TAIL = 1.2         # 最後一句講完到片尾


TEMPO = 1.0  # pace.json 的 tempo：整片語速倍率（ffmpeg atempo，音高不變）


def who_of(text, clawd_lines, host=None):
    """lines.json 的 who：音色＋語速倍率。兩者任一改了，舊音檔就不沿用。"""
    who = "clawd" if text in clawd_lines else (host or HOST_WHO)
    return who if TEMPO == 1.0 else f"{who}@{TEMPO:g}"


def speed_up(wav):
    """atempo 加速（保留音高），在核稿前做，Whisper 聽的是成片會用的音。"""
    if TEMPO == 1.0:
        return
    tmp = wav.with_suffix(".tempo.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-filter:a", f"atempo={TEMPO}", str(tmp)], check=True)
    tmp.replace(wav)


def set_host(spec):
    """cast.json 的 host 段 → 換掉主旁白範本。"""
    global REF, REF_TEXT_FILE, HOST_WHO
    REF = ROOT / spec["ref"]
    REF_TEXT_FILE = ROOT / spec["text"]
    HOST_WHO = "host:" + REF.stem
    ref_text(REF, REF_TEXT_FILE)  # 缺檔當場炸，附補法，不要等 mlx 丟 traceback


def reusable(prev, text, clawd_lines, host=None):
    """舊音檔能不能沿用：稿文同、核稿過、而且音色沒換（10-20 換旁白音色時，沒改稿的句子沿用了舊音色）。"""
    return bool(prev) and prev["sim"] >= SIM_MIN and prev.get("who", "host") == who_of(text, clawd_lines, host)


def lines_of(sections):
    """[(段名, 句子)]，句子去掉頭尾空白，空句丟掉。"""
    return [(t, s.strip()) for t, body in sections for s in sentences(body) if s.strip()]


def layout(items, gap_line=GAP_LINE, gap_section=GAP_SECTION):
    """items＝[(段名, 句子, 秒數)] → 每句的起訖時間。換段的停頓比同段長。
    片子目錄有 pace.json（{"gap_line": 秒, "gap_section": 秒}）就用它的停頓，給一句一卡、要停留看圖的片。"""
    out, t, prev = [], LEAD, None
    for sec, text, dur in items:
        if prev is not None:
            t += gap_section if sec != prev else gap_line
        out.append({"section": sec, "text": text, "dur": round(dur, 3),
                    "t0": round(t, 3), "t1": round(t + dur, 3)})
        t += dur
        prev = sec
    return out, round(t + TAIL, 3)


def similarity(want, got):
    return difflib.SequenceMatcher(None, asr_norm(want), asr_norm(got), autojunk=False).ratio()


def duration(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True)
    return float(r.stdout)


def trim(src, dst):
    """去掉頭尾靜音，轉 48k 立體聲（mix.py 的取樣率）。"""
    cut = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af",
                    f"{cut},areverse,{cut},areverse", "-ar", "48000", "-ac", "2", str(dst)], check=True)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    heavy = Path.home() / ".local/bin/heavy"  # 全機重活閘（agent-tools/bin/heavy），10-14 事故
    if os.environ.get("HEAVY_HELD") != "1" and heavy.exists():
        os.execv(str(heavy), [str(heavy), "--", sys.executable, *sys.argv])
    film = Path(sys.argv[1]).resolve()
    vdir = film / "out" / "voice"
    vdir.mkdir(parents=True, exist_ok=True)
    items = lines_of(parse_narration((film / "narration.md").read_text(encoding="utf-8")))
    cast = film / "cast.json"
    global TEMPO
    pace = json.loads((film / "pace.json").read_text()) if (film / "pace.json").is_file() else {}
    TEMPO = float(pace.get("tempo", 1.0))
    cj = json.loads(cast.read_text(encoding="utf-8")) if cast.is_file() else {}
    clawd_lines = set(cj.get("clawd", []))
    if cj.get("host"):
        set_host(cj["host"])
    missing = clawd_lines - {t for _, t in items}
    if missing:
        print("cast.json 有句子對不上 narration.md 斷句：\n  " + "\n  ".join(sorted(missing)))
        return 1
    old = {}
    lj = vdir / "lines.json"
    if lj.is_file():
        old = {(x["text"], x["file"]): x for x in json.loads(lj.read_text(encoding="utf-8"))["lines"]}

    model = None
    import mlx_whisper
    rows, bad = [], []
    for i, (sec, text) in enumerate(items):
        name = f"{i + 1:02d}.wav"
        prev = old.get((text, name))
        if reusable(prev, text, clawd_lines) and (vdir / name).is_file():
            rows.append((sec, text, duration(vdir / name), prev["sim"], prev["heard"]))
            continue
        if model is None:
            from mlx_audio.tts.generate import generate_audio
            from mlx_audio.tts.utils import load_model
            model = load_model(model_path=TTS_MODEL)
        best = None
        for k in range(TRIES):
            raw = f"raw-{i + 1:02d}-{k}"
            # 送簡體：Qwen3-TTS 把繁體「詐」念成 jué（「反詐騙」→「反驅片」），簡體就念對
            ref_audio, ref_text = voice_for(text, clawd_lines)
            generate_audio(text=to_simplified(text), model=model, lang_code="Chinese", ref_audio=ref_audio,
                           ref_text=ref_text, output_path=str(vdir), file_prefix=raw,
                           join_audio=True, verbose=False)
            speed_up(vdir / f"{raw}.wav")
            heard = mlx_whisper.transcribe(str(vdir / f"{raw}.wav"), path_or_hf_repo=ASR_MODEL,
                                           language="zh", temperature=0.0)["text"]
            sim = similarity(text, heard)
            print(f"  {i + 1:02d} 第 {k + 1} 次 相似度 {sim:.2f}  {heard}")
            if best is None or sim > best[0]:
                best = (sim, raw, heard)
            if sim >= SIM_MIN:
                break
        trim(vdir / f"{best[1]}.wav", vdir / name)
        for f in vdir.glob(f"raw-{i + 1:02d}-*.wav"):
            f.unlink()
        if best[0] < SIM_MIN:
            bad.append(f"{i + 1:02d} {text}（最好 {best[0]:.2f}：{best[2]}）")
        rows.append((sec, text, duration(vdir / name), round(best[0], 3), best[2]))

    tl, dur = layout([(s, t, d) for s, t, d, _, _ in rows], pace.get("gap_line", GAP_LINE), pace.get("gap_section", GAP_SECTION))
    for x, (_, _, _, sim, heard), i in zip(tl, rows, range(len(rows))):
        x.update(file=f"{i + 1:02d}.wav", sim=sim, heard=heard,
                 who=who_of(x["text"], clawd_lines))
    lj.write_text(json.dumps({"dur": dur, "lines": tl}, ensure_ascii=False, indent=1), encoding="utf-8")
    js = {"dur": dur, "lines": [{k: x[k] for k in ("section", "text", "t0", "t1", "who")} for x in tl]}
    (film / "timeline.js").write_text(
        "// scripts/voice.py 產生，不要手改。改稿後重跑 voice.py。\nwindow.TL = "
        + json.dumps(js, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"{len(tl)} 句，片長 {dur}s → {lj.relative_to(film)}、timeline.js")
    if bad:
        print("核稿沒過（重念 %d 次仍不到 %.2f）：\n  " % (TRIES, SIM_MIN) + "\n  ".join(bad))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
