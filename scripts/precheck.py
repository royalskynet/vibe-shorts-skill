#!/usr/bin/env python3
"""發布前閘門。全部用腳本判，零 token。

用法：python3 scripts/precheck.py films/flt-11days
退出碼 0 代表可以發，非 0 代表有項目沒過，輸出會列出哪幾項。

為什麼要這支：規則寫在文件裡的符合率接近零，寫成會擋人的腳本才有用。
每一條都對應 docs/COMPLIANCE.md 裡的一段。

ponytail: 只檢查檔案存在與文字內容，不驗影片畫面。畫面交給 rhythm_check.py。
"""
import difflib
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

PLATFORMS = ["shorts", "reels", "threads"]

# 揭露句的必要元素，照 docs/COMPLIANCE.md。不比對整句，避免改一個字就假失敗。
DISCLOSURE_PARTS = ["合成語音", "程式"]

# 畫不出來的詞（docs/WRITING.md 規則 1）。寫在「動作」欄代表那張卡會退化成換字卡。
ABSTRACT = ["科技", "進步", "發展", "意義", "未來", "希望", "重大", "象徵", "氛圍", "感覺", "概念"]

SCRUB = Path.home() / "dev/reelbench-skills/skills/video-scrub/scripts/video-scrub.mjs"

# 故事閘門（2026-10-13 加）。費馬片 24 道工藝門全過，卻沒有鉤子、轉折、人生落點、片內提問、旁白。
# 必備段照 refs/vkv/narrative-templates.md 六段式的 1、4、5、6，順序固定；其他段可自由加。
# 門檻寫在這裡不寫在片子裡：受評者改不到評分器（fix 10368）。
STORY_SECTIONS = ["鉤子", "轉折", "落點", "提問"]
HOOK_MAX_CHARS = 25       # 鉤子第一句的字數上限；旁白約 4–5 字／秒，25 字約 5 秒講完
LEAD_SILENCE_MAX = 0.5    # 第一個字最晚幾秒出現；開場不留空白
ASR_SIM_MIN = 0.85        # 成片聽寫與旁白稿的字元相似度；低於此＝沒混進去或吃字
QUESTION_TAIL_S = 15      # 結尾提問要在片尾幾秒內講出來
QUESTION_SIM_MIN = 0.7    # 片尾聽寫與提問句的相似度
COVER_LUMA_MIN = 24       # 第 0 幀平均亮度（0–255）；limited range 全黑是 16
COVER_TEXT_H = 0.04       # 封面大字：字高至少畫面高的 4%（1920 → 77px；角落小字 28–46px，卡片大標 110px 起）
COVER_TEXT_MIN = 2        # 大字裡至少幾個中文字或數字
COVER_OCR_CONF = 60


VERDICTS = {"PRO_WINS", "CON_WINS", "SPLIT", "UNRESOLVED"}

# 目視自評（2026-10-18 採 xilo-opus-video 的 7 項打分）。拼圖由 scripts/qa_sheet.sh 產。
REVIEW_ITEMS = ["開場", "手機可讀", "動作", "變化", "構圖", "貼合原稿", "聲畫同步"]
REVIEW_MIN = 8


def review_problems(log: Path, master_sha: str):
    """qa/review_log.md：首行 video_sha 要等於成片，7 項每項一行「- 項目：分數 — 理由」且 ≥ REVIEW_MIN。"""
    if not log.is_file():
        return ["沒有 qa/review_log.md，跑 scripts/qa_sheet.sh 後看拼圖打分"]
    lines = log.read_text(encoding="utf-8").splitlines()
    m = re.fullmatch(r"video_sha:\s*([0-9a-f]{64})", lines[0].strip()) if lines else None
    if not m:
        return ["review_log.md 首行要是 video_sha: <成片 sha256>"]
    out = [] if m.group(1) == master_sha else ["video_sha 對不上現在的成片，重看重打"]
    scores = {}
    for ln in lines[1:]:
        s = re.match(r"^\s*-\s*(\S+?)[：:]\s*(\d+)\s*(?:/\s*10)?\s*[—-]+\s*\S", ln)
        if s:
            scores[s.group(1)] = int(s.group(2))
    for item in REVIEW_ITEMS:
        if item not in scores:
            out.append(f"缺「{item}」或沒寫理由")
        elif scores[item] < REVIEW_MIN:
            out.append(f"{item} {scores[item]} 分 < {REVIEW_MIN}")
    return out


# 抄襲閘（2026-10-18 使用者定）：sixty-one 台詞是 @canwebuildthis 原稿逐句直譯，不能發。
# 原稿只借結構（節拍、三段加碼、回扣），台詞要重寫。比對對象是 refs/dialogue-corpus/originals-zh.md 的直譯句。
COPY_SIM_MAX = 0.6    # 台詞與任一直譯句的字元相似度上限
COPY_MIN_CHARS = 5    # 短於此的句子（「好啦」「是很棒」）是通用口語，不比
# 圈內公共梗（docs/WRITING.md §5.1），不是哪支片的原創台詞，比對前從兩邊剔除
MEMES = ["你說得完全正確", "妳說得完全正確", "開新對話"]


def strip_memes(n: str) -> str:
    for m in MEMES:
        n = n.replace(norm(m), "")
    return n


