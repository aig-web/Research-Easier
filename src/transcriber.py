"""Video transcription module using faster-whisper.

Provides accurate speech-to-text transcription with timestamps.
"""

from faster_whisper import WhisperModel

from src.utils import format_timestamp

# Available model sizes (speed vs accuracy tradeoff)
MODEL_SIZES = {
    "tiny": "Fastest, least accurate (~1GB RAM)",
    "base": "Good balance of speed and accuracy (~1GB RAM)",
    "small": "Better accuracy, moderate speed (~2GB RAM)",
    "medium": "High accuracy, slower (~5GB RAM)",
    "large-v3": "Best accuracy, slowest (~10GB RAM)",
}

DEFAULT_MODEL_SIZE = "base"


def transcribe_video(
    video_path: str,
    model_size: str = DEFAULT_MODEL_SIZE,
    language: str | None = None,
    progress_callback=None,
) -> dict:
    """Transcribe audio from a video file.

    Args:
        video_path: Path to the video file.
        model_size: Whisper model size to use.
        language: Optional language code (e.g., 'en'). Auto-detected if None.
        progress_callback: Optional callback for progress updates.

    Returns:
        Dictionary with:
            - text: Full transcription text
            - segments: List of segments with start, end, text
            - language: Detected language
            - language_probability: Confidence of language detection
    """
    if progress_callback:
        progress_callback(0.1, "Loading transcription model...")

    model = WhisperModel(
        model_size,
        device="auto",
        compute_type="auto",
    )

    if progress_callback:
        progress_callback(0.3, "Transcribing audio...")

    segments_gen, info = model.transcribe(
        video_path,
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(
            min_silence_duration_ms=500,
        ),
    )

    segments = []
    full_text_parts = []

    for segment in segments_gen:
        seg_data = {
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
            "start_formatted": format_timestamp(segment.start),
            "end_formatted": format_timestamp(segment.end),
        }
        segments.append(seg_data)
        full_text_parts.append(segment.text.strip())

    full_text = " ".join(full_text_parts)

    if progress_callback:
        progress_callback(1.0, "Transcription complete!")

    return {
        "text": full_text,
        "segments": segments,
        "language": info.language,
        "language_probability": info.language_probability,
    }


def format_transcription(segments: list[dict], include_timestamps: bool = True) -> str:
    """Format transcription segments into readable text.

    Args:
        segments: List of segment dictionaries from transcribe_video.
        include_timestamps: Whether to include timestamps.

    Returns:
        Formatted transcription string.
    """
    lines = []
    for seg in segments:
        if include_timestamps:
            lines.append(
                f"[{seg['start_formatted']} - {seg['end_formatted']}] {seg['text']}"
            )
        else:
            lines.append(seg["text"])

    return "\n".join(lines)
