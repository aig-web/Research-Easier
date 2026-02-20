import re
import tempfile
import os
import yt_dlp


def normalize_tweet_url(url):
    """Normalize twitter/x URLs to a consistent format."""
    url = url.strip()
    url = re.sub(r'\?.*$', '', url)
    url = url.replace("x.com", "twitter.com")
    match = re.search(r'twitter\.com/(\w+)/status/(\d+)', url)
    if match:
        return f"https://twitter.com/{match.group(1)}/status/{match.group(2)}"
    return url


def is_twitter_url(url):
    """Check if the URL is a valid Twitter/X link."""
    return bool(re.search(r'(twitter\.com|x\.com)/\w+/status/\d+', url))


def extract_tweet_data(url):
    """Extract tweet metadata and optionally download video using yt-dlp."""
    url = normalize_tweet_url(url)

    video_path = None
    temp_dir = tempfile.mkdtemp()

    ydl_opts = {
        'skip_download': False,
        'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),
        'format': 'best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'extractor_args': {'twitter': {'api': ['syndication']}},
    }

    # First try to extract info
    try:
        with yt_dlp.YoutubeDL({**ydl_opts, 'skip_download': True}) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        return {
            "success": False,
            "error": f"Could not extract tweet data: {str(e)}",
            "tweet_url": url,
        }

    if info is None:
        return {
            "success": False,
            "error": "No data returned from tweet extraction",
            "tweet_url": url,
        }

    tweet_text = info.get("description", "") or ""
    author = info.get("uploader", "") or ""
    author_handle = info.get("uploader_id", "") or info.get("uploader_url", "").split("/")[-1] or ""
    tweet_date = info.get("upload_date", "")
    if tweet_date and len(tweet_date) == 8:
        tweet_date = f"{tweet_date[:4]}-{tweet_date[4:6]}-{tweet_date[6:8]}"

    view_count = info.get("view_count")
    like_count = info.get("like_count")
    repost_count = info.get("repost_count")

    view_str = _format_count(view_count)
    has_video = info.get("ext") in ("mp4", "webm") or info.get("duration") is not None

    # Download video if present
    if has_video:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            for f in os.listdir(temp_dir):
                if f.endswith(('.mp4', '.webm', '.mkv')):
                    video_path = os.path.join(temp_dir, f)
                    break
        except Exception:
            has_video = False
            video_path = None

    return {
        "success": True,
        "tweet_url": url,
        "tweet_text": tweet_text,
        "author": author,
        "author_handle": author_handle,
        "tweet_date": tweet_date,
        "view_count": view_str,
        "like_count": _format_count(like_count),
        "repost_count": _format_count(repost_count),
        "has_video": has_video,
        "video_path": video_path,
        "temp_dir": temp_dir,
    }


def _format_count(count):
    if count is None:
        return "N/A"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)
