"""Research Easier — Flask Web Application.

Download videos from any platform, transcribe accurately,
and analyse Instagram Reel comments for sentiment & key talking points.

Supports both local development and Vercel serverless deployment.
"""

import base64
import json
import os

from flask import Flask, Response, jsonify, render_template, request, send_from_directory, stream_with_context

from src.utils import clean_url, detect_platform, is_instagram_url
from src.downloader import download_video
from src.transcriber import transcribe_video, format_transcription
from src.instagram_analyzer import fetch_comments
from src.sentiment import analyze_comments
from src.key_points import (
    extract_key_points_from_comments,
    extract_key_points_from_transcription,
)

# ── App setup ────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload limit

ON_VERCEL = bool(os.environ.get("VERCEL"))

# Local: project-local downloads/  |  Vercel: ephemeral /tmp
DOWNLOAD_DIR = (
    "/tmp/downloads" if ON_VERCEL
    else os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Max video size (bytes) to inline as base64 for Vercel (10 MB)
MAX_INLINE_VIDEO_SIZE = 10 * 1024 * 1024


# ── Helpers ──────────────────────────────────────────────────────────────────


def _sse(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"


def _video_to_data_url(path: str) -> str | None:
    """Encode a video file as a base64 data-URL (for serverless serving)."""
    try:
        size = os.path.getsize(path)
        if size > MAX_INLINE_VIDEO_SIZE:
            return None
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        ext = os.path.splitext(path)[1].lstrip(".")
        mime = {"mp4": "video/mp4", "webm": "video/webm", "mkv": "video/x-matroska"}.get(ext, "video/mp4")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None


# ── Routes ───────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")


@app.route("/api/video/<path:filename>")
def serve_video(filename):
    """Serve a downloaded video file (local development only)."""
    return send_from_directory(DOWNLOAD_DIR, filename)


@app.route("/api/process", methods=["POST"])
def process():
    """Process a video URL, streaming progress as SSE events.

    Expects JSON body:
        url, model_size, language, insta_username, insta_password,
        max_comments, cookies_file

    Returns text/event-stream with events:
        {type: "progress", step, progress, message}
        {type: "result",   result: { ... }}
        {type: "error",    error: "..."}
    """
    data = request.get_json(force=True)
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400

    def generate():
        yield from _run_pipeline(data)

    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",        # nginx
            "Connection": "keep-alive",
        },
    )


# ── Processing pipeline (generator) ─────────────────────────────────────────


def _run_pipeline(data: dict):
    """Yield SSE events as the pipeline progresses."""

    url = clean_url(data.get("url", ""))
    model_size = data.get("model_size", "base")
    language = data.get("language", "") or None
    insta_username = data.get("insta_username", "") or None
    insta_password = data.get("insta_password", "") or None
    max_comments = int(data.get("max_comments", 200))
    cookies_file = data.get("cookies_file", "") or None

    platform = detect_platform(url)
    is_insta = is_instagram_url(url)
    result: dict = {"platform": platform, "is_instagram": is_insta}

    # ── Step 1: Download ─────────────────────────────────────────────────
    yield _sse({"type": "progress", "step": "downloading", "progress": 5, "message": "Downloading video..."})

    try:
        last_progress = [5]  # mutable so the callback can update

        def dl_progress(pct, msg):
            p = int(5 + pct * 30)
            if p > last_progress[0]:
                last_progress[0] = p

        video_info = download_video(
            url,
            output_dir=DOWNLOAD_DIR,
            cookies_file=cookies_file,
            progress_callback=dl_progress,
        )

        # Video serving: local uses /api/video/<file>, Vercel uses base64 data URL
        video_path = video_info["video_path"]
        if ON_VERCEL:
            data_url = _video_to_data_url(video_path)
            if data_url:
                video_info["video_data"] = data_url
            video_info.pop("video_path", None)
        else:
            filename = os.path.basename(video_path)
            video_info["video_url"] = f"/api/video/{filename}"

        result["video"] = video_info

        yield _sse({"type": "progress", "step": "downloading", "progress": 35, "message": "Download complete"})
    except Exception as e:
        yield _sse({"type": "error", "error": f"Download failed: {e}"})
        return

    # ── Step 2: Transcribe ───────────────────────────────────────────────
    yield _sse({"type": "progress", "step": "transcribing", "progress": 38, "message": "Loading transcription model..."})

    try:
        def tr_progress(pct, msg):
            pass  # SSE events are yielded between steps

        transcription = transcribe_video(
            video_path,
            model_size=model_size,
            language=language,
            progress_callback=tr_progress,
        )
        transcription["formatted"] = format_transcription(
            transcription["segments"], include_timestamps=True
        )
        transcription["formatted_plain"] = format_transcription(
            transcription["segments"], include_timestamps=False
        )
        result["transcription"] = transcription

        yield _sse({"type": "progress", "step": "transcribing", "progress": 65, "message": "Extracting key points..."})

        trans_kp = extract_key_points_from_transcription(transcription["text"])
        result["transcription_key_points"] = trans_kp

        yield _sse({"type": "progress", "step": "transcribing", "progress": 70, "message": "Transcription complete"})
    except Exception as e:
        result["transcription"] = None
        result["transcription_key_points"] = None
        yield _sse({"type": "progress", "step": "transcribing", "progress": 70, "message": f"Transcription failed: {e}"})

    # ── Step 3: Instagram comments & analysis ────────────────────────────
    if is_insta:
        yield _sse({"type": "progress", "step": "fetching_comments", "progress": 72, "message": "Fetching Instagram comments..."})

        try:
            def insta_progress(pct, msg):
                pass

            insta_data = fetch_comments(
                url,
                username=insta_username,
                password=insta_password,
                max_comments=max_comments,
                progress_callback=insta_progress,
            )
            result["instagram"] = insta_data
            yield _sse({"type": "progress", "step": "fetching_comments", "progress": 88, "message": "Comments fetched"})
        except Exception as e:
            result["instagram"] = None
            yield _sse({"type": "progress", "step": "fetching_comments", "progress": 88, "message": f"Could not fetch comments: {e}"})

        # Sentiment + key points
        if result.get("instagram") and result["instagram"].get("comments"):
            yield _sse({"type": "progress", "step": "analysing", "progress": 90, "message": "Running sentiment analysis..."})
            try:
                result["sentiment"] = analyze_comments(result["instagram"]["comments"])
                result["key_points"] = extract_key_points_from_comments(result["instagram"]["comments"])
                yield _sse({"type": "progress", "step": "analysing", "progress": 98, "message": "Analysis complete"})
            except Exception:
                result["sentiment"] = None
                result["key_points"] = None
        else:
            result["sentiment"] = None
            result["key_points"] = None

    # ── Clean up temp file on Vercel ─────────────────────────────────────
    if ON_VERCEL:
        try:
            os.remove(video_path)
        except OSError:
            pass

    # ── Done ─────────────────────────────────────────────────────────────
    yield _sse({"type": "result", "result": result})


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
