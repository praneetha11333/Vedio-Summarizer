# Lab 3 — YouTube Video Summarizer Pipeline

Converts any YouTube video into a structured JSON summary using subtitles and an LLM.

## What it does

Given a YouTube URL, the pipeline:
1. Downloads subtitles (no video download) using `yt-dlp`
2. Parses the `.vtt` subtitle file into timestamped segments
3. Extracts main topics from the transcript
4. Divides the video into logical chapters with timestamps
5. Generates Q&A pairs a viewer might ask
6. Saves everything as a structured JSON file

## Setup

1. Install dependencies:
```bash
uv sync
```

2. Add your API key to `.env`:
```
AIPIPE_API_KEY=<your_aipipe_key>
```

## Usage

```bash
uv run python pipeline.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Output is saved to `output/<video_id>_summary.json`.

## Output format

```json
{
  "video_id": "...",
  "title": "...",
  "url": "...",
  "duration_seconds": 3600,
  "duration_formatted": "01:00:00",
  "topics": ["topic1", "topic2"],
  "one_line_summary": "...",
  "chapters": [
    {
      "title": "Introduction",
      "start_time": "00:00",
      "end_time": "05:30",
      "summary": "...",
      "key_points": ["..."]
    }
  ],
  "qa_pairs": [
    {
      "question": "...",
      "answer": "...",
      "timestamp": "12:34",
      "confidence": 0.9
    }
  ],
  "total_segments": 320
}
```

## Project structure

| File | Purpose |
|------|---------|
| `pipeline.py` | Main entry point, orchestrates all steps |
| `downloader.py` | Downloads subtitles via `yt-dlp` |
| `vtt_parser.py` | Parses `.vtt` files into segments |
| `llm_processor.py` | All LLM calls (topics, chapters, Q&A) |
| `models.py` | Pydantic models for structured data |

## Model

Uses `o3-mini` via [aipipe.org](https://aipipe.org) (OpenAI proxy) with `reasoning_effort="low"` for all steps.
