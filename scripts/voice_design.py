"""用 Qwen3-TTS VoiceDesign 生第二個角色的音色範本（一次性；之後 voice.py 用 Base 模型複製它，音色就鎖住）。

VoiceDesign 每次呼叫都會重抽一個新聲音，所以不能每句都用它念：生幾個候選，挑 Whisper 聽得最準的一個存成範本。
用法：.venv/bin/python scripts/voice_design.py <輸出wav> <稿.txt> "<聲音描述>" [候選數]
"""
import difflib
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_tts import norm, to_simplified  # noqa: E402

MODEL = "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16"
ASR = "mlx-community/whisper-large-v3-turbo"


def main():
    out, script, instruct = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    text = script.read_text(encoding="utf-8").replace("\n", "")
    from mlx_audio.tts.generate import generate_audio
    from mlx_audio.tts.utils import load_model
    import mlx_whisper
    model = load_model(model_path=MODEL)
    tmp = out.parent / f".{out.stem}-cand"
    tmp.mkdir(exist_ok=True)
    best = None
    for i in range(n):
        generate_audio(text=to_simplified(text), model=model, lang_code="Chinese", instruct=instruct,
                       output_path=str(tmp), file_prefix=f"c{i}", audio_format="wav", join_audio=True, verbose=False)
        wav = tmp / f"c{i}.wav"
        heard = mlx_whisper.transcribe(str(wav), path_or_hf_repo=ASR, language="zh")["text"]
        sim = difflib.SequenceMatcher(None, norm(text), norm(heard)).ratio()
        print(f"候選 {i}: 相似度 {sim:.3f}  聽到：{heard}")
        if best is None or sim > best[0]:
            best = (sim, wav)
    if best[0] < 0.9:
        print(f"最好的候選相似度只有 {best[0]:.3f}，低於 0.9，不存範本")
        return 1
    # voice.py 的範本是 24 kHz 單聲道（跟 d24k.wav 一樣）
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(best[1]), "-ac", "1", "-ar", "24000", str(out)], check=True)
    print(f"存成 {out}（候選相似度 {best[0]:.3f}）")
    shutil.rmtree(tmp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
