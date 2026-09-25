from pydantic import BaseModel, Field
from typing import Optional

class TimeRange(BaseModel):
    start: str = Field(description="Timestamp in HH:MM:SS or MM:SS format")
    end: str = Field(description="Timestamp in HH:MM:SS or MM:SS format")
    
    
class Chapter(BaseModel):
    title: str = Field(description="Short title for this chapter/section")
    start_time: str = Field(description="When this chapter starts, e.g. '05:30'")
    end_time: str = Field(description="When this chapter ends")
    summary: str = Field(
        max_length=300,
        description="2-3 sentence summary of what's covered in this chapter"
    )
    key_points: list[str] = Field(
        min_length=1,
        max_length=5,
        description="3-5 key points from this chapter"
    )

class QAPair(BaseModel):
    question: str = Field(description="A question a viewer might ask about this content")
    answer: str = Field(description="The answer found in the transcript")
    timestamp: str = Field(description="When this answer appears, e.g. '12:34'")
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="How confident you are this timestamp is accurate"
    )

class SubtitleSegment(BaseModel):
    """One timestamped line from a VTT file."""
    text: str
    start_seconds: float
    end_seconds: float
    start_formatted: str  # "MM:SS" or "HH:MM:SS"

class VideoSummary(BaseModel):
    """The complete structured summary of a video."""
    video_id: str
    title: str
    url: str
    duration_seconds: int
    duration_formatted: str
    language: str = "en"
    topics: list[str] = Field(
        min_length=1,
        max_length=15,
        description="Main topics covered in the video"
    )
    one_line_summary: str = Field(
        max_length=150,
        description="One sentence capturing what the video is about"
    )
    chapters: list[Chapter] = Field(
        min_length=1,
        max_length=20
    )
    qa_pairs: list[QAPair] = Field(
        min_length=3,
        max_length=10,
        description="Questions a viewer would have, with answers from the transcript"
    )
    total_segments: int
    processing_notes: Optional[str] = None 

#Playlist of all the models defined in this file
class VideoSummaryPlaylist(BaseModel):
    """A playlist of video summaries."""
    playlist_url: str
    videos: list[VideoSummary] = Field(
        min_length=1,
        description="List of video summaries in the playlist"
    )