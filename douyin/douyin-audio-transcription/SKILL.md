---
name: douyin-audio-transcription
description: Use when processing Douyin video links to find subtitles, extract audio, transcribe Mandarin speech, identify songs, or produce timestamped subtitle and Markdown reports on macOS Apple Silicon.
---

# Douyin Audio Transcription

Use a subtitle-first, audio-first pipeline. Avoid downloading a full MP4 or running OCR unless cheaper sources cannot provide the requested text.

## Workflow

1. Verify `yt-dlp`, `ffmpeg`, and `mlx-whisper`; use Chrome cookies when login is required.
2. Check subtitles before media download:

   ```bash
   yt-dlp --cookies-from-browser chrome --list-subs "$URL"
   ```

   Also inspect `subtitles` and `automatic_captions` from `--dump-single-json --skip-download`. This detects downloadable soft subtitles only, not burned-in text.
3. If subtitles exist, download only the selected subtitle formats/languages; do not download MP4 or audio unnecessarily.
4. If no subtitles exist, extract audio only:

   ```bash
   # Resolve title first; use a sanitized title as the per-video folder,
   # falling back to %(id)s when title is missing or unusable.
   # Set OUT to the current project's root (git root when available).
   yt-dlp --cookies-from-browser chrome -x --audio-format m4a \
     -o "$OUT/douyin/%(title)s [%(id)s]/音频/%(id)s.%(ext)s" "$URL"
   ```

5. Run Apple Silicon ASR with MLX:

   ```bash
   mlx_whisper "$AUDIO" --model mlx-community/whisper-small-mlx \
     --language Chinese --output-format srt
   ```

   Use `small` as the default accuracy/latency balance for Mandarin song titles. Select `base` or a larger model according to the actual machine's available memory and speed; do not assume or encode a specific computer configuration. Models download once and cache locally.

   If Hugging Face times out, retry with the reachable mirror before changing models:

   ```bash
   HF_ENDPOINT=https://hf-mirror.com mlx_whisper "$AUDIO" \
     --model mlx-community/whisper-small-mlx \
     --language Chinese --output-format srt
   ```

   A successful first download caches the model locally; subsequent runs do not need the network.
   The required deliverables are all three formats: `TXT`, `SRT`, and `VTT`. Generate `SRT` from MLX, derive plain `TXT` from caption text, and derive `VTT` from the same timestamps. `mlx-whisper` may emit Traditional Chinese; convert all three outputs with OpenCC (`t2s`) while preserving timestamps. Install with `python3 -m pip install --user opencc-python-reimplemented`; never silently deliver Traditional Chinese when Simplified Chinese was requested.
6. Only if ASR cannot resolve a song title/artist, download MP4, sample frames, and OCR likely text frames. `ffmpeg` extracts frames; it does not OCR.
7. Generate Markdown columns: `序号`, `歌曲名称`, `作者名称`, `时间点`, `来源/置信度`. Preserve timestamps and mark inferred or unresolved entries.

## Output Layout

```text
<project-root>/douyin/
├── 视频标题 A [视频ID]/
│   ├── 音频/
│   ├── 字幕/
│   ├── 视频/       # only for OCR fallback
│   └── 抖音歌曲清单.md
├── 视频标题 B [视频ID]/
│   └── ...
└── （每条视频一个独立目录）
```

Resolve `<project-root>` with `git rev-parse --show-toplevel`; if the current directory is not inside a Git repository, use the current working directory. Do not default to `~/Desktop` or another fixed user directory. Keep all generated files inside the current project unless the user explicitly chooses another output root.

Prefer the fetched video `title` for the outer directory. Do not use `--restrict-filenames`, because it discards useful Chinese title text. If title metadata is empty, inaccessible, too long, or sanitizes to an empty string, use the video ID. Sanitize `/`, `:`, `?`, `*`, `\\`, control characters, and trailing dots/spaces for macOS compatibility; cap the directory name at a practical length and retain the ID to avoid collisions. Check before overwriting existing files.

## Accuracy and Safety

- Missing soft subtitles does not prove hard subtitles are absent.
- Whisper may misrecognize Chinese names and titles; retain timestamps and flag uncertain entries.
- Do not upload private or logged-in content to third-party transcription services.
- Process only content the user is authorized to download and analyze.
- Have the user complete login or CAPTCHA in their browser; never handle passwords or OTP codes.
