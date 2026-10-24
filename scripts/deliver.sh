#!/bin/bash
# 把一支成片轉成三個平台的交付檔，並清掉元資料。
#
# 用法：scripts/deliver.sh films/flt-11days/flt-11days.mp4
# 產出：films/<名稱>/dist/<名稱>-{shorts,reels,threads}.mp4
#
# 為什麼要三個檔而不是一個檔發三次：三個平台的時長上限和位元率不同，
# shorts 上限 180 秒、reels 上限 90 秒。用同一個檔發，長片會被平台自己裁。
# Threads 沒有專屬 preset，用 reels（同樣 9:16，Threads 影片上限 5 分鐘更寬）。
#
# 為什麼最後要清元資料：匯出會把編碼器名稱、建檔時間寫進檔案，
# 碼流裡還有 ffprobe 看不到的 SEI 身份串。公開發布前清掉。
set -euo pipefail

FFMPEG_SKILL="$HOME/dev/ffmpeg-skill/scripts"
SCRUB="$HOME/dev/reelbench-skills/skills/video-scrub/scripts/video-scrub.mjs"

SRC="${1:?用法: deliver.sh <成片.mp4>}"
[ -f "$SRC" ] || { echo "找不到 $SRC" >&2; exit 1; }

# 不要處理還在被寫入的檔案。
#
# 這個坑踩過兩次。第一次是兩個建置同時跑，第二個讀到寫一半的 mix.wav，
# 量到 peak +61.9 dBFS 這種不可能的值。當時只把順序寫進 build.sh，
# 沒想到從外面呼叫 deliver.sh 一樣會撞上——2026-10-11 就撞了，
# ffmpeg 還在 mux，我對 16.8 MB 的半成品跑匯出，得到 moov atom not found。
# 檔案被誰開著是唯一可靠的判斷，檔案大小看起來正常不代表寫完了。
if lsof -t -- "$SRC" >/dev/null 2>&1; then
  echo "還有行程開著 $SRC，應該是建置沒跑完。等它結束再來。" >&2
  exit 1
fi

DIR="$(cd "$(dirname "$SRC")" && pwd)"
NAME="$(basename "$SRC" .mp4)"
OUT="$DIR/dist"
mkdir -p "$OUT"

# 渲染出來的主片是全範圍 yuvj420p（逐幀 JPEG）。export.py 雖然帶 -pix_fmt yuv420p，
# 範圍旗標照樣是 pc，check.py 判 FAIL；2026-10-13 IG／Threads container 都 ERROR。
# 先無損轉成標準範圍再匯出，畫質只差範圍量化那一步。
IN="$SRC"
# color_range 有時讀成 unknown，但 pix_fmt 仍是 yuvj420p（france 10-20：YouTube 私人片手機無法播放），兩個都要判
SRC_RANGE="$(ffprobe -v error -select_streams v:0 -show_entries stream=color_range,pix_fmt -of csv=p=0 "$SRC")"
if [[ "$SRC_RANGE" == *pc* || "$SRC_RANGE" == yuvj* ]]; then
  IN="$OUT/$NAME.tv.mp4"
  echo "=== 全範圍 → 標準範圍（無損）==="
  ffmpeg -v error -y -i "$SRC" -vf "scale=in_range=pc:out_range=tv,format=yuv420p" \
    -c:v libx264 -qp 0 -preset ultrafast -color_range tv -c:a copy "$IN"
fi

