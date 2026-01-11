"""Test script for YouTube scraper functionality."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.scrapers.youtube import fetch_channel_videos, get_channel_rss_url


def main():
    """Test fetching videos from a single channel."""
    # Replace with your channel ID for testing
    channel_id = "UCrM7B7SL_g1edFOnmj-SDKg"
    
    print(f"Channel ID: {channel_id}")
    print(f"RSS Feed: {get_channel_rss_url(channel_id)}")
    print(f"\nFetching videos from the last 24 hours...\n")
    
    try:
        videos = fetch_channel_videos(channel_id, hours=24, get_transcripts=False)
        
        if videos:
            video = videos[0]  # Get first video
            print(f"✅ Found {len(videos)} video(s)")
            print(f"\nFirst video:")
            print(f"  Title: {video['title']}")
            print(f"  Published: {video['published_at']}")
            print(f"  URL: {video['url']}")
            print(f"  Video ID: {video['video_id']}")
        else:
            print("ℹ️  No videos found in the last 24 hours")
            
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
