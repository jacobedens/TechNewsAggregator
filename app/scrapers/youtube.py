"""YouTube scraper for fetching videos from RSS feeds and transcripts."""

import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from youtube_transcript_api import YouTubeTranscriptApi

# Import exceptions from the public API
# These are exported from the main package, not from the private _errors module
try:
    from youtube_transcript_api import (
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable,
        TooManyRequests,
    )
except ImportError:
    # Fallback if package structure differs - use generic Exception types
    # This should not occur with the standard youtube-transcript-api package
    TranscriptsDisabled = Exception
    NoTranscriptFound = Exception
    VideoUnavailable = Exception
    TooManyRequests = Exception


def get_channel_rss_url(channel_id: str) -> str:
    """
    Generate YouTube RSS feed URL from channel ID.
    
    YouTube RSS feed format: https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID
    
    Args:
        channel_id: YouTube channel ID (format: UCxxxxx, 24 characters starting with UC)
    
    Returns:
        RSS feed URL string
    
    Example:
        >>> get_channel_rss_url("UCSHZKyawb77ixDdsGog4iWA")
        'https://www.youtube.com/feeds/videos.xml?channel_id=UCSHZKyawb77ixDdsGog4iWA'
    """
    if not channel_id.startswith('UC'):
        raise ValueError(f"Invalid channel ID format. Must start with 'UC': {channel_id}")
    
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def parse_rss_feed(rss_url: str) -> List[Dict]:
    """
    Parse YouTube RSS feed and extract video information.
    
    Args:
        rss_url: RSS feed URL
    
    Returns:
        List of dictionaries containing video information:
        - title: Video title
        - url: Video URL
        - video_id: YouTube video ID
        - published_at: Published datetime (UTC)
        - description: Video description/summary
        - author: Channel name
        - link: Video link
    """
    feed = feedparser.parse(rss_url)
    
    if feed.bozo and feed.bozo_exception:
        raise ValueError(f"Failed to parse RSS feed: {feed.bozo_exception}")
    
    videos = []
    
    for entry in feed.entries:
        # Extract video ID from various possible fields
        video_id = None
        if hasattr(entry, 'yt_videoid'):
            video_id = entry.yt_videoid
        elif hasattr(entry, 'link'):
            # Extract from URL if needed
            video_id = _extract_video_id_from_url(entry.link)
        
        # Parse published date
        published_at = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                published_at = datetime(*entry.published_parsed[:6])
            except (TypeError, ValueError):
                pass
        
        video_data = {
            'title': entry.get('title', 'Untitled'),
            'url': entry.get('link', ''),
            'video_id': video_id,
            'published_at': published_at,
            'description': entry.get('summary', entry.get('description', '')),
            'author': entry.get('author', ''),
            'link': entry.get('link', ''),
        }
        videos.append(video_data)
    
    return videos


def _extract_video_id_from_url(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL if needed as fallback."""
    import re
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_video_transcript(video_id: str, languages: List[str] = ['en']) -> Optional[str]:
    """
    Fetch transcript for a YouTube video.
    
    Args:
        video_id: YouTube video ID (11 characters)
        languages: List of language codes to try in order (default: ['en'])
    
    Returns:
        Transcript text as a single string, or None if unavailable
    """
    if not video_id or len(video_id) != 11:
        return None
    
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try to get transcript in preferred languages
        for lang in languages:
            try:
                transcript = transcript_list.find_transcript([lang])
                transcript_data = transcript.fetch()
                # Combine all text segments into a single string
                return ' '.join([item['text'] for item in transcript_data])
            except (NoTranscriptFound, TranscriptsDisabled):
                continue
        
        # If preferred languages don't work, try any manually created transcript
        try:
            transcript = transcript_list.find_manually_created_transcript(['en'])
            transcript_data = transcript.fetch()
            return ' '.join([item['text'] for item in transcript_data])
        except (NoTranscriptFound, TranscriptsDisabled):
            pass
        
        # Try auto-generated transcript
        try:
            transcript = transcript_list.find_generated_transcript(['en'])
            transcript_data = transcript.fetch()
            return ' '.join([item['text'] for item in transcript_data])
        except (NoTranscriptFound, TranscriptsDisabled):
            pass
        
        return None
        
    except VideoUnavailable:
        print(f"Video {video_id} is unavailable")
        return None
    except TooManyRequests:
        print(f"Too many requests for video {video_id}")
        return None
    except Exception as e:
        print(f"Error fetching transcript for video {video_id}: {e}")
        return None


def filter_videos_by_time(videos: List[Dict], hours: int = 24) -> List[Dict]:
    """
    Filter videos published within the last N hours.
    
    Args:
        videos: List of video dictionaries with 'published_at' field
        hours: Number of hours to look back (default: 24)
    
    Returns:
        Filtered list of videos published within the time window
    """
    if not videos:
        return []
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    filtered = []
    for video in videos:
        published_at = video.get('published_at')
        if published_at and isinstance(published_at, datetime):
            if published_at >= cutoff_time:
                filtered.append(video)
    
    return filtered


def fetch_channel_videos(
    channel_id: str, 
    hours: int = 24, 
    get_transcripts: bool = False,
    languages: List[str] = ['en']
) -> List[Dict]:
    """
    Fetch recent videos from a YouTube channel and optionally get transcripts.
    
    Args:
        channel_id: YouTube channel ID (format: UCxxxxx)
        hours: Number of hours to look back for new videos (default: 24)
        get_transcripts: Whether to fetch video transcripts (default: False)
        languages: List of language codes for transcripts (default: ['en'])
    
    Returns:
        List of video dictionaries with optional 'transcript' field
    """
    rss_url = get_channel_rss_url(channel_id)
    all_videos = parse_rss_feed(rss_url)
    recent_videos = filter_videos_by_time(all_videos, hours=hours)
    
    if get_transcripts:
        for video in recent_videos:
            video_id = video.get('video_id')
            if video_id:
                transcript = get_video_transcript(video_id, languages=languages)
                video['transcript'] = transcript
            else:
                video['transcript'] = None
    
    return recent_videos


def fetch_multiple_channels(
    channel_ids: List[str], 
    hours: int = 24, 
    get_transcripts: bool = False,
    languages: List[str] = ['en']
) -> Dict[str, List[Dict]]:
    """
    Fetch videos from multiple YouTube channels.
    
    Args:
        channel_ids: List of YouTube channel IDs
        hours: Number of hours to look back (default: 24)
        get_transcripts: Whether to fetch transcripts (default: False)
        languages: List of language codes for transcripts (default: ['en'])
    
    Returns:
        Dictionary mapping channel_id to list of recent videos
    """
    results = {}
    
    for channel_id in channel_ids:
        try:
            videos = fetch_channel_videos(
                channel_id, 
                hours=hours, 
                get_transcripts=get_transcripts,
                languages=languages
            )
            results[channel_id] = videos
        except Exception as e:
            print(f"Error fetching videos for channel {channel_id}: {e}")
            results[channel_id] = []
    
    return results

