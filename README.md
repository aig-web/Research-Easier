# Research Easier

Download videos from anywhere, transcribe them accurately, and get sentiment analysis with key talking points from Instagram comments.

## Features

- **Universal Video Download** — Instagram, Twitter/X, Threads, YouTube, TikTok, Facebook, Reddit, and 1000+ platforms via yt-dlp
- **Accurate Transcription** — Speech-to-text powered by OpenAI Whisper (faster-whisper) with multiple model sizes and auto language detection
- **Instagram Sentiment Analysis** — Fetches comments from Instagram Reels, analyses sentiment with interactive donut chart
- **Key Talking Points** — Extracts key phrases, common themes, and highlights popular comments people are discussing
- **Transcription Key Points** — Extracts key topics from the video's spoken content

## Prerequisites

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/download.html) installed and in PATH

```bash
# Ubuntu / Debian
sudo apt update && sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows (chocolatey)
choco install ffmpeg
```

## Setup

```bash
git clone https://github.com/aig-web/Research-Easier.git
cd Research-Easier

python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

## How It Works

1. **Paste any video URL** and click Process
2. Video downloads via yt-dlp (handles platform detection automatically)
3. Audio is transcribed with Whisper (model size configurable)
4. **If Instagram Reel** — comments are fetched and analysed:
   - Sentiment donut chart (positive / negative / neutral)
   - Top positive and negative comments
   - Key phrases and common themes extracted
5. Key talking points are extracted from the transcription itself

## Settings (in the collapsible panel)

| Setting | Description |
|---------|-------------|
| Whisper model | `tiny` (fastest) → `large-v3` (best accuracy) |
| Language code | Auto-detected by default; override with `en`, `es`, `hi`, etc. |
| Instagram credentials | Optional — improves comment access |
| Cookies file | Path to `cookies.txt` for age-gated / private videos |
| Max comments | Number of Instagram comments to fetch (50–500) |

## Project Structure

```
Research-Easier/
├── app.py                      # Flask web application
├── requirements.txt            # Python dependencies
├── templates/
│   └── index.html              # Frontend HTML
├── static/
│   ├── css/style.css           # Styles (dark theme)
│   └── js/app.js               # Frontend logic
├── src/
│   ├── downloader.py           # Video download (yt-dlp)
│   ├── transcriber.py          # Transcription (faster-whisper)
│   ├── instagram_analyzer.py   # Instagram comment fetching
│   ├── sentiment.py            # VADER sentiment analysis
│   ├── key_points.py           # Key phrase & topic extraction
│   └── utils.py                # URL detection & helpers
└── downloads/                  # Downloaded videos (gitignored)
```

## Tech Stack

| Component | Library |
|-----------|---------|
| Backend | Flask |
| Frontend | Vanilla HTML/CSS/JS + Chart.js |
| Video download | yt-dlp |
| Transcription | faster-whisper (CTranslate2) |
| Instagram data | instaloader |
| Sentiment | VADER (vaderSentiment) |
| Keywords | RAKE (rake-nltk) |
