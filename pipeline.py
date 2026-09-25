"""
Main pipeline: YouTube URL → structured JSON summary.

Usage:
    python pipeline.py "https://youtube.com/watch?v=VIDEO_ID"
    python pipeline.py "https://youtube.com/watch?v=VIDEO_ID" --output my_output.json
"""
import sys
import time
import argparse
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from dotenv import load_dotenv

load_dotenv()

from downloader import download_subtitles, download_playlist_subtitles
from md_exporter import summary_to_markdown
from vtt_parser import parse_vtt, segments_to_transcript
from llm_processor import (
    extract_topics,
    create_chapters,
    extract_qa_pairs,
    build_final_summary,
)

console = Console()

def _safe_output_dir(output_dir: str) -> Path:
    """Resolve output_dir and ensure it stays within the current working directory."""
    base = Path.cwd().resolve()
    resolved = (base / output_dir).resolve()
    if not str(resolved).startswith(str(base)):
        raise ValueError(f"Invalid output directory: {output_dir!r} escapes the working directory.")
    return resolved


def run_pipeline(url: str, output_dir: str = "output") -> dict:
    """Run the full pipeline for a YouTube URL."""
    start_time = time.time()
    safe_dir = _safe_output_dir(output_dir)
    safe_dir.mkdir(exist_ok=True)

    # ── Step 1: Download subtitles ─────────────────────────────────────────────
    console.rule("[bold blue]Step 1: Downloading subtitles")
    video_info = download_subtitles(url, str(safe_dir))

    if not video_info.vtt_path:
        console.print("[red]❌ No subtitles found. Cannot proceed.[/red]")
        console.print("Try a video with auto-generated captions (most English YT videos have them).")
        sys.exit(1)

    console.print(f"[green]✅ Downloaded:[/green] {video_info.title}")
    console.print(f"   Duration: {video_info.duration // 60}m {video_info.duration % 60}s")
    console.print(f"   VTT file: {video_info.vtt_path}")

    # ── Step 2: Parse VTT ─────────────────────────────────────────────────────
    console.rule("[bold blue]Step 2: Parsing subtitles")
    segments = parse_vtt(video_info.vtt_path)
    console.print(f"[green]✅ Parsed {len(segments)} segments[/green]")

    if len(segments) < 10:
        console.print("[yellow]⚠️  Very few segments — subtitle quality may be low.[/yellow]")

    # Preview
    console.print("\nFirst 3 segments:")
    for seg in segments[:3]:
        console.print(f"  [{seg.start_formatted}] {seg.text[:80]}")

    # ── Step 3: Extract Topics ─────────────────────────────────────────────────
    console.rule("[bold blue]Step 3: Extracting topics ")
    topic_result = extract_topics(segments, video_info.title)
    console.print(f"[green]✅ Topics:[/green] {', '.join(topic_result.topics)}")
    console.print(f"   Summary: {topic_result.one_line_summary}")

    # ── Step 4: Create Chapters ────────────────────────────────────────────────
    console.rule("[bold blue]Step 4: Creating chapters ")
    chapters = create_chapters(segments, video_info.title, topic_result.topics)
    console.print(f"[green]✅ Created {len(chapters)} chapters[/green]")
    for ch in chapters:
        console.print(f"  [{ch.start_time}] {ch.title}")

    # ── Step 5: Extract Q&A Pairs ──────────────────────────────────────────────
    console.rule("[bold blue]Step 5: Extracting Q&A pairs")
    qa_pairs = extract_qa_pairs(segments, video_info.title, topic_result.topics)
    console.print(f"[green]✅ Extracted {len(qa_pairs)} Q&A pairs[/green]")
    for qa in qa_pairs[:3]:
        console.print(f"  Q [{qa.timestamp}]: {qa.question[:70]}")

    # ── Step 6: Build Final Summary ────────────────────────────────────────────
    console.rule("[bold blue]Step 6: Assembling final summary")
    summary = build_final_summary(video_info, segments, topic_result, chapters, qa_pairs)

    # Save output
    output_path = safe_dir / f"{video_info.video_id}.md"
    output_path.write_text(summary_to_markdown(summary), encoding="utf-8")
    output_dict = summary.model_dump()

    elapsed = time.time() - start_time
    console.rule("[bold green]✅ Pipeline Complete")
    console.print(f"Output saved to: [bold]{output_path}[/bold]")
    console.print(f"Total time: {elapsed:.1f}s")
    console.print(f"Chapters: {len(chapters)}, Q&A pairs: {len(qa_pairs)}")

    return output_dict

def is_playlist(url: str) -> bool:
    return "list=" in url


def run_playlist_pipeline(playlist_url: str, output_dir: str = "output") -> list[dict]:
    """Run the pipeline for every video in a YouTube playlist."""
    console.print(f"[bold]📋 Detected playlist URL[/bold]")
    video_infos = download_playlist_subtitles(playlist_url, output_dir)
    console.print(f"[green]✅ Found {len(video_infos)} videos in playlist[/green]")

    results = []
    for i, video_info in enumerate(video_infos, 1):
        console.rule(f"[bold cyan]Video {i}/{len(video_infos)}: {video_info.title}")
        result = run_pipeline(video_info.url, output_dir)
        results.append(result)

    console.rule("[bold green]✅ Playlist Complete")
    console.print(f"Processed {len(results)} videos. Outputs saved to: [bold]{output_dir}/[/bold]")
    return results


def main():
    parser = argparse.ArgumentParser(
        description="YouTube → Subtitles → Structured JSON Pipeline"
    )
    parser.add_argument("url", help="YouTube video or playlist URL")
    parser.add_argument("--output", default="output", help="Output directory (default: output/)")
    args = parser.parse_args()

    console.print(f"\n[bold]🎬 TDS Lab 3.1 — YouTube Pipeline[/bold]")
    console.print(f"URL: {args.url}\n")

    if is_playlist(args.url):
        run_playlist_pipeline(args.url, args.output)
    else:
        result = run_pipeline(args.url, args.output)
        console.print(f"\n[dim]JSON keys: {list(result.keys())}[/dim]")

if __name__ == "__main__":
    main()