# preset 對應：Threads 借用 reels
for target in shorts:shorts reels:reels threads:reels; do
  label="${target%%:*}"
  preset="${target##*:}"
  raw="$OUT/$NAME-$label.raw.mp4"
  clean="$OUT/$NAME-$label.clean.mp4"
  final="$OUT/$NAME-$label.mp4"

  # 全形括號不是 bash 的分隔符，變數一定要包大括號，否則變數名會黏住後面的字
  echo "=== ${label}（preset ${preset}）==="
  # reels preset 會裁到 90 秒，那是舊規格；Meta 官方 Reels API 上限 15 分鐘、Threads 5 分鐘（france 10-20 125 秒差點被砍掉結尾）
  long=(); [ "$label" = shorts ] || long=(--allow-long)
  python3 "$FFMPEG_SKILL/export.py" "$IN" --preset "$preset" -o "$raw" --overwrite ${long[@]+"${long[@]}"}

  echo "--- 清元資料 ---"
  node "$SCRUB" run "$raw" -o "$clean"

  # IG 與 Threads 官方規格：MP4 不能有 edit list、moov 在前。ffmpeg 封裝預設會寫 elst。
  # 畫面不重編，元資料照 scrub 的結果帶過去。音訊 scrub 重編成 192k，官方規格寫 AAC 128 kbps，
  # 這裡再編一次；bitexact 讓 AAC 不寫 ffmpeg 版本號（scrub 同一招）。
  # AAC 再轉一代成 128k 會把真峰值推高：scam-map 2026-10-14 實測 -1.6 → +0.8 dBTP，
  # 先降音量 2.5 dB 再轉也只到 -0.8。所以 Shorts（不受 128k 限制）沿用 scrub 的 192k 不再轉；
  # reels／threads 改從混音原檔 out/mix.wav 只編一次，loudnorm 壓到 -14 LUFS／TP -2（實測 -2.0）。
  if [ "$label" = shorts ]; then
    amap=(-map 0); acodec=(-c:a copy)
  elif [ -f "$DIR/out/mix.wav" ]; then
    amap=(-i "$DIR/out/mix.wav" -map 0:v -map 1:a); acodec=(-af loudnorm=I=-14:TP=-2:LRA=11 -c:a aac -b:a 128k -ar 48000 -flags:a +bitexact -shortest)
  else
    echo "找不到 $DIR/out/mix.wav，$label 從成片音訊轉 128k，真峰值可能超標" >&2
    amap=(-map 0); acodec=(-c:a aac -b:a 128k -ar 48000 -flags:a +bitexact)
  fi
  ffmpeg -v error -y -i "$clean" "${amap[@]}" -c:v copy "${acodec[@]}" \
    -metadata:s:a:0 encoder= -map_metadata 0 -use_editlist 0 -movflags +faststart+negative_cts_offsets "$final"
  # negative_cts_offsets：B-frame 的顯示延遲原本靠 elst 抵銷，拿掉 elst 後畫面起點變 0.067s、
  # 比聲音晚 2 幀。改用負的 CTS 讓畫面仍從 0 開始。下面檢查影音起點一致。
  vs=$(ffprobe -v error -select_streams v:0 -show_entries stream=start_time -of csv=p=0 "$final")
  [ "$vs" = "0.000000" ] || { echo "$final 畫面起點 $vs，影音不同步" >&2; exit 1; }
  # 交付檔不准比成片短（被 preset 默默裁掉就會少結尾）
  python3 -c "import sys; a,b=map(float,sys.argv[1:]); sys.exit(abs(a-b)>0.2)" \
    "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SRC")" \
    "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$final")" \
    || { echo "$final 時長跟成片對不上，被裁了" >&2; exit 1; }
  rm -f "$raw" "$clean"
done
[ "$IN" = "$SRC" ] || rm -f "$IN"

echo
echo "=== 規格檢查 ==="
for label in shorts reels threads; do
  f="$OUT/$NAME-$label.mp4"
  plat=$([ "$label" = shorts ] && echo shorts || echo "reels --max-duration 300")
  # 只印出來不擋：true peak 這類 [judgement] 項目由人判斷；格式錯誤會被下面的 precheck 門擋
  python3 "$FFMPEG_SKILL/check.py" "$f" --platform $plat | grep -E "FAIL|checks" || true
  python3 -c "import sys; sys.exit(open('$f','rb').read(1<<20).count(b'elst'))" || { echo "$f 還有 edit list" >&2; exit 1; }
done

echo
echo "=== 交付檔 ==="
ls -lh "$OUT"/*.mp4 | awk '{print $9, $5}'
