"""Research Easier — Flask Web Application.

Download videos from any platform, transcribe accurately,
and analyse Instagram Reel comments for sentiment & key talking points.
"""

import os
import uuid
import threading

from flask import Flask, jsonify, render_template, request, send_from_directory

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

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# In-memory task store  {task_id: {status, step, progress, message, result, error}}
tasks: dict[str, dict] = {}

# ── Routes ───────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")


@app.route("/api/process", methods=["POST"])
def start_processing():
    """Start processing a video URL.

    Expects JSON body:
        url (str):              Video URL
        model_size (str):       Whisper model size (tiny/base/small/medium/large-v3)
        language (str):         Language code or empty for auto
        insta_username (str):   Optional Instagram username
        insta_password (str):   Optional Instagram password
        max_comments (int):     Max comments to fetch
        cookies_file (str):     Optional cookies file path
    """
    data = request.get_json(force=True)
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400

    task_id = uuid.uuid4().hex[:12]
    tasks[task_id] = {
        "status": "processing",
        "step": "queued",
        "progress": 0,
        "message": "Starting...",
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_process_pipeline,
        args=(task_id, data),
        daemon=True,
    )
    thread.start()

    return jsonify({"task_id": task_id})


@app.route("/api/status/<task_id>")
def task_status(task_id):
    """Return the current status of a processing task."""
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)


@app.route("/api/video/<path:filename>")
def serve_video(filename):
    """Serve a downloaded video file."""
    return send_from_directory(DOWNLOAD_DIR, filename)


# ── Background processing pipeline ──────────────────────────────────────────


def _update_task(task_id: str, **kwargs):
    """Update task state."""
    if task_id in tasks:
        tasks[task_id].update(kwargs)


def _process_pipeline(task_id: str, data: dict):
    """Run the full download → transcribe → analyse pipeline."""
    url = clean_url(data.get("url", ""))
    model_size = data.get("model_size", "base")
    language = data.get("language", "") or None
    insta_username = data.get("insta_username", "") or None
    insta_password = data.get("insta_password", "") or None
    max_comments = int(data.get("max_comments", 200))
    cookies_file = data.get("cookies_file", "") or None

    platform = detect_platform(url)
    is_insta = is_instagram_url(url)
    result = {"platform": platform, "is_instagram": is_insta}

    # ── Step 1: Download ─────────────────────────────────────────────────
    try:
        _update_task(
            task_id, step="downloading", progress=5,
            message="Downloading video..."
        )

        def dl_progress(pct, msg):
            _update_task(
                task_id, progress=int(5 + pct * 30), message=msg
            )

        video_info = download_video(
            url,
            output_dir=DOWNLOAD_DIR,
            cookies_file=cookies_file,
            progress_callback=dl_progress,
        )
        # Make video path relative for serving
        video_filename = os.path.basename(video_info["video_path"])
        video_info["video_url"] = f"/api/video/{video_filename}"
        result["video"] = video_info

        _update_task(task_id, progress=35, message="Download complete")
    except Exception as e:
        _update_task(
            task_id, status="error", step="downloading",
            error=f"Download failed: {e}"
        )
        return

    # ── Step 2: Transcribe ───────────────────────────────────────────────
    try:
        _update_task(
            task_id, step="transcribing", progress=38,
            message="Loading transcription model..."
        )

        def tr_progress(pct, msg):
            _update_task(
                task_id, progress=int(38 + pct * 30), message=msg
            )

        transcription = transcribe_video(
            video_info["video_path"],
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

        # Key points from transcription
        trans_kp = extract_key_points_from_transcription(transcription["text"])
        result["transcription_key_points"] = trans_kp

        _update_task(task_id, progress=70, message="Transcription complete")
    except Exception as e:
        _update_task(
            task_id, step="transcribing", progress=70,
            message=f"Transcription failed: {e}"
        )
        result["transcription"] = None
        result["transcription_key_points"] = None

    # ── Step 3: Instagram comments & analysis ────────────────────────────
    if is_insta:
        try:
            _update_task(
                task_id, step="fetching_comments", progress=72,
                message="Fetching Instagram comments..."
            )

            def insta_progress(pct, msg):
                _update_task(
                    task_id, progress=int(72 + pct * 15), message=msg
                )

            insta_data = fetch_comments(
                url,
                username=insta_username,
                password=insta_password,
                max_comments=max_comments,
                progress_callback=insta_progress,
            )
            result["instagram"] = insta_data

            _update_task(
                task_id, progress=88,
                message="Analysing sentiment..."
            )
        except Exception as e:
            result["instagram"] = None
            _update_task(
                task_id, progress=88,
                message=f"Could not fetch comments: {e}"
            )

        # Sentiment + key points
        if result.get("instagram") and result["instagram"]["comments"]:
            try:
                _update_task(
                    task_id, step="analysing", progress=90,
                    message="Running sentiment analysis..."
                )
                sentiment = analyze_comments(result["instagram"]["comments"])
                result["sentiment"] = sentiment

                key_points = extract_key_points_from_comments(
                    result["instagram"]["comments"]
                )
                result["key_points"] = key_points

                _update_task(task_id, progress=98, message="Analysis complete")
            except Exception as e:
                result["sentiment"] = None
                result["key_points"] = None
        else:
            result["sentiment"] = None
            result["key_points"] = None

    # ── Done ─────────────────────────────────────────────────────────────
    _update_task(
        task_id, status="complete", step="done",
        progress=100, message="All done!", result=result
    )


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
