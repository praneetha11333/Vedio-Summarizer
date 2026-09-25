"""
All LLM calls for the YouTube pipeline.
"""
import os
import openai
import instructor
from pydantic import BaseModel, Field
from typing import Optional
from models import Chapter, QAPair, SubtitleSegment, VideoSummary, VideoSummaryPlaylist
from vtt_parser import segments_to_transcript, chunk_segments, download_and_parse_playlist

# Use Instructor for structured output
_openai_client = openai.OpenAI(
    api_key=os.environ["AIPIPE_API_KEY"],
    base_url="https://aipipe.org/openai/v1",
)
open_ai = instructor.from_openai(_openai_client)
'''raw_open_ai = _openai_client()'''

# ── Step 1: Extract Topics ─────────────────────────────────────────────────────

class TopicList(BaseModel):
    topics: list[str] = Field(
        min_length=3,
        max_length=15,
        description="Main topics covered in the video, in order of appearance"
    )
    one_line_summary: str = Field(
        max_length=150,
        description="One sentence capturing what the video is about"
    )

def extract_topics(segments: list[SubtitleSegment], title: str) -> TopicList:
    """Extract the main topics from the first 1/3 of the transcript."""
    # Use the first third of segments for topic extraction (efficient)
    sample_size = max(30, len(segments) // 3)
    sample_segments = segments[:sample_size]
    transcript_sample = segments_to_transcript(sample_segments)

    return open_ai.messages.create(
        model="o3-mini",
        max_completion_tokens=512,
        reasoning_effort="low",
        messages=[{
            "role": "user",
            "content": f"""Video title: "{title}"

Transcript sample (first part of video):
{transcript_sample}

Extract the main topics covered in this video. Be specific and technical."""
        }],
        response_model=TopicList,
    )

# ── Step 2: Create Chapter Breakdown ──────────────────────────────────────────

class ChapterList(BaseModel):
    chapters: list[Chapter] = Field(min_length=2, max_length=20)

def create_chapters(
    segments: list[SubtitleSegment],
    title: str,
    topics: list[str],
) -> list[Chapter]:
    """
    Divide the video into logical chapters with timestamps.
    For long videos, processes in chunks and merges.
    """
    # Chunk the transcript for long videos
    chunks = chunk_segments(segments, max_chars=6000)

    if len(chunks) == 1:
        return _create_chapters_single(segments_to_transcript(segments), title, topics)

    # Process each chunk independently, then merge
    all_chapters = []
    for i, chunk in enumerate(chunks):
        print(f"  Processing chapter chunk {i+1}/{len(chunks)}...")
        transcript_chunk = segments_to_transcript(chunk)
        chunk_start = chunk[0].start_formatted
        chunk_end = chunk[-1].start_formatted

        result = open_ai.messages.create(
            model="o3-mini",
            max_completion_tokens=2048,
            reasoning_effort="low",
            messages=[{
                "role": "user",
                "content": f"""Video section from {chunk_start} to {chunk_end}.
Video title: "{title}"
Topics: {', '.join(topics)}

Transcript:
{transcript_chunk}

Identify 2-4 logical chapters in this section with timestamps."""
            }],
            response_model=ChapterList,
        )
        all_chapters.extend(result.chapters)

    return all_chapters

def _create_chapters_single(transcript: str, title: str, topics: list[str]) -> list[Chapter]:
    result = open_ai.messages.create(
        model="o3-mini",
        max_completion_tokens=2048,
        reasoning_effort="low",
        messages=[{
            "role": "user",
            "content": f"""Video title: "{title}"
Topics covered: {', '.join(topics)}

Full transcript with timestamps:
{transcript}

Divide this video into 3-8 logical chapters. Each chapter should cover a distinct topic or phase of the video.
Use the exact timestamps from the transcript."""
        }],
        response_model=ChapterList,
    )
    return result.chapters

# ── Step 3: Extract Q&A Pairs ─────────────────────────────────────────────────

class QAList(BaseModel):
    qa_pairs: list[QAPair] = Field(min_length=3, max_length=10)

def extract_qa_pairs(
    segments: list[SubtitleSegment],
    title: str,
    topics: list[str],
) -> list[QAPair]:
    """Extract questions a viewer might ask, with answers from the transcript."""
    # Use a focused sample — most Q&A content is in the middle
    start = len(segments) // 6
    end = len(segments) * 5 // 6
    sample = segments[start:end][:80]  # up to 80 segments
    transcript = segments_to_transcript(sample)

    result = open_ai.messages.create(
        model="o3-mini",
        max_completion_tokens=2048,
        reasoning_effort="low",
        messages=[{
            "role": "user",
            "content": f"""Video title: "{title}"
Topics: {', '.join(topics)}

Transcript excerpt with timestamps:
{transcript}

Generate 5-8 question-answer pairs that a viewer watching this video would find valuable.
For each Q&A, provide the timestamp where the answer is given in the video.
Focus on the most educational and practical information."""
        }],
        response_model=QAList,
    )
    return result.qa_pairs

# playlist support
def process_playlist(playlist_url: str, output_dir: str = "output") -> VideoSummaryPlaylist:
    """
    Process all videos in a YouTube playlist and create a structured summary.
    """
    all_segments = download_and_parse_playlist(playlist_url, output_dir)
    video_summaries = []

    for segments in all_segments:
        if not segments:
            continue  # Skip videos with no subtitles
        for video_info in segments:
            topics_result = extract_topics(segments, video_info.title)
            chapters = create_chapters(segments, video_info.title, topics_result.topics)
            qa_pairs = extract_qa_pairs(segments, video_info.title, topics_result.topics)

            summary = build_final_summary(
                video_info=video_info,
                segments=segments,
                topic_result=topics_result,
                chapters=chapters,
                qa_pairs=qa_pairs,
            )
            video_summaries.append(summary)
        pass

    return VideoSummaryPlaylist(
        playlist_url=playlist_url,
        videos=video_summaries
    )

# ── Step 4: Final Structured Summary ──────────────────────────────────────────

def build_final_summary(
    video_info,              # VideoInfo from downloader
    segments: list[SubtitleSegment],
    topic_result: TopicList,
    chapters: list[Chapter],
    qa_pairs: list[QAPair],
) -> VideoSummary:
    """Assemble all extracted data into the final VideoSummary."""
    duration = video_info.duration
    h = duration // 3600
    m = (duration % 3600) // 60
    s = duration % 60
    duration_fmt = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

    return VideoSummary(
        video_id=video_info.video_id,
        title=video_info.title,
        url=video_info.url,
        duration_seconds=duration,
        duration_formatted=duration_fmt,
        topics=topic_result.topics,
        one_line_summary=topic_result.one_line_summary,
        chapters=chapters,
        qa_pairs=qa_pairs,
        total_segments=len(segments),
    )