"""你說得完全正確 — 雙人對白＋深夜 lo-fi 配樂＋音效。
旁白：out/voice/lines.json（scripts/voice.py 產生，每句在片中的 t0）。
音效：events.json（頁面匯出的 window.EV）。
配樂讓位給旁白：旁白有聲的地方配樂壓低 DUCK_DB（側鏈閃避），句與句之間再浮回來。
用法：LIB=~/dev/lemo-opuscar $LIB/.venv/bin/python mix.py
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.environ.get('LIB') or os.path.expanduser('~/dev/lemo-opuscar')
sys.path.insert(0, os.path.join(LIB, 'core', 'audio'))
from sfx import SR, add, bp, lp, hp, noise, limit, click, clack, thump, whoosh, pop, t_, env_exp  # noqa: E402
import soundfile as sf  # noqa: E402

EV = json.load(open(os.path.join(HERE, 'events.json'), encoding='utf-8'))
LINES = json.load(open(os.path.join(HERE, 'out', 'voice', 'lines.json'), encoding='utf-8'))
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)

DUR = EV['dur']
N = int(DUR * SR)
music = np.zeros((N, 2), np.float32)
fx = np.zeros((N, 2), np.float32)
voice = np.zeros((N, 2), np.float32)

BPM = 78.0           # 深夜 lo-fi：慢、無重鼓
BEAT = 60.0 / BPM
BAR = BEAT * 4
VOICE_GAIN = 1.0
MUSIC_GAIN = 0.5
DUCK_DB = -11.0      # 旁白講話時配樂壓多少


def kick(v=1.0):
    d = 0.28
    tt = t_(d)
    f = 110 * np.exp(-tt / 0.03) + 46
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(d, 0.08) * v


def hat(v=1.0, d=0.05):
    return hp(noise(d), 7500) * env_exp(d, 0.014) * v * 0.35


def bass(d, f, v=1.0):
    tt = t_(d)
    x = np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2 * tt)
    e = np.minimum(1, tt / 0.008) * env_exp(d, d * 0.5)
    return lp(x, 600) * e * v * 0.5


def pad(d, freqs, v=1.0):
    tt = t_(d)
    x = sum(np.sin(2 * np.pi * f * tt + i * 0.7) * (0.85 ** i) for i, f in enumerate(freqs))
    e = np.minimum(1, tt / 0.5) * np.minimum(1, (d - tt) / 0.6)
    return lp(x, 1500) * e * v * 0.2


def pluck(d, f, v=1.0):
    tt = t_(d)
    x = np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * f * 3.99 * tt) * np.exp(-tt / 0.05)
    return x * env_exp(d, 0.18) * v * 0.45


def bell(f, v=1.0):
    d = 1.4
    tt = t_(d)
    x = np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * f * 2.76 * tt)
    return x * env_exp(d, 0.4) * v * 0.4


# —— 1. 配樂：Fmaj7–Em7–Dm7–Cmaj7 循環，軟墊＋輕低音＋刷音 hat，不打大鼓（對談片要安靜）——
F2, E2, D2, C2 = 87.3, 82.4, 73.4, 65.4
A4, C5, E5, G4, B4, D5, F4 = 440.0, 523.3, 659.3, 392.0, 493.9, 587.3, 349.2
PROG = [(F2, [F4, A4, C5, E5]), (E2, [G4, B4, D5, E5]), (D2, [F4, A4, C5, D5]), (C2, [G4, B4, E5, C5])]
for b in range(int(DUR / BAR) + 1):
    t0 = b * BAR
    root, notes = PROG[b % 4]
    add(music, lp(pad(BAR, notes, 0.6), 1100), t0, pan=0.05)
    for i in (0, 5):
        add(music, bass(BEAT * 1.4, root, 0.55), t0 + i * BEAT / 2, pan=-0.06)
    if b >= 1:
        for i in range(8):
            add(music, hat(0.14 if i % 2 else 0.2, 0.04), t0 + i * BEAT / 2 + (0.03 if i % 2 else 0), pan=0.18)
        add(music, kick(0.18), t0)
    if b % 2 == 1:
        for i, n in enumerate([E5, C5, A4]):
            add(music, lp(pluck(BEAT, n, 0.22), 2500), t0 + 2 * BEAT + i * BEAT * 0.5, pan=-0.14)

# —— 2. 音效 ——
for e in EV['ev']:
    t, k = float(e['t']), e['type']
    if k == 'cut':
        pass                                # 正反打切鏡不配聲，對談片切得密，配聲會吵
    elif k == 'blip':                       # Claude 表情變化：兩聲短電子音
        add(fx, pop(0.16), t)
        add(fx, lp(pluck(0.25, 1318.5, 0.25), 4000), t + 0.07, pan=-0.1)
    elif k == 'paper':                      # 便利貼
        add(fx, lp(whoosh(0.18, 0.18), 3000), t)
        add(fx, click(1.0, 0.2), t + 0.12)
    elif k == 'click':                      # 螢幕變化（錯誤條、清空）
        add(fx, click(1.0, 0.2), t)
    elif k == 'chime':
        for i, n in enumerate([C5, E5, A4 * 2]):
            add(fx, bell(n, 0.32 - i * 0.06), t + i * 0.18, pan=0.1 * i)
    elif k == 'bed':
        pass
    else:
        raise SystemExit(f'未知的事件類型 {k}（頁面 EV 跟 mix.py 對不上）')

# —— 3. 旁白 ——
for ln in LINES['lines']:
    x, sr = sf.read(os.path.join(HERE, 'out', 'voice', ln['file']), dtype='float32', always_2d=True)
    if sr != SR:
        raise SystemExit(f'{ln["file"]} 取樣率 {sr}，要 {SR}（重跑 scripts/voice.py）')
    s = int(ln['t0'] * SR)
    e = min(N, s + len(x))
    voice[s:e] += x[:e - s, :2] * VOICE_GAIN

# 側鏈閃避：旁白包絡（10ms 起、250ms 放）→ 配樂增益
env = np.abs(voice).max(axis=1)
att, rel = np.exp(-1 / (0.01 * SR)), np.exp(-1 / (0.25 * SR))
follow = np.zeros(N, np.float32)
lvl = 0.0
for i in range(0, N, 64):                   # 每 64 個樣本算一次，夠細且快
    v = env[i:i + 64].max()
    lvl = v + (lvl - v) * (att ** 64 if v > lvl else rel ** 64)
    follow[i:i + 64] = lvl
duck = 10 ** (DUCK_DB / 20 * np.clip(follow / 0.05, 0, 1))
music *= (MUSIC_GAIN * duck)[:, None]
# 提問句講完配樂就收掉：片尾 1 秒多的純配樂會讓 Whisper 幻聽出「明镜与点点栏目」，旁白核對判片尾不是提問句。
END = int(LINES['lines'][-1]['t1'] * SR)
music[END:] *= np.linspace(1, 0, N - END)[:, None] ** 3

buf = music + fx * 0.8 + voice


def fade(x, a, b):
    y = x.copy()
    ia, ib = int(a * SR), int(b * SR)
    y[:ia] *= np.linspace(0, 1, ia)
    y[len(y) - ib:] *= np.linspace(1, 0, ib)
    return y


for c in range(2):
    buf[:, c] = fade(buf[:, c], 0.02, 0.8)
    buf[:, c] = limit(np.tanh(buf[:, c] * 1.1) * 0.9, 0.5)   # 0.89 時 mux 拉到 -14 LUFS 峰值 -0.8 dB，超過 -1.2 上限

peak = float(np.abs(buf).max())
rms = float(np.sqrt((buf ** 2).mean()))
vr = float(np.sqrt((voice ** 2).mean()))
mr = float(np.sqrt((music ** 2).mean()))
out = os.path.join(HERE, 'out', 'mix.wav')
sf.write(out, buf, SR)
print(f'{out}  {len(buf) / SR:.2f}s  peak {peak:.3f}  rms {rms:.4f}  旁白/配樂 {20 * np.log10(vr / mr):+.1f} dB')
