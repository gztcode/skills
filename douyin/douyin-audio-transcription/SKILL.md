---
name: douyin-audio-transcription
description: Use when processing Douyin video links to inspect subtitle availability, extract audio, transcribe Mandarin speech, or produce simplified-Chinese TXT/SRT/VTT captions on macOS Apple Silicon.
---

# Douyin Audio Transcription

Use a subtitle-first, audio-first pipeline for general video transcription. Do not infer that a video contains songs or create song reports unless the user explicitly requests that extension.

## Workflow

1. Verify `yt-dlp`, `ffmpeg`, `mlx-whisper`, and the `opencc-python-reimplemented` package. Use Chrome cookies when the source requires the user's logged-in session.
2. Check subtitles before media download:

   ```bash
   yt-dlp --cookies-from-browser chrome --list-subs "$URL"
   yt-dlp --cookies-from-browser chrome --dump-single-json --skip-download "$URL"
   ```

   Inspect `subtitles` and `automatic_captions`. This detects downloadable soft subtitles only, not text burned into video frames. An empty subtitle list is a normal branch, not a fatal error.
3. If subtitles exist, download the selected subtitle formats/languages and convert them with `scripts/convert_subtitles.py`. Do not download MP4 or audio unnecessarily.
4. If no subtitles exist, extract audio only. Set `OUT` to the current project root: use `git rev-parse --show-toplevel` when available, otherwise the current working directory. Resolve the outer directory name from the video title before downloading: keep only the primary title before the first `#`, trim whitespace, sanitize filesystem characters, and fall back to the video ID if the result is empty.

   ```bash
   VIDEO_ID="$(yt-dlp --cookies-from-browser chrome --print id --skip-download "$URL" | tail -1)"
   RAW_TITLE="$(yt-dlp --cookies-from-browser chrome --print title --skip-download "$URL" | tail -1)"
   MAIN_TITLE="${RAW_TITLE%%#*}"
   MAIN_TITLE="$(printf '%s' "$MAIN_TITLE" | sed 's/[[:space:]]*$//' | sed 's#[/:?*\\]#_#g')"
   [ -n "$MAIN_TITLE" ] || MAIN_TITLE="$VIDEO_ID"
   VIDEO_DIR="$OUT/douyin/$MAIN_TITLE [$VIDEO_ID]"
   mkdir -p "$VIDEO_DIR/音频"
   yt-dlp --cookies-from-browser chrome -x --audio-format m4a \
     -o "$VIDEO_DIR/音频/$MAIN_TITLE.%(ext)s" "$URL"
   ```

5. Run MLX Whisper and produce an intermediate SRT:

   ```bash
   mlx_whisper "$AUDIO" --model mlx-community/whisper-small-mlx \
     --language Chinese --output-format srt --output-dir "$CAPTION_DIR"
   ```

   Use `base` or a larger model only when the actual machine's resources or accuracy needs justify it. If Hugging Face times out, retry with:

   ```bash
   HF_ENDPOINT=https://hf-mirror.com mlx_whisper "$AUDIO" \
     --model mlx-community/whisper-small-mlx \
     --language Chinese --output-format srt --output-dir "$CAPTION_DIR"
   ```

6. Convert the intermediate SRT into all required simplified-Chinese outputs:

   ```bash
   python3 scripts/convert_subtitles.py \
     --input "$CAPTION_DIR/<video-id>.srt" \
     --output-dir "$CAPTION_DIR" \
     --simplified --name "$MAIN_TITLE"
   ```

   The script creates `<主标题>.txt`, `<主标题>.srt`, and `<主标题>.vtt`, preserving timestamps in SRT/VTT and applying OpenCC `t2s` to all text. The intermediate SRT may use the video ID; final media and caption filenames use only the primary title.
7. Only if the user explicitly needs burned-in visual text and ASR is insufficient, download MP4, sample frames, and use OCR. `ffmpeg` extracts frames; it does not perform OCR.

## Output Layout

```text
<project-root>/douyin/
└── 视频标题 [视频ID]/
    ├── 音频/
    │   └── 视频标题.m4a
    └── 字幕/
        ├── 视频标题.txt
        ├── 视频标题.srt
        └── 视频标题.vtt
```

Use the same sanitized primary title for the audio, video, and final caption filenames. The outer directory remains `<主标题> [视频ID]` so duplicate titles stay distinct. Strip the hashtag suffix beginning at the first `#`; do not include topic tags. If title metadata is empty, inaccessible, too long, or sanitizes to an empty string, use the video ID for both directory and filenames. Do not use `--restrict-filenames`; it discards useful Chinese title text. Sanitize `/`, `:`, `?`, `*`, `\\`, control characters, and trailing dots/spaces for macOS compatibility, and check before overwriting.

## Resources

- `scripts/convert_subtitles.py`: deterministic SRT -> simplified TXT/SRT/VTT conversion. Call this script instead of generating ad-hoc Python snippets.

## Accuracy and Safety

- Missing soft subtitles does not prove hard subtitles are absent.
- Validate input paths before starting ASR; a missing audio file is a workflow error, not a reason to silently skip output.
- Whisper may misrecognize names and terminology; retain timestamps and flag uncertain text when relevant.
- Do not upload private or logged-in content to third-party transcription services.
- Process only content the user is authorized to download and analyze.
- Have the user complete login or CAPTCHA in their browser; never handle passwords or OTP codes.
