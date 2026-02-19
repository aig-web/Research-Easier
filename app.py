"""Research Easier — Video Download, Transcribe & Analyze.

A Streamlit application that downloads videos from any platform,
transcribes them accurately, and provides sentiment analysis with
key talking points for Instagram Reels.
"""

import streamlit as st
import plotly.graph_objects as go

from src.utils import clean_url, detect_platform, is_instagram_url
from src.downloader import download_video
from src.transcriber import transcribe_video, format_transcription, MODEL_SIZES
from src.instagram_analyzer import fetch_comments
from src.sentiment import analyze_comments
from src.key_points import (
    extract_key_points_from_comments,
    extract_key_points_from_transcription,
)

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Research Easier",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #888;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #1e1e2e;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
    }
    .sentiment-positive { color: #2ecc71; font-weight: 600; }
    .sentiment-negative { color: #e74c3c; font-weight: 600; }
    .sentiment-neutral  { color: #95a5a6; font-weight: 600; }
    .comment-card {
        background: #262637;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar settings ────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Settings")

    st.subheader("Transcription")
    model_size = st.selectbox(
        "Whisper model size",
        options=list(MODEL_SIZES.keys()),
        index=1,  # default: base
        format_func=lambda k: f"{k} — {MODEL_SIZES[k]}",
    )
    language = st.text_input(
        "Language code (leave empty for auto-detect)",
        placeholder="en, es, hi, fr ...",
    )

    st.divider()
    st.subheader("Instagram (optional)")
    st.caption(
        "Credentials improve access to comments. "
        "Leave blank to try without login."
    )
    insta_username = st.text_input("Instagram username", type="default")
    insta_password = st.text_input("Instagram password", type="password")

    st.divider()
    st.subheader("Advanced")
    cookies_file = st.text_input(
        "Cookies file path (for age-gated / private videos)",
        placeholder="/path/to/cookies.txt",
    )
    max_comments = st.slider(
        "Max Instagram comments to fetch", 50, 500, 200, step=50
    )

# ── Main UI ──────────────────────────────────────────────────────────────────

st.markdown('<div class="main-header">Research Easier</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">'
    "Download videos from anywhere &bull; Accurate transcription &bull; "
    "Instagram sentiment analysis &amp; key talking points"
    "</div>",
    unsafe_allow_html=True,
)

# URL input
url_input = st.text_input(
    "Paste video URL",
    placeholder="https://www.instagram.com/reel/... or any video URL",
    label_visibility="collapsed",
)

col_btn, col_info = st.columns([1, 3])
with col_btn:
    process_btn = st.button("Process", type="primary", use_container_width=True)
with col_info:
    if url_input:
        platform = detect_platform(clean_url(url_input))
        label = platform.title() if platform != "other" else "Video"
        st.info(f"Detected platform: **{label}**")


# ── Processing pipeline ─────────────────────────────────────────────────────

def render_sentiment_chart(distribution: dict):
    """Render a plotly donut chart of sentiment distribution."""
    colors = {"Positive": "#2ecc71", "Negative": "#e74c3c", "Neutral": "#95a5a6"}
    fig = go.Figure(data=[go.Pie(
        labels=list(distribution.keys()),
        values=list(distribution.values()),
        hole=0.5,
        marker=dict(colors=[colors[k] for k in distribution]),
        textinfo="label+percent",
        textfont_size=14,
    )])
    fig.update_layout(
        showlegend=False,
        margin=dict(t=20, b=20, l=20, r=20),
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
    )
    return fig


def render_comment(comment: dict, show_sentiment: bool = True):
    """Render a single comment with sentiment badge."""
    sentiment = comment.get("sentiment", "")
    css_class = f"sentiment-{sentiment.lower()}" if sentiment else ""
    badge = f' <span class="{css_class}">[{sentiment}]</span>' if show_sentiment else ""
    likes = f' ({comment.get("likes", 0)} likes)' if comment.get("likes") else ""

    st.markdown(
        f'<div class="comment-card">'
        f"<strong>@{comment.get('owner', 'unknown')}</strong>{likes}{badge}<br/>"
        f"{comment['text']}"
        f"</div>",
        unsafe_allow_html=True,
    )


if process_btn and url_input:
    url = clean_url(url_input)
    is_insta = is_instagram_url(url)

    # ── Step 1: Download ─────────────────────────────────────────────────
    st.divider()
    with st.status("Downloading video...", expanded=True) as status:
        progress_bar = st.progress(0)

        def download_progress(pct, msg):
            progress_bar.progress(min(pct, 1.0))
            status.update(label=msg)

        try:
            video_info = download_video(
                url,
                cookies_file=cookies_file if cookies_file else None,
                progress_callback=download_progress,
            )
            status.update(label="Download complete!", state="complete")
        except Exception as e:
            status.update(label="Download failed", state="error")
            st.error(f"Failed to download video: {e}")
            st.stop()

    # Show video info
    st.subheader(video_info["title"])
    col_v, col_m = st.columns([2, 1])
    with col_v:
        st.video(video_info["video_path"])
    with col_m:
        st.metric("Platform", video_info["platform"].title())
        if video_info.get("duration"):
            minutes = int(video_info["duration"] // 60)
            seconds = int(video_info["duration"] % 60)
            st.metric("Duration", f"{minutes}m {seconds}s")
        st.metric("Uploader", video_info.get("uploader", "Unknown"))

    # ── Step 2: Transcribe ───────────────────────────────────────────────
    with st.status("Transcribing video...", expanded=True) as status:
        progress_bar = st.progress(0)

        def transcribe_progress(pct, msg):
            progress_bar.progress(min(pct, 1.0))
            status.update(label=msg)

        try:
            transcription = transcribe_video(
                video_info["video_path"],
                model_size=model_size,
                language=language if language else None,
                progress_callback=transcribe_progress,
            )
            status.update(label="Transcription complete!", state="complete")
        except Exception as e:
            status.update(label="Transcription failed", state="error")
            st.error(f"Transcription failed: {e}")
            transcription = None

    # ── Step 3: Instagram analysis (if applicable) ───────────────────────
    insta_data = None
    sentiment_data = None
    key_points_comments = None

    if is_insta:
        with st.status("Fetching Instagram comments...", expanded=True) as status:
            progress_bar = st.progress(0)

            def insta_progress(pct, msg):
                progress_bar.progress(min(pct, 1.0))
                status.update(label=msg)

            try:
                insta_data = fetch_comments(
                    url,
                    username=insta_username if insta_username else None,
                    password=insta_password if insta_password else None,
                    max_comments=max_comments,
                    progress_callback=insta_progress,
                )
                status.update(
                    label=f"Fetched {insta_data['comment_count']} comments!",
                    state="complete",
                )
            except Exception as e:
                status.update(label="Could not fetch comments", state="error")
                st.warning(
                    f"Could not fetch Instagram comments: {e}\n\n"
                    "Try providing Instagram credentials in the sidebar."
                )

        # Sentiment analysis
        if insta_data and insta_data["comments"]:
            with st.status("Analyzing sentiment...", expanded=False) as status:
                sentiment_data = analyze_comments(insta_data["comments"])
                key_points_comments = extract_key_points_from_comments(
                    insta_data["comments"]
                )
                status.update(label="Analysis complete!", state="complete")

    # ── Display results ──────────────────────────────────────────────────
    st.divider()

    if is_insta and (transcription or sentiment_data):
        tab_names = ["Transcription", "Sentiment Analysis", "Key Points"]
        if not transcription:
            tab_names.remove("Transcription")
        if not sentiment_data:
            tab_names.remove("Sentiment Analysis")
            tab_names.remove("Key Points")

        tabs = st.tabs(tab_names)
        tab_idx = 0

        # ── Transcription tab ────────────────────────────────────────────
        if transcription:
            with tabs[tab_idx]:
                st.subheader("Video Transcription")
                lang = transcription.get("language", "unknown")
                prob = transcription.get("language_probability", 0)
                st.caption(
                    f"Detected language: **{lang}** "
                    f"(confidence: {prob:.0%})"
                )

                show_timestamps = st.toggle("Show timestamps", value=True)
                formatted = format_transcription(
                    transcription["segments"],
                    include_timestamps=show_timestamps,
                )
                st.text_area(
                    "Full transcription",
                    formatted,
                    height=400,
                    label_visibility="collapsed",
                )

                st.download_button(
                    "Download transcription",
                    formatted,
                    file_name="transcription.txt",
                    mime="text/plain",
                )
            tab_idx += 1

        # ── Sentiment tab ────────────────────────────────────────────────
        if sentiment_data:
            with tabs[tab_idx]:
                st.subheader("Comment Sentiment Analysis")
                st.write(sentiment_data["summary"])

                col_chart, col_stats = st.columns([1, 1])
                with col_chart:
                    fig = render_sentiment_chart(sentiment_data["distribution"])
                    st.plotly_chart(fig, use_container_width=True)
                with col_stats:
                    dist = sentiment_data["distribution"]
                    total = sum(dist.values())
                    st.metric("Total comments analyzed", total)
                    st.metric("Positive", f"{dist['Positive']} ({dist['Positive']/total*100:.1f}%)" if total else "0")
                    st.metric("Negative", f"{dist['Negative']} ({dist['Negative']/total*100:.1f}%)" if total else "0")
                    st.metric("Neutral", f"{dist['Neutral']} ({dist['Neutral']/total*100:.1f}%)" if total else "0")

                with st.expander("Top positive comments"):
                    for c in sentiment_data["most_positive"]:
                        render_comment(c)

                with st.expander("Top negative comments"):
                    for c in sentiment_data["most_negative"]:
                        render_comment(c)
            tab_idx += 1

        # ── Key Points tab ───────────────────────────────────────────────
        if sentiment_data:
            with tabs[tab_idx]:
                st.subheader("Key Talking Points")

                if key_points_comments:
                    st.markdown("#### What people are saying")
                    for point in key_points_comments["summary_points"]:
                        st.markdown(f"- {point}")

                    if key_points_comments["key_phrases"]:
                        st.markdown("#### Top Phrases")
                        for kp in key_points_comments["key_phrases"]:
                            st.markdown(
                                f"- **{kp['phrase']}** (relevance: {kp['score']})"
                            )

                    if key_points_comments["common_themes"]:
                        st.markdown("#### Common Themes")
                        themes_text = ", ".join(
                            f"**{t['word']}** ({t['count']}x)"
                            for t in key_points_comments["common_themes"][:10]
                        )
                        st.markdown(themes_text)

                # Also show transcription key points
                if transcription:
                    st.markdown("---")
                    st.markdown("#### Key Points from Video Content")
                    trans_kp = extract_key_points_from_transcription(
                        transcription["text"]
                    )
                    for point in trans_kp["summary_points"]:
                        st.markdown(f"- {point}")

    else:
        # Non-Instagram: just show transcription and key points
        if transcription:
            st.subheader("Video Transcription")
            lang = transcription.get("language", "unknown")
            prob = transcription.get("language_probability", 0)
            st.caption(
                f"Detected language: **{lang}** "
                f"(confidence: {prob:.0%})"
            )

            show_timestamps = st.toggle("Show timestamps", value=True)
            formatted = format_transcription(
                transcription["segments"],
                include_timestamps=show_timestamps,
            )
            st.text_area(
                "Full transcription",
                formatted,
                height=400,
                label_visibility="collapsed",
            )

            st.download_button(
                "Download transcription",
                formatted,
                file_name="transcription.txt",
                mime="text/plain",
            )

            # Key points from transcription
            st.divider()
            st.subheader("Key Points from Video")
            trans_kp = extract_key_points_from_transcription(
                transcription["text"]
            )
            for point in trans_kp["summary_points"]:
                st.markdown(f"- {point}")

            if trans_kp["key_phrases"]:
                st.markdown("#### Top Phrases")
                for kp in trans_kp["key_phrases"]:
                    st.markdown(
                        f"- **{kp['phrase']}** (relevance: {kp['score']})"
                    )

elif process_btn and not url_input:
    st.warning("Please enter a video URL to get started.")

# ── Footer ───────────────────────────────────────────────────────────────────

st.divider()
st.caption(
    "Research Easier — Supports Instagram, Twitter/X, Threads, YouTube, "
    "TikTok, Facebook, Reddit, and 1000+ other platforms via yt-dlp. "
    "Transcription powered by Whisper. Sentiment analysis powered by VADER."
)
