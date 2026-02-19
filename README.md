# Research Easier

Download videos from anywhere, transcribe them accurately, and get sentiment analysis with key talking points from Instagram comments.

## Features

- **Universal Video Download** — Download videos from Instagram, Twitter/X, Threads, YouTube, TikTok, Facebook, Reddit, and 1000+ other platforms via yt-dlp
- **Accurate Transcription** — Speech-to-text powered by OpenAI Whisper (faster-whisper) with multiple model sizes and language auto-detection
- **Instagram Sentiment Analysis** — Automatically fetches comments from Instagram Reels and analyzes sentiment (positive / negative / neutral) with visual charts
- **Key Talking Points** — Extracts key phrases, common themes, and popular comments to show what people are discussing
- **Transcription Key Points** — Extracts key topics and phrases from the video's spoken content

## Prerequisites

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/download.html) installed and available in PATH

### Install ffmpeg

```bash
# Ubuntu / Debian
sudo apt update && sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows (via chocolatey)
choco install ffmpeg
```

## Setup

```bash
# Clone the repo
git clone https://github.com/aig-web/Research-Easier.git
cd Research-Easier

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
streamlit run app.py
```

The app opens in your browser. Paste any video URL and click **Process**.

### Workflow

1. **Paste a URL** — Instagram Reel, tweet, YouTube video, TikTok, or any supported platform
2. **Video downloads** automatically using yt-dlp
3. **Transcription** runs via Whisper (select model size in sidebar)
4. **If Instagram** — comments are fetched and analyzed for sentiment + key talking points
5. **Results** are displayed in organized tabs with download options

### Sidebar Settings

| Setting | Description |
|---------|-------------|
| Whisper model size | `tiny` (fastest) → `large-v3` (most accurate) |
| Language code | Auto-detected by default; override with `en`, `es`, `hi`, etc. |
| Instagram credentials | Optional; improves comment access |
| Cookies file | Path to `cookies.txt` for age-gated or private videos |
| Max comments | Number of Instagram comments to fetch (50–500) |

## Project Structure

```
Research-Easier/
├── app.py                      # Streamlit UI application
├── requirements.txt            # Python dependencies
├── src/
│   ├── __init__.py
│   ├── downloader.py           # Video download (yt-dlp)
│   ├── transcriber.py          # Audio transcription (faster-whisper)
│   ├── instagram_analyzer.py   # Instagram comment fetching
│   ├── sentiment.py            # VADER sentiment analysis
│   ├── key_points.py           # Key phrase & topic extraction
│   └── utils.py                # URL detection & helpers
└── downloads/                  # Downloaded videos (gitignored)
```

## Supported Platforms

yt-dlp supports 1000+ sites. Key platforms:

- Instagram (Reels, Posts, Stories)
- Twitter / X
- Threads
- YouTube
- TikTok
- Facebook
- Reddit
- Vimeo
- Dailymotion
- And many more

## Tech Stack

| Component | Library |
|-----------|---------|
| UI | Streamlit |
| Video download | yt-dlp |
| Transcription | faster-whisper (CTranslate2) |
| Instagram data | instaloader |
| Sentiment analysis | VADER (vaderSentiment) |
| Keyword extraction | RAKE (rake-nltk) |
| Charts | Plotly |
