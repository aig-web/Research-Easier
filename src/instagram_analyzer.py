"""Instagram-specific analysis module.

Fetches comments from Instagram reels/posts using instaloader
and provides analysis of the engagement.
"""

import instaloader

from src.utils import extract_instagram_shortcode


def create_loader(username: str | None = None, password: str | None = None):
    """Create an instaloader instance with optional authentication.

    Authentication improves access to comments and reduces rate limiting.
    """
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=True,
        save_metadata=False,
        compress_json=False,
        quiet=True,
    )

    if username and password:
        try:
            loader.login(username, password)
        except instaloader.exceptions.BadCredentialsException:
            raise ValueError("Invalid Instagram credentials")
        except instaloader.exceptions.TwoFactorAuthRequiredException:
            raise ValueError(
                "Two-factor authentication is enabled. "
                "Please disable it temporarily or use a cookies file."
            )

    return loader


def fetch_comments(
    url: str,
    username: str | None = None,
    password: str | None = None,
    max_comments: int = 200,
    progress_callback=None,
) -> dict:
    """Fetch comments from an Instagram post or reel.

    Args:
        url: Instagram post/reel URL.
        username: Optional Instagram username for authentication.
        password: Optional Instagram password for authentication.
        max_comments: Maximum number of comments to fetch.
        progress_callback: Optional callback for progress updates.

    Returns:
        Dictionary with:
            - comments: List of comment dicts (text, owner, likes, timestamp)
            - post_info: Basic post information
            - comment_count: Total comments fetched
            - login_used: Whether authentication was used
    """
    shortcode = extract_instagram_shortcode(url)
    if not shortcode:
        raise ValueError(
            f"Could not extract Instagram shortcode from URL: {url}"
        )

    if progress_callback:
        progress_callback(0.1, "Connecting to Instagram...")

    loader = create_loader(username, password)

    if progress_callback:
        progress_callback(0.3, "Fetching post data...")

    try:
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
    except Exception as e:
        raise RuntimeError(
            f"Failed to fetch Instagram post. It may be private or deleted. "
            f"Try providing Instagram credentials. Error: {e}"
        )

    post_info = {
        "caption": post.caption or "",
        "likes": post.likes,
        "owner": post.owner_username,
        "date": str(post.date_utc),
        "is_video": post.is_video,
        "video_view_count": post.video_view_count if post.is_video else None,
        "media_type": "reel" if post.is_video else "image",
    }

    if progress_callback:
        progress_callback(0.5, "Fetching comments...")

    comments = []
    try:
        for i, comment in enumerate(post.get_comments()):
            if i >= max_comments:
                break

            comments.append({
                "text": comment.text,
                "owner": comment.owner.username,
                "likes": comment.likes_count,
                "timestamp": str(comment.created_at_utc),
            })

            if progress_callback and i % 20 == 0:
                pct = 0.5 + (0.4 * min(i / max_comments, 1.0))
                progress_callback(pct, f"Fetched {i + 1} comments...")

    except Exception as e:
        if not comments:
            raise RuntimeError(
                f"Could not fetch comments. This may require authentication. "
                f"Error: {e}"
            )
        # Return whatever comments we managed to get

    if progress_callback:
        progress_callback(1.0, "Comments fetched!")

    return {
        "comments": comments,
        "post_info": post_info,
        "comment_count": len(comments),
        "login_used": username is not None,
    }
