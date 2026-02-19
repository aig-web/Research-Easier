"""Video downloader module using yt-dlp.

Supports downloading videos from virtually any platform including
Instagram, Twitter/X, Threads, YouTube, TikTok, Facebook, Reddit, and more.
"""

import uuid
from pathlib import Path

import yt_dlp

from src.utils import ensure_download_dir, detect_platform


def get_yt_dlp_opts(output_dir: Path, filename: str) -> dict:
    """Build yt-dlp options for reliable video downloading."""
    return {
        "outtmpl": str(output_dir / f"{filename}.%(ext)s"),
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 5,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        },
        "postprocessors": [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ],
    }


def download_video(
    url: str,
    output_dir: str = "downloads",
    cookies_file: str | None = None,
    progress_callback=None,
) -> dict:
    """Download a video from the given URL.

    Args:
        url: The video URL to download.
        output_dir: Directory to save the downloaded video.
        cookies_file: Optional path to a cookies.txt file for authentication.
        progress_callback: Optional callback function for progress updates.

    Returns:
        Dictionary with:
            - video_path: Path to the downloaded video file
            - title: Video title
            - description: Video description
            - duration: Video duration in seconds
            - platform: Detected platform name
            - thumbnail: Thumbnail URL
            - uploader: Uploader name
    """
    download_path = ensure_download_dir(output_dir)
    platform = detect_platform(url)
    filename = f"video_{uuid.uuid4().hex[:8]}"

    opts = get_yt_dlp_opts(download_path, filename)

    if cookies_file:
        opts["cookiefile"] = cookies_file

    if progress_callback:
        def progress_hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                downloaded = d.get("downloaded_bytes", 0)
                if total > 0:
                    pct = downloaded / total
                    progress_callback(pct, "Downloading...")
            elif d["status"] == "finished":
                progress_callback(1.0, "Download complete, processing...")

        opts["progress_hooks"] = [progress_hook]

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

        video_path = None
        for ext in ["mp4", "webm", "mkv"]:
            candidate = download_path / f"{filename}.{ext}"
            if candidate.exists():
                video_path = str(candidate)
                break

        if video_path is None:
            matches = list(download_path.glob(f"{filename}.*"))
            if matches:
                video_path = str(matches[0])
            else:
                raise FileNotFoundError(
                    f"Downloaded video file not found in {download_path}"
                )

        return {
            "video_path": video_path,
            "title": info.get("title", "Unknown"),
            "description": info.get("description", ""),
            "duration": info.get("duration", 0),
            "platform": platform,
            "thumbnail": info.get("thumbnail", ""),
            "uploader": info.get("uploader", "Unknown"),
            "url": url,
        }


def extract_video_info(url: str) -> dict:
    """Extract video metadata without downloading.

    Useful for previewing video information before downloading.
    """
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "title": info.get("title", "Unknown"),
            "description": info.get("description", ""),
            "duration": info.get("duration", 0),
            "platform": detect_platform(url),
            "thumbnail": info.get("thumbnail", ""),
            "uploader": info.get("uploader", "Unknown"),
        }
