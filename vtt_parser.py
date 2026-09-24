"""
Parse WebVTT subtitle files into clean, deduplicated, timestamped segments.
"""
import re
from models import SubtitleSegment

def parse_vtt(vtt_path: str) -> list[SubtitleSegment]:
    """
    Parse a VTT file into timestamped text segments.
    Handles: duplicates, overlapping timestamps, multi-line cues.
    """
    content = open(vtt_path, encoding="utf-8", errors="replace").read()
    segments = _parse_raw(content)
    segments = _deduplicate(segments)
    segments = _merge_short_segments(segments, min_chars=20)
    return segments

def _timestamp_to_seconds(ts: str) -> float:
    """Convert '01:23:45.678' or '01:23.456' to seconds."""
    ts = ts.strip()
    parts = ts.replace(",", ".").split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    else:
        return float(parts[0])

def _seconds_to_formatted(seconds: float) -> str:
    """Convert 125.5 to '02:05'."""
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def _parse_raw(content: str) -> list[SubtitleSegment]:
    """Extract all cues from VTT content."""
    segments = []

    # Remove VTT header and metadata lines
    lines = content.split("\n")
    i = 0
    while i < len(lines) and not "-->" in lines[i]:
        i += 1

    # Parse each cue
    while i < len(lines):
        line = lines[i].strip()

        if "-->" in line:
            # Parse timestamp line: "00:01:23.000 --> 00:01:25.500"
            match = re.match(
                r"(\d{1,2}:\d{2}[:.]\d{3}|\d{2}:\d{2}:\d{2}[.:]\d{3})"
                r"\s*-->\s*"
                r"(\d{1,2}:\d{2}[:.]\d{3}|\d{2}:\d{2}:\d{2}[.:]\d{3})",
                line,
            )
            if match:
                start_ts, end_ts = match.group(1), match.group(2)
                start_sec = _timestamp_to_seconds(start_ts)
                end_sec = _timestamp_to_seconds(end_ts)

                # Collect text lines until blank line
                i += 1
                text_lines = []
                while i < len(lines) and lines[i].strip():
                    t = lines[i].strip()
                    # Remove VTT formatting tags: <c>, <00:00:01.000>, etc.
                    t = re.sub(r"<[^>]+>", "", t)
                    if t:
                        text_lines.append(t)
                    i += 1

                text = " ".join(text_lines).strip()
                if text:
                    segments.append(SubtitleSegment(
                        text=text,
                        start_seconds=start_sec,
                        end_seconds=end_sec,
                        start_formatted=_seconds_to_formatted(start_sec),
                    ))
        i += 1

    return segments

def _deduplicate(segments: list[SubtitleSegment]) -> list[SubtitleSegment]:
    """Remove consecutive duplicate lines (VTT often repeats the same text)."""
    if not segments:
        return []

    result = [segments[0]]
    for seg in segments[1:]:
        # Skip if identical text to previous (common in auto-generated captions)
        if seg.text.strip().lower() != result[-1].text.strip().lower():
            result.append(seg)

    return result

def _merge_short_segments(
    segments: list[SubtitleSegment],
    min_chars: int = 20,
    max_gap_seconds: float = 3.0,
) -> list[SubtitleSegment]:
    """
    Merge very short segments with the next one.
    Avoids sending "OK" or "Yeah" as separate chunks to the LLM.
    """
    if not segments:
        return []

    merged = []
    current = segments[0]

    for next_seg in segments[1:]:
        gap = next_seg.start_seconds - current.end_seconds
        if len(current.text) < min_chars and gap < max_gap_seconds:
            # Merge: append text, extend end time
            current = SubtitleSegment(
                text=current.text + " " + next_seg.text,
                start_seconds=current.start_seconds,
                end_seconds=next_seg.end_seconds,
                start_formatted=current.start_formatted,
            )
        else:
            merged.append(current)
            current = next_seg

    merged.append(current)
    return merged

def segments_to_transcript(segments: list[SubtitleSegment]) -> str:
    """Convert segments to a plain text transcript with timestamps."""
    lines = []
    for seg in segments:
        lines.append(f"[{seg.start_formatted}] {seg.text}")
    return "\n".join(lines)

def chunk_segments(
    segments: list[SubtitleSegment],
    max_chars: int = 8000,
) -> list[list[SubtitleSegment]]:
    """
    Split segments into chunks that fit within the LLM context.
    Each chunk is a list of SubtitleSegments.
    """
    chunks = []
    current_chunk = []
    current_chars = 0

    for seg in segments:
        seg_chars = len(seg.text) + 15  # +15 for timestamp
        if current_chars + seg_chars > max_chars and current_chunk:
            chunks.append(current_chunk)
            current_chunk = [seg]
            current_chars = seg_chars
        else:
            current_chunk.append(seg)
            current_chars += seg_chars

    if current_chunk:
        chunks.append(current_chunk)

    return chunks