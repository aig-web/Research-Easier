"""Utility functions for URL detection and file management."""

import re
from pathlib import Path
from urllib.parse import urlparse


PLATFORM_PATTERNS = {
    "instagram": [
        r"(www\.)?instagram\.com",
        r"instagr\.am",
    ],
    "twitter": [
        r"(www\.)?twitter\.com",
        r"(www\.)?x\.com",
    ],
    "threads": [
        r"(www\.)?threads\.net",
    ],
    "youtube": [
        r"(www\.)?youtube\.com",
        r"youtu\.be",
    ],
    "tiktok": [
        r"(www\.)?tiktok\.com",
        r"vm\.tiktok\.com",
    ],
    "facebook": [
        r"(www\.)?facebook\.com",
        r"fb\.watch",
    ],
    "reddit": [
        r"(www\.)?reddit\.com",
        r"v\.redd\.it",
    ],
}


def detect_platform(url: str) -> str:
    """Detect which platform a URL belongs to.

    Returns the platform name or 'other' if unrecognized.
    """
    parsed = urlparse(url)
    hostname = parsed.netloc.lower()

    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, hostname):
                return platform

    return "other"


def is_instagram_url(url: str) -> bool:
    """Check if the URL is an Instagram URL."""
    return detect_platform(url) == "instagram"


def extract_instagram_shortcode(url: str) -> str | None:
    """Extract the shortcode from an Instagram URL.

    Supports formats like:
    - https://www.instagram.com/reel/ABC123/
    - https://www.instagram.com/p/ABC123/
    - https://www.instagram.com/reels/ABC123/
    """
    patterns = [
        r"instagram\.com/(?:reel|reels|p|tv)/([A-Za-z0-9_-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def ensure_download_dir(base_dir: str = "downloads") -> Path:
    """Ensure the download directory exists and return its path."""
    download_dir = Path(base_dir)
    download_dir.mkdir(parents=True, exist_ok=True)
    return download_dir


def clean_url(url: str) -> str:
    """Clean and normalize a URL."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def format_timestamp(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS timestamp."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
