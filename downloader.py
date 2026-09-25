"""
Downloads YouTube video metadata and subtitles using yt-dlp.
No video downloaded — subtitles only (fast, lightweight).
"""
import subprocess
import json
import tempfile
import os
from pathlib import Path
from dataclasses import dataclass

@dataclass
class VideoInfo:
    video_id: str
    title: str
    duration: int          # seconds
    url: str
    vtt_path: str | None   # path to downloaded VTT file

# Playlist Support:
def download_playlist_subtitles(playlist_url: str, output_dir: str = "output") -> list[VideoInfo]:
    """
    Download auto-generated English subtitles for all videos in a YouTube playlist.
    Returns a list of VideoInfo objects with paths to the VTT files.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Step 1: Get playlist metadata (no download)
    print(f"Fetching playlist info: {playlist_url}")
    meta_result = subprocess.run(
        [
            "yt-dlp",
            "--dump-json",       # print metadata as JSON
            "--flat-playlist",   # only get video IDs, no full metadata
            "--skip-download",
            playlist_url,
        ],
        capture_output=True,
        text=True,
    )

    if meta_result.returncode != 0:
        raise RuntimeError(f"yt-dlp playlist metadata failed: {meta_result.stderr}")

    videos = []
    for line in meta_result.stdout.strip().splitlines():
        video_meta = json.loads(line)
        video_id = video_meta["id"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        video_info = download_subtitles(video_url, output_dir)
        videos.append(video_info)

    return videos


def download_subtitles(url: str, output_dir: str = "output") -> VideoInfo:
    """
    Download auto-generated English subtitles for a YouTube video.
    Returns VideoInfo with path to the VTT file.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Step 1: Get video metadata (no download)
    print(f"Fetching video info: {url}")
    meta_result = subprocess.run(
        [
            "yt-dlp",
            "--dump-json",       # print metadata as JSON
            "--no-playlist",
            "--skip-download",
            url,
        ],
        capture_output=True,
        text=True,
    )

    if meta_result.returncode != 0:
        raise RuntimeError(f"yt-dlp metadata failed: {meta_result.stderr}")

    meta = json.loads(meta_result.stdout)
    video_id = meta["id"]
    title = meta["title"]
    duration = meta.get("duration", 0)

    # Step 2: Download subtitles
    print(f"Downloading subtitles for: '{title}' ({duration//60}m {duration%60}s)")
    sub_result = subprocess.run(
        [
            "yt-dlp",
            "--write-auto-sub",    # auto-generated captions
            "--write-sub",         # also get manual subs if available
            "--sub-lang", "en",    # English
            "--sub-format", "vtt", # WebVTT format (timestamped)
            "--skip-download",     # don't download video
            "--no-playlist",
            "-o", f"{output_dir}/{video_id}.%(ext)s",
            url,
        ],
        capture_output=True,
        text=True,
    )

    # Find the downloaded VTT file
    vtt_path = None
    for ext in [".en.vtt", ".en-US.vtt", ".en-GB.vtt"]:
        candidate = f"{output_dir}/{video_id}{ext}"
        if Path(candidate).exists():
            vtt_path = candidate
            break

    if not vtt_path:
        # Try glob for any .vtt file with the video ID
        vtt_files = list(Path(output_dir).glob(f"{video_id}*.vtt"))
        if vtt_files:
            vtt_path = str(vtt_files[0])

    if not vtt_path:
        print("Warning: No subtitles found. Video may not have captions.")
        print(f"yt-dlp stderr: {sub_result.stderr[-500:]}")

    return VideoInfo(
        video_id=video_id,
        title=title,
        duration=duration,
        url=url,
        vtt_path=vtt_path,
    )