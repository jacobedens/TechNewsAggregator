"""Service for fetching YouTube video transcripts."""

from typing import Optional
from youtube_transcript_api import YouTubeTranscriptApi


def get_transcript(video_id: str) -> Optional[str]:
    """Get transcript for a YouTube video as plain text."""
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)
        return transcript
    except Exception:
        return None

if __name__ == "__main__":
    print(get_transcript("dTTLsmaVqBk"))
    
    ytt_api = YouTubeTranscriptApi()
    result = ytt_api.fetch("dTTLsmaVqBk") 