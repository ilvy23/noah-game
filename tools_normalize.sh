#!/usr/bin/env bash
# Two-pass loudness normalisation of all soundtracks to the same level (-18 LUFS, true peak -1.5 dB).
# Writes a new file and renames it over the old one, so hard links to other copies are not touched.
set -u
cd "$(dirname "$0")/soundtracks"
I=-18; TP=-1.5; LRA=11
for f in *.flac; do
  out=$(ffmpeg -hide_banner -nostats -i "$f" -af "loudnorm=I=$I:TP=$TP:LRA=$LRA:print_format=json" -f null - 2>&1)
  mi=$(echo "$out" | grep '"input_i"' | sed 's/[^-0-9.]//g'); mtp=$(echo "$out" | grep '"input_tp"' | sed 's/[^-0-9.]//g')
  mlra=$(echo "$out" | grep '"input_lra"' | sed 's/[^-0-9.]//g'); mth=$(echo "$out" | grep '"input_thresh"' | sed 's/[^-0-9.]//g')
  off=$(echo "$out" | grep '"target_offset"' | sed 's/[^-0-9.]//g')
  ffmpeg -hide_banner -loglevel error -y -i "$f" -af "loudnorm=I=$I:TP=$TP:LRA=$LRA:measured_I=$mi:measured_TP=$mtp:measured_LRA=$mlra:measured_thresh=$mth:offset=$off:linear=true" -ar 44100 -c:a flac "tmp-$f" && mv "tmp-$f" "$f" && echo "ok $f (was $mi LUFS)"
done
# short effects: plain gain to -18 LUFS with a peak limiter
for f in *.mp3; do
  mi=$(ffmpeg -nostats -i "$f" -af ebur128 -f null - 2>&1 | awk '/I:/ {i=$2} END{print i}')
  g=$(python3 -c "print(round($I - ($mi), 2))")
  ffmpeg -hide_banner -loglevel error -y -i "$f" -af "volume=${g}dB,alimiter=limit=0.84" -c:a libmp3lame -q:a 2 "tmp-$f" && mv "tmp-$f" "$f" && echo "ok $f (gain ${g} dB)"
done