def copy_problems(narr_text: str, originals_text: str):
    """narration.md 每句和原稿直譯句（「N. 角色：英文｜中文」的中文）比，太像就列出來。"""
    srcs = [strip_memes(norm(m)) for m in re.findall(r"^\d+\.\s*[^：:]+[：:].*?｜(.+)$", originals_text, re.M)]
    if not srcs:
        return ["originals-zh.md 讀不到任何直譯句，無法比對"]
    out = []
    for s in sentences(re.sub(r"^##.*$", "", narr_text, flags=re.M)):
        n = strip_memes(norm(s))
        if len(n) < COPY_MIN_CHARS:
            continue
        best = max(srcs, key=lambda x: difflib.SequenceMatcher(None, n, x).ratio())
        r = difflib.SequenceMatcher(None, n, best).ratio()
        if r > COPY_SIM_MAX:
            out.append(f"「{s.strip()}」像原稿「{best}」({r:.2f})")
    return out


def forbid_problems(text: str):
    """TREATMENT.md 要有「## 禁止清單」節，底下至少一條「- 」。"""
    m = re.search(r"^##\s*禁止清單\s*\n(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not m:
        return ["TREATMENT.md 沒有「## 禁止清單」節，寫法見 docs/WRITING.md §6"]
    items = [ln for ln in m.group(1).splitlines() if re.match(r"^\s*-\s*\S", ln)]
    return [] if items else ["禁止清單是空的"]


def sha_of(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "none"


def humanize_problems(film: Path):
    """audit/humanize.md 首行 `narration_sha: <sha256>` 要等於現在的 narration.md；有改動清單或寫「無需改」。"""
    p = film / "audit" / "humanize.md"
    if not p.is_file():
        return ["沒有 audit/humanize.md：照 genie-humanizer 逐句改成台灣口語後寫戳記（docs/WRITING.md §7）"]
    lines = p.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != f"narration_sha: {sha_of(film / 'narration.md')}":
        return ["humanize 戳記跟現在的 narration.md 不符（改稿後要重過）"]
    if not any(ln.strip() for ln in lines[1:]):
        return ["humanize.md 沒寫改了哪些句（或「無需改」）"]
    return []


def audit_problems(film: Path):
    """反方稽核門（docs/WRITING.md §4）：證據包合格、每個爭點都有裁決、裁決綁的是現在的稿與來源。"""
    pack, ver = film / "audit" / "devils-advocate.md", film / "audit" / "verdicts.md"
    if not pack.is_file():
        return ["缺 audit/devils-advocate.md；跑 scripts/devils.sh"]
    p = pack.read_text(encoding="utf-8")
    if not p.startswith("# Devil's Advocate Evidence Pack"):
        return ["證據包開頭不是 # Devil's Advocate Evidence Pack"]
    issues = re.split(r"^## 爭點 *\d+\s*$", p, flags=re.M)[1:]
    if not issues:
        return ["證據包沒有任何爭點"]
    out = []
    for i, b in enumerate(issues, 1):
        none = "NO_EVIDENCE_BACKED_OBJECTION" in b
        cited = re.search(r"URL: *https?://\S+", b) and re.search(r"EXCERPT: *\S", b)
        if not (none or cited or "REPORT:" in b):
            out.append(f"爭點 {i} 沒有 URL＋摘錄，也沒標 NO_EVIDENCE_BACKED_OBJECTION")
    if not ver.is_file():
        return out + ["缺 audit/verdicts.md：主 session 要逐爭點裁決"]
    v = ver.read_text(encoding="utf-8")
    if not re.match(r"engine=(codex|opencode|subagent)\b", v):
        out.append("verdicts.md 首行要是 engine=<codex|opencode|subagent>")
    for key, f in (("narration_sha", film / "narration.md"), ("sources_sha", film / "SOURCES.md")):
        m = re.search(rf"^{key}: *(\S+)", v, re.M)
        if not m or m.group(1) != sha_of(f):
            out.append(f"{f.name} 在稽核後改過（{key} 對不上），重跑 scripts/devils.sh 並重新裁決")
    got = re.findall(r"^VERDICT: *(\S+)\s*\nREASON: *(\S.*)$", v, re.M)
    if len(got) != len(issues):
        out.append(f"證據包 {len(issues)} 個爭點，verdicts.md 有 {len(got)} 筆 VERDICT＋REASON")
    bad = [x for x, _ in got if x not in VERDICTS]
    if bad:
        out.append(f"不認得的裁決 {bad}，只能是 {sorted(VERDICTS)}")
    return out


def shot_grid_exempt(film: Path):
    """地圖格式不比鏡頭格線，回傳原因；其他格式回 None。

    地圖片是同一張地圖連續平移縮放，卡片之間沒有硬切，場景偵測切不出卡片：
    scam-map 53 秒 14 張卡只切出 5 鏡，對標的 6 支地圖頭部片也只切出 1–5 鏡（refs/BREAKDOWN-NOTES.md）。
    格式跟 rhythm_check 共用片目錄的 rhythm-profile 檔。
    """
    f = film / "rhythm-profile"
    prof = f.read_text(encoding="utf-8").strip() if f.is_file() else ""
    if prof == "map":
        return "地圖格式連續運鏡沒有硬切，場景偵測切不出卡片，不比格線"
    if prof == "calm":
        # 靜態科普換卡是原地交叉淡化，沒有硬切（使用者 2026-10-30 核准，對標 DemDuhNk1ZR 0 次硬切）
        return "靜態格式換卡原地淡化，沒有硬切，場景偵測切不出卡片"
    if prof == "dialogue":
        # 對談片一句一鏡，鏡長跟著台詞長短走，本來就沒有固定格線（使用者 2026-10-17 核准免除）
        return "對談格式一句一鏡，鏡長隨台詞長短，沒有卡片格線"
    return None


def cut_boundary_problems(cuts, lines, tol=0.3):
    """有配音時間軸的片，每個偵測到的切點都要落在兩句之間的空檔（容差 tol 秒），回傳沒貼上的切點。

    卡長跟著配音走就沒有等長格線（france 3.46–8.57 秒），改比 voice.py 產的句界（使用者 2026-10-20 核准）。
    ponytail: 暗底同色卡偵測器常漏切（france 21 個換卡只切出 4 刀），只驗得到切出來的那幾刀；
    要更嚴就改成逐句界抽幀比對卡片內容。
    """
    if not cuts:
        return ["偵測不到任何切點，無法對時間軸"]
    gaps = [(a["t1"], b["t0"]) for a, b in zip(lines, lines[1:])]
    out = []
    for c in cuts:
        dist = min((0 if a <= c <= b else min(abs(c - a), abs(c - b)) for a, b in gaps), default=None)
        if dist is None or dist > tol:
            out.append(f"{c:.2f}s 離句界 {dist if dist is None else round(dist, 2)}s")
    return out


def facts_exempt(film: Path):
    """對談片稿中沒有三位數以上的數字（門本身只驗 3 位數以上）就不要求 facts.md，回傳原因；否則回 None。

    使用者 2026-10-17 核准：對談片是角色日常對話，沒有要查證的事實數字。
    稿裡一旦出現三位數以上的數字（統計、年份），就跟一般片一樣要附來源。
    """
    f = film / "rhythm-profile"
    narr = film / "narration.md"
    if not (f.is_file() and f.read_text(encoding="utf-8").strip() == "dialogue" and narr.is_file()):
        return None
    if re.search(r"\d{3,}", narr.read_text(encoding="utf-8")):
        return None
    return "對談格式且稿中沒有三位數以上的數字"


def check(name: str, ok: bool, detail: str = "") -> bool:
    print(f"{'OK  ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))
    return ok


VIRAL_MIN = 100_000  # 對標至少一支 ≥10 萬播放／瀏覽，才算有爆款依據


def viral_problems(text):
    """TREATMENT.md 要有「爆款證據：」行，附連結與播放數（萬／億），且至少一筆 ≥ VIRAL_MIN。
    爆款是至高原則：沒證據的題不准出片。證據來源用 viral-scout，寫進 refs/VIRAL-LEDGER.md。"""
    lines = [ln for ln in text.splitlines() if ln.lstrip("-* ").startswith("爆款證據")]
    if not lines:
        return ["TREATMENT.md 沒有「爆款證據：」行（先跑 viral-scout）"]
    body = " ".join(lines)
    if not re.search(r"https?://", body):
        return ["爆款證據沒附連結"]
    nums = [float(n) * (1e8 if u == "億" else 1e4) for n, u in re.findall(r"(\d+(?:\.\d+)?)\s*(萬|億)", body)]
    if not nums or max(nums) < VIRAL_MIN:
        return [f"爆款證據最高不到 {VIRAL_MIN // 10000} 萬播放"]
    return []


def parse_narration(text):
    """narration.md 的「## 段名」切段，回 [(段名, 內文)]。"""
    out = []
    for block in re.split(r"^##\s+", text, flags=re.M)[1:]:
        title, _, body = block.partition("\n")
        out.append((title.strip(), body.strip()))
    return out


def sentences(text):
    return [s for s in re.findall(r"[^。？！?!\n]+[。？！?!]?", text) if s.strip()]


def story_problems(sections, dialogue=False):
    """旁白稿結構：必備段齊、順序對、有內容；鉤子短且跟觀眾有關或丟問題；提問段以問號收尾。

    dialogue（對談格式）不比「鉤子跟觀眾有關」：對談片第一句是角色對角色說話，
    對標的 IG 對談爆款開頭多是陳述句（docs/RESEARCH-dialogue.md），使用者 2026-10-17 核准免除。
    """
    titles = [t for t, _ in sections]
    body = dict(sections)
    problems = [f"缺「{s}」段" for s in STORY_SECTIONS if s not in titles]
    if problems:
        return problems
    order = [titles.index(s) for s in STORY_SECTIONS]
    if order != sorted(order):
        problems.append("必備段順序要是 " + "→".join(STORY_SECTIONS))
    problems += [f"「{s}」段是空的" for s in STORY_SECTIONS if not body[s]]
    if problems:
        return problems
    first = sentences(body["鉤子"])[0].strip()
    if len(norm(first)) > HOOK_MAX_CHARS:
        problems.append(f"鉤子第一句 {len(norm(first))} 字，上限 {HOOK_MAX_CHARS}")
    if not dialogue and "你" not in first and not re.search(r"[？?]", first):
        problems.append("鉤子第一句沒有「你」也沒有問題，跟觀眾無關")
    last = sentences(body["提問"])[-1].strip()
    if not re.search(r"[？?]$", last):
        problems.append("提問段最後一句不是問句")
    return problems


def storyboard_rows(text):
    """TREATMENT.md 的分鏡表（表頭有「動作」欄的那張），表頭到表尾連續的 | 列。
    檔裡還有其他表（爆款文本對照）時只取分鏡表；找不到就退回第一張表，讓呼叫端報缺欄。"""
    lines = text.splitlines()
    tables, cur = [], []
    for ln in lines + [""]:
        if ln.startswith("|"):
            cur.append(ln)
        elif cur:
            tables.append(cur)
            cur = []
    for tb in tables:
        if any(c.strip().startswith("動作") for c in tb[0].strip("|").split("|")):
            return tb
    return tables[0] if tables else []


def norm(s):
    """只留中日韓字與英數，比對時不受標點、空白影響。"""
    return re.sub(r"[^\w㐀-鿿]|_", "", s).lower()


def to_trad(s):
    """Whisper 中文常吐簡體，比對前轉繁。opencc 不在就讓它炸：不能安靜地判成相似度低。
    用台灣用字（s2tw）：s2t 會把「为／里」轉成「爲／裏」，跟稿上的「為／裡」對不上，念對也扣分。"""
    return subprocess.run(["opencc", "-c", "s2tw"], input=s, capture_output=True,
                          text=True, check=True).stdout


def asr_norm(s):
    """聽寫比稿用的正規化：數字寫法與異體字不算念錯（跟 voice.py 單句核稿同一套數字讀法）。
    10-30 pedestrian-hell：Whisper 把念對的「三百六十六」「二〇二二」寫成 366、2022，
    「台」轉成「臺」，整片 0.845 卡在 0.85 門下；真正聽錯的只有幾個字。門檻不動，只修量法。"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from verify_tts import DIGIT, spell
    s = re.sub(r"\d{4}(?=年)", lambda m: "".join(DIGIT[int(c)] for c in m.group()), s)
    s = re.sub(r"\d+", lambda m: spell(int(m.group())), s)
    return norm(s).replace("〇", "零").replace("臺", "台")


def asr_problems(sections, rep, duration):
    """拿成片聽寫比旁白稿：有沒有混進去、有沒有吃字、開場空白、片尾有沒有講出提問。"""
    words = rep.get("words") or []
    if not words:
        return ["成片聽不到旁白"]
    problems = []
    script = asr_norm("".join(b for _, b in sections))
    # 一次轉完再按換行切回各字詞（opencc 保留換行），不必每個字詞叫一次 opencc
    trad = to_trad("\n".join(w["w"].replace("\n", "") for w in words)).split("\n")
    heard = asr_norm("".join(trad))
    sim = difflib.SequenceMatcher(None, script, heard, autojunk=False).ratio()
    if sim < ASR_SIM_MIN:
        problems.append(f"聽寫與旁白稿相似度 {sim:.2f}，門檻 {ASR_SIM_MIN}（沒混進成片或吃字）")
    if words[0]["t0"] > LEAD_SILENCE_MAX:
        problems.append(f"第一個字在 {words[0]['t0']}s，開場空白上限 {LEAD_SILENCE_MAX}s")
    q = asr_norm(sentences(dict(sections)["提問"])[-1])
    chars = [(c, w["t0"]) for w, t in zip(words, trad) for c in asr_norm(t)]
    # 提問句不一定是最後幾個字：Whisper 會在片尾音樂上幻聽出「請不吝點讚訂閱…明鏡與點點欄目」
    # （dating-bill 10-15），所以在後段每個起點比一次，取最像的那段。
    best = (0.0, None)
    for i in range(max(0, len(chars) - 3 * len(q)), max(0, len(chars) - len(q)) + 1) if q else []:
        win = chars[i:i + len(q)]
        s = difflib.SequenceMatcher(None, q, "".join(c for c, _ in win), autojunk=False).ratio()
        if s > best[0]:
            best = (s, win[0][1])
    tail_sim, q_at = best
    if tail_sim < QUESTION_SIM_MIN:
        problems.append(f"片尾聽到的不是提問句（相似度 {tail_sim:.2f}）")
    elif q_at < duration - QUESTION_TAIL_S:
        problems.append(f"提問在 {q_at}s 講出，要在最後 {QUESTION_TAIL_S}s 內")
    return problems


def duration_of(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def first_frame_luma(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-f", "lavfi", "-i", f"movie={path},signalstats",
                        "-show_entries", "frame_tags=lavfi.signalstats.YAVG", "-read_intervals", "%+#1",
                        "-of", "csv=p=0"], capture_output=True, text=True, check=True)
    return float(r.stdout.split()[0].strip(","))


def cover_big_text(tsv: str, frame_h: int) -> str:
    """tesseract TSV 裡夠大、夠有把握的字，只留中文字與數字（雜訊常是單個拉丁字母）。"""
    out = ""
    for row in tsv.splitlines()[1:]:
        x = row.split("\t")
        if len(x) < 12 or not x[11].strip():
            continue
        if int(x[9]) >= frame_h * COVER_TEXT_H and float(x[10]) >= COVER_OCR_CONF:
            out += "".join(ch for ch in x[11] if ch.isdigit() or "一" <= ch <= "鿿")
    return out


def first_frame_text(path):
    """第 0 幀 OCR，回傳 cover_big_text 的結果。tesseract 不在就讓它丟錯，不默默過。"""
    png = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-frames:v", "1", "-f", "image2pipe",
                          "-vcodec", "png", "-"], capture_output=True, check=True).stdout
    h = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=height", "-of", "csv=p=0", str(path)],
                           capture_output=True, text=True, check=True).stdout.strip())
    r = subprocess.run(["tesseract", "stdin", "-", "-l", "chi_tra+eng", "--psm", "11", "tsv"],
                       input=png, capture_output=True, check=True)
    return cover_big_text(r.stdout.decode("utf-8", "replace"), h)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    film = Path(sys.argv[1]).resolve()
    if not film.is_dir():
        print(f"找不到 {film}")
        return 2

    name = film.name
    dist = film / "dist"
    meta = film / "meta"
    results = []

    # 0. 成片要比頁面新。
    #
    # 2026-10-11 踩到：改了 index.html 裡的一個數字（129 頁改成 109 頁），
    # 其他每一道門都過，因為它們比的是 index.html 和 facts.md。
    # 但 mp4 是改之前渲染的，畫面上還是錯的數字。
    # 檔案時間是唯一能機械判斷「這支片有沒有包含最新改動」的依據。
    master = film / f"{name}.mp4"
    page = film / "index.html"
    if master.is_file() and page.is_file():
        fresh = master.stat().st_mtime > page.stat().st_mtime
        results.append(check("成片比頁面新", fresh,
                             "" if fresh else "index.html 改過但還沒重新渲染，跑 build.sh"))
    else:
        results.append(check("成片比頁面新", False, "找不到成片或 index.html"))

    # 1. 三個平台的交付檔都在
    for p in PLATFORMS:
        f = dist / f"{name}-{p}.mp4"
        # 交付檔要比成片新：10-20 france 建置鏈在 deliver 中途被 SIGTERM，dist 留著上一版成片的匯出，
        # 時長一樣，其他門都看不出來
        stale = f.is_file() and master.is_file() and f.stat().st_mtime < master.stat().st_mtime
        results.append(check(f"{p} 交付檔", f.is_file() and not stale,
                             "比成片舊，重跑 scripts/deliver.sh" if stale else
                             f"{f.stat().st_size // 1048576} MB" if f.is_file() else str(f)))

    # 1b. 第 0 幀當封面要看得到東西。
    # Threads API 沒有封面參數、IG 不傳 cover_url 時都拿第 0 幀當封面。
    # 2026-10-18 踩到：codex 骨架片頭 0.4s 從黑淡入，codex 公開後 IG／Threads 封面一片黑。
    for p in PLATFORMS:
        f = dist / f"{name}-{p}.mp4"
        if f.is_file():
            y = first_frame_luma(f)
            results.append(check(f"{p} 封面幀", y >= COVER_LUMA_MIN,
                                 f"第 0 幀亮度 {y:.0f}" + ("" if y >= COVER_LUMA_MIN else
                                 f" < {COVER_LUMA_MIN}，片頭別從黑淡入")))

    # 1c. 第 0 幀要有大字（使用者 2026-10-20 定：預覽畫面都要帶文字）。
    # france 第 0 幀大標還在逐字滑出，只剩角落小字，三平台預覽都是一張空地圖。
    # 判準：OCR 字高 ≥ 畫面 4% 的中文字／數字至少 2 個；做法是第一卡大標第 0 幀就完整顯示。
    for p in PLATFORMS:
        f = dist / f"{name}-{p}.mp4"
        if f.is_file():
            txt = first_frame_text(f)
            results.append(check(f"{p} 封面有字", len(txt) >= COVER_TEXT_MIN,
                                 f"第 0 幀大字「{txt}」" if txt else
                                 "第 0 幀沒有大字，第一卡大標要在第 0 幀就完整顯示"))

    # 2. 元資料清掉了。
    # 判準交給 video-scrub 自己的 verify：它比對的是「來源片的身份字串有沒有漏進輸出」。
    # 不要自己掃 Lavf／libx264，那是 ffmpeg 重封裝時自己寫的標籤，
    # 跟來源身份無關，掃了會得到假失敗（2026-10-11 實際踩到）。
    for p in PLATFORMS:
        f = dist / f"{name}-{p}.mp4"
        if not (f.is_file() and master.is_file()):
            results.append(check(f"{p} 元資料", False, "檔案不存在，跳過"))
            continue
        r = subprocess.run(["node", str(SCRUB), "verify", str(master), str(f)],
                           capture_output=True, text=True)
        results.append(check(f"{p} 元資料", r.returncode == 0,
                             "" if r.returncode == 0 else
                             (r.stdout or r.stderr).strip().splitlines()[-1][:80]))

    # 3. 三個平台各有說明文字，而且內容不一樣（同一段發三次會壓低互動）
    captions = {}
    for p in PLATFORMS:
        f = meta / f"caption-{p}.txt"
        if f.is_file():
            captions[p] = f.read_text(encoding="utf-8").strip()
        results.append(check(f"{p} 說明文字", f.is_file(), "" if f.is_file() else str(f)))

    if len(captions) == len(PLATFORMS):
        uniq = len({c for c in captions.values()})
        results.append(check("說明文字三份互不相同", uniq == len(PLATFORMS),
                             f"只有 {uniq} 種"))

    # 3b. 每份說明文字都有結尾提問（BRAND.md：結尾提問的留言多出幾十倍）。
    # 2026-10-13 第二支片三份說明都漏了，發布前才發現。
    for p, text in captions.items():
        has_q = bool(re.search(r"[？?]\s*(留言[^\n]*)?$", text, re.M))
        results.append(check(f"{p} 結尾提問", has_q, "" if has_q else "沒有以問號結尾的句子"))

    # 4. 每份說明文字都帶 AI 揭露
    for p, text in captions.items():
        missing = [w for w in DISCLOSURE_PARTS if w not in text]
        results.append(check(f"{p} AI 揭露", not missing,
                             "缺 " + "、".join(missing) if missing else ""))

    # 5. 事實類內容要列來源。至少一行以「來源」開頭。
    for p, text in captions.items():
        has_src = bool(re.search(r"^\s*來源", text, re.M))
        results.append(check(f"{p} 列出來源", has_src))

    # 6. 公開網址用隨機 token，不是片名
    manifest = film / "meta" / "public-path.txt"
    if manifest.is_file():
        token = manifest.read_text(encoding="utf-8").strip()
        ok = bool(re.fullmatch(r"[0-9a-f]{16,}", token)) and name not in token
        results.append(check("公開路徑是隨機 token", ok, token[:24]))
    else:
        results.append(check("公開路徑是隨機 token", False,
                             "還沒產，發布前跑 scripts/publish/public_path.py"))

    # 7. 片中每個數字都要在 facts.md 有來源。
    # 這條是 2026-10-11 加的：成片裡「Wiles 的證明 129 頁」是錯的，正確是 109 頁，
    # 而且錯誤已經渲染進影片。數字錯了再公開發布收不回來，所以用腳本擋。
    facts = film / "meta" / "facts.md"
    if facts_exempt(film):
        results.append(check("數字都有來源", True, f"略過：{facts_exempt(film)}"))
    elif facts.is_file() and page.is_file():
        # 判準是 index.html 頂端的 FACTS 物件，不是散落各處的數字字面值。
        # 原本掃卡片文字，漏掉繪圖函式裡的 `* 129`：同一個事實寫在兩個地方，
        # 改了卡片沒改動畫，成片標題是 109、畫面正中央的大數字卻數到 129，而門全過。
        # 散在各處的數字沒辦法跟版面座標區分，驗不了；集中到 FACTS 才驗得動。
        src = facts.read_text(encoding="utf-8").replace(",", "")
        html = page.read_text(encoding="utf-8")
        block = re.search(r"const FACTS = \{(.*?)\n\};", html, re.S)
        if not block:
            results.append(check("數字都有來源", False,
                                 "index.html 沒有 FACTS 物件，事實數字要集中在那裡"))
        else:
            pairs = re.findall(r"(\w+):\s*(\d+)", block.group(1))
            missing = [f"{k}={v}" for k, v in pairs if v not in src]
            # 卡片文字裡的數字分兩種處理。
            # 值同時出現在 FACTS 的，必須寫成 ${FACTS.X}：那代表同一個事實被畫出來
            # 也被講出來，兩邊各寫一次就會分岔，129／109 那次就是這樣漏的。
            # 不在 FACTS 的（只在散文裡出現一次），有來源就行，不必硬塞進 FACTS。
            fact_vals = {v for _, v in pairs}
            cards = re.findall(r"^\s*\{\s*head:.*$", html, re.M)
            bare = {n for line in cards for n in re.findall(r"(?<![\w.$}])\d{3,}", line)}
            dup = sorted(bare & fact_vals)
            unsourced = sorted(n for n in bare - fact_vals if n not in src)
            detail = "　".join(filter(None, [
                "facts.md 缺 " + "、".join(missing) if missing else "",
                "這些在 FACTS 裡了，卡片要改用 ${FACTS.X}： " + "、".join(dup) if dup else "",
                "沒來源的數字 " + "、".join(unsourced) if unsourced else "",
            ]))
            results.append(check("數字都有來源", not (missing or dup or unsourced),
                                 detail or f"FACTS {len(pairs)} 項＋散文數字都對得上"))
    else:
        results.append(check("數字都有來源", False, f"找不到 {facts.name} 或 index.html"))

    # 8. 鏡頭格線：拉片量到的鏡長中位數要貼合卡片格線。
    #
    # 為什麼用中位數而不是「有沒有短鏡頭」：2026-10-11 實測，我們為了過節奏閘門
    # 加的大面積網點呼吸，會被場景偵測讀成切點。費馬那支在卡 1 到卡 2 的轉場
    # 被切出 0.63 秒和 0.9 秒兩個鏡頭，但那是偵測器的假切點，畫面沒有硬切。
    # 兩個工具方向相反：節奏閘門要亮度大幅變化，場景偵測靠亮度變化找切點。
    # 中位數不受這種假切點影響，還抓得到真正的時間軸漂移。
    shots = film / "shots" / "shots.json"
    exempt = shot_grid_exempt(film)
    if exempt:
        results.append(check("鏡頭格線", True, f"略過：{exempt}"))
    elif shots.is_file() and page.is_file():
        if master.is_file() and shots.stat().st_mtime < master.stat().st_mtime:
            results.append(check("鏡頭格線", False, "shots.json 比成片舊，重跑 video-shots seed"))
        else:
            data = json.loads(shots.read_text(encoding="utf-8"))
            tl = film / "timeline.js"
            if tl.is_file():
                # 有配音時間軸：卡長跟著句子走，改驗切點貼句界（見 cut_boundary_problems）
                t = tl.read_text(encoding="utf-8")
                lines = json.loads(t[t.index("{"):t.rindex("}") + 1])["lines"]
                cuts = [s["start"] for s in data["shots"][1:]]
                bad = cut_boundary_problems(cuts, lines)
                results.append(check("鏡頭格線", not bad,
                                     "；".join(bad) or f"{len(cuts)} 個切點都落在句界（{len(lines)} 句）"))
            else:
                secs = sorted(s["seconds"] for s in data["shots"])
                median = secs[len(secs) // 2]
                cards = len(re.findall(r"^\s*\{\s*head:", page.read_text(encoding="utf-8"), re.M))
                expect = data["meta"]["durationSeconds"] / cards if cards else 0
                ok = expect and abs(median - expect) / expect < 0.10
                results.append(check("鏡頭格線", bool(ok),
                                     f"中位數 {median:.2f}s／格線 {expect:.2f}s"))
    else:
        results.append(check("鏡頭格線", False, "還沒跑 video-shots seed"))

    # 9. 節奏閘門
    if master.is_file():
        r = subprocess.run([sys.executable, "scripts/rhythm_check.py", str(master)],
                           capture_output=True, text=True)
        results.append(check("節奏閘門", r.returncode == 0,
                             r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""))
    else:
        results.append(check("節奏閘門", False, f"找不到母帶 {master}"))

    # 10. 尋幀一致：build.sh 渲染前跑的 seek_check.mjs 留下的報告。
    # 報告要比 index.html 新，不然是改頁面之前的結果。
    seek = film / "out" / "seek-report.json"
    if seek.is_file() and page.is_file():
        rep = json.loads(seek.read_text(encoding="utf-8"))
        fresh = seek.stat().st_mtime > page.stat().st_mtime
        bad = [f["frame"] for f in rep["frames"] if not f["identical"]]
        detail = ("報告比 index.html 舊，跑 build.sh" if not fresh
                  else f"交界幀不一致 {bad}" if bad
                  else f"外部請求 {len(rep['external'])} 筆" if rep["external"]
                  else f"震動 {rep['orphanShakes']}s 對不到事件表" if rep.get("orphanShakes")
                  else "" if rep.get("shakes") is not None else "頁面沒匯出 SHAKES，震動對時未查")
        # 沒查到不算過（fix 10370：不可能失敗的事通過了不帶資訊）。原本這裡只提示、照樣 OK。
        checked = rep.get("shakes") is not None
        results.append(check("尋幀一致", fresh and rep["ok"] and checked, detail))
    else:
        results.append(check("尋幀一致", False, "還沒跑 scripts/seek_check.mjs"))

    # 11. 藏字檢查：build.sh 渲染前跑的 textless_check.mjs 留下的報告。
    # 藏字後只剩外框的卡判失敗。已做完的片可以在 meta/textless-waive.txt 逐卡豁免，
    # 一行一張「<卡號> <原因>」，沒寫原因不算。
    tl = film / "out" / "textless-report.json"
    if tl.is_file() and page.is_file():
        rep = json.loads(tl.read_text(encoding="utf-8"))
        waive_f = meta / "textless-waive.txt"
        waived = set()
        if waive_f.is_file():
            for line in waive_f.read_text(encoding="utf-8").splitlines():
                parts = line.split(maxsplit=1)
                if len(parts) == 2 and parts[0].isdigit():
                    waived.add(int(parts[0]))
        fresh = tl.stat().st_mtime > page.stat().st_mtime
        bad = [c["card"] for c in rep["cards"] if c["level"] == "fail" and c["card"] not in waived]
        warn = [c["card"] for c in rep["cards"] if c["level"] == "warn"]
        detail = ("報告比 index.html 舊，跑 build.sh" if not fresh
                  else f"卡 {bad} 藏字後只剩外框" if bad
                  else "; ".join(x for x in [f"豁免卡 {sorted(waived)}" if waived else "",
                                             f"偏薄卡 {warn}" if warn else ""] if x))
        results.append(check("藏字檢查", fresh and not bad, detail))
    else:
        results.append(check("藏字檢查", False, "還沒跑 scripts/textless_check.mjs"))

    # 12. 寫稿規則（docs/WRITING.md）：TREATMENT.md 表格每張卡都要有能畫的「動作」，
    # 「衝擊事件」填的類型要真的在 events.json 裡，不然寫了等於沒接上聲音。
    # ponytail: 抽象詞只擋清單裡的；清單外的抽象寫法要靠人看。
    treat = film / "TREATMENT.md"
    # 12a. 爆款證據（至高原則）：題目要有對標爆款，不然整支片不該做。
    problems = viral_problems(treat.read_text(encoding="utf-8")) if treat.is_file() else ["找不到 TREATMENT.md"]
    results.append(check("爆款證據", not problems, "；".join(problems)))
    # 12a'. 禁止清單：做片前先寫這支不准出現的畫面寫法（xilo-opus-video 的 forbidden list）。
    problems = forbid_problems(treat.read_text(encoding="utf-8")) if treat.is_file() else ["找不到 TREATMENT.md"]
    results.append(check("禁止清單", not problems, "；".join(problems)))
    evf = film / "out" / "events.json"
    if not evf.is_file():
        evf = film / "events.json"
    if treat.is_file() and evf.is_file():
        rows = storyboard_rows(treat.read_text(encoding="utf-8"))
        head = [c.strip() for c in rows[0].strip("|").split("|")] if rows else []
        ai = next((i for i, c in enumerate(head) if c.startswith("動作")), None)
        ei = next((i for i, c in enumerate(head) if c.startswith("衝擊事件")), None)
        if ai is None or ei is None:
            results.append(check("寫稿規則", False, "TREATMENT.md 表格缺「動作」或「衝擊事件」欄，格式見 docs/WRITING.md"))
        else:
            types = {e["type"] for e in json.loads(evf.read_text(encoding="utf-8"))["ev"]}
            problems = []
            for ln in rows[2:]:
                cells = [c.strip() for c in ln.strip("|").split("|")]
                if len(cells) <= max(ai, ei):
                    # 原本 continue：欄位少的列整列沒檢查卻不報，等於默默放行
                    problems.append(f"這列欄位不足：{ln[:30]}")
                    continue
                card, act, ev = cells[1], cells[ai], cells[ei]
                if act in ("", "—", "-"):
                    problems.append(f"卡 {card} 沒寫動作")
                hit = [w for w in ABSTRACT if w in act]
                if hit:
                    problems.append(f"卡 {card} 動作用了抽象詞 {hit}")
                if ev not in ("", "—", "-") and ev not in types:
                    problems.append(f"卡 {card} 衝擊事件 {ev} 不在 events.json")
            results.append(check("寫稿規則", not problems, "；".join(problems)))
    else:
        results.append(check("寫稿規則", False, "找不到 TREATMENT.md 或 events.json"))

    # 13. 故事閘門：旁白稿結構（判 narration.md 本身）
    narr = film / "narration.md"
    sections = parse_narration(narr.read_text(encoding="utf-8")) if narr.is_file() else []
    dialogue = (film / "rhythm-profile").is_file() and \
        (film / "rhythm-profile").read_text(encoding="utf-8").strip() == "dialogue"
    if narr.is_file():
        problems = story_problems(sections, dialogue)
        results.append(check("旁白稿結構", not problems, "；".join(problems)))
    else:
        results.append(check("旁白稿結構", False, "找不到 narration.md，格式見 docs/WRITING.md §3"))
    # 13a. 口語門（使用者 10-29 定）：稿要過 humanize，戳記綁現在的稿，改稿後要重過
    problems = humanize_problems(film)
    results.append(check("口語化（humanize）", not problems, "；".join(problems)))

    # 13b. 抄襲閘：台詞不得沿用爆款原稿的直譯句。原稿檔不進版控，找不到就擋（沒比對不算過）。
    orig = Path(__file__).resolve().parent.parent / "refs" / "dialogue-corpus" / "originals-zh.md"
    if not dialogue:  # 原創稿沒有可抄的原稿，這道門不適用（rhythm-profile 不是 dialogue）
        results.append(check("台詞非照抄", True, "非改編對談片，不適用"))
    else:
        if narr.is_file() and orig.is_file():
            problems = copy_problems(narr.read_text(encoding="utf-8"), orig.read_text(encoding="utf-8"))
        else:
            problems = ["找不到 narration.md 或 refs/dialogue-corpus/originals-zh.md，無法比對"
                        "（原創稿把 rhythm-profile 設成 vkv 就不適用）"]
        results.append(check("台詞非照抄", not problems, "；".join(problems[:4]) +
                             (f" 等 {len(problems)} 句" if len(problems) > 4 else "")))

    # 14. 故事閘門：旁白真的進了成片（判 narration_check.py 留下的 Whisper 證據）。
    # 報告用 sha256 綁定成片與旁白稿，任一改過就是舊證據，不靠檔案時間。
    nr = film / "out" / "narration-report.json"
    if not (nr.is_file() and narr.is_file() and master.is_file()):
        results.append(check("旁白進成片", False, "缺旁白稿、成片或報告；跑 .venv/bin/python scripts/narration_check.py"))
    else:
        rep = json.loads(nr.read_text(encoding="utf-8"))
        stale = (rep.get("master_sha") != hashlib.sha256(master.read_bytes()).hexdigest()
                 or rep.get("narration_sha") != hashlib.sha256(narr.read_bytes()).hexdigest())
        if stale:
            results.append(check("旁白進成片", False, "報告跟現在的成片或旁白稿對不上，重跑 narration_check.py"))
        elif story_problems(sections, dialogue):
            results.append(check("旁白進成片", False, "旁白稿結構沒過，先修稿"))
        else:
            problems = asr_problems(sections, rep, duration_of(master))
            results.append(check("旁白進成片", not problems, "；".join(problems)))

    # 15. 反方稽核：旁白稿定稿前要過 /research 第三輪 devil's advocate，避免 AI 幻覺的數字或推論被發出去。
    problems = audit_problems(film)
    results.append(check("反方稽核", not problems, "；".join(problems)))

    # 16. 目視自評：其他門都驗檔案與聲音，沒有一道看畫面。看拼圖按 7 項打分，綁成片 sha。
    problems = review_problems(film / "qa" / "review_log.md", sha_of(master))
    results.append(check("目視自評", not problems, "；".join(problems)))

    failed = results.count(False)
    print()
    print(f"{len(results) - failed}/{len(results)} 過" + ("" if not failed else f"，{failed} 項要補"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
