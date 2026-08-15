#!/usr/bin/env python3
"""Convert an SRT caption file to simplified TXT, SRT, and WebVTT."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from opencc import OpenCC


def parse_srt(text: str) -> list[tuple[str, str, str]]:
    blocks: list[tuple[str, str, str]] = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip()):
        lines = block.splitlines()
        if len(lines) >= 3 and "-->" in lines[1]:
            blocks.append((lines[0].strip(), lines[1].strip(), "\n".join(lines[2:]).strip()))
    return blocks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--simplified", action="store_true")
    args = parser.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"Input subtitle file not found: {args.input}")

    blocks = parse_srt(args.input.read_text(encoding="utf-8"))
    if not blocks:
        raise SystemExit(f"No valid SRT blocks found: {args.input}")

    converter = OpenCC("t2s") if args.simplified else None

    def convert(value: str) -> str:
        return converter.convert(value) if converter else value

    converted = [(number, timing, convert(caption)) for number, timing, caption in blocks]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.input.stem

    (args.output_dir / f"{stem}.txt").write_text(
        "\n".join(caption.replace("\n", " ") for _, _, caption in converted) + "\n",
        encoding="utf-8",
    )

    srt = "\n\n".join(f"{number}\n{timing}\n{caption}" for number, timing, caption in converted) + "\n"
    (args.output_dir / f"{stem}.srt").write_text(srt, encoding="utf-8")

    vtt = "WEBVTT\n\n" + "\n\n".join(
        f"{number}\n{timing.replace(',', '.')}\n{caption}"
        for number, timing, caption in converted
    ) + "\n"
    (args.output_dir / f"{stem}.vtt").write_text(vtt, encoding="utf-8")


if __name__ == "__main__":
    main()
