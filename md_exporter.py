"""
Converts a VideoSummary into a Docusaurus-ready Markdown file.
"""
from models import VideoSummary


def summary_to_markdown(summary: VideoSummary) -> str:
    lines = []

    # ── Docusaurus frontmatter ─────────────────────────────────────────────────
    lines += [
        "---",
        f"title: \"{summary.title.replace(chr(34), chr(39))}\"",
        f"description: \"{summary.one_line_summary.replace(chr(34), chr(39))}\"",
        f"tags: [{', '.join(f'\"{t}\"' for t in summary.topics)}]",
        f"duration: \"{summary.duration_formatted}\"",
        f"video_url: \"{summary.url}\"",
        "---",
        "",
    ]

    # ── Header ─────────────────────────────────────────────────────────────────
    lines += [
        f"# {summary.title}",
        "",
        f"> {summary.one_line_summary}",
        "",
        f"**Duration:** {summary.duration_formatted} &nbsp;|&nbsp; **Topics:** {', '.join(summary.topics)}",
        "",
        f"[▶ Watch on YouTube]({summary.url})",
        "",
    ]

    # ── Chapters ───────────────────────────────────────────────────────────────
    lines += ["## Chapters", ""]
    for ch in summary.chapters:
        lines += [
            f"### {ch.title}",
            f"`{ch.start_time}` – `{ch.end_time}`",
            "",
            ch.summary,
            "",
        ]
        if ch.key_points:
            for point in ch.key_points:
                lines.append(f"- {point}")
            lines.append("")

    # ── Q&A ────────────────────────────────────────────────────────────────────
    lines += ["## Q&A", ""]
    for qa in summary.qa_pairs:
        lines += [
            f"**Q: {qa.question}**",
            "",
            f"{qa.answer}",
            "",
            f"*Timestamp: [{qa.timestamp}]({summary.url}&t={_to_seconds(qa.timestamp)})*",
            "",
        ]

    return "\n".join(lines)


def _to_seconds(timestamp: str) -> int:
    """Convert MM:SS or HH:MM:SS to total seconds for YouTube URL ?t= param."""
    parts = list(map(int, timestamp.split(":")))
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]
