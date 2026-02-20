import os
from google import genai

DEFAULT_MODEL = "gemini-2.5-flash-preview-05-20"


def get_client(api_key=None):
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return None
    return genai.Client(api_key=key)


def analyze_tweet_text(tweet_text, author="", api_key=None, model=None):
    """Use Gemini to summarize tweet text and extract topic."""
    client = get_client(api_key)
    if not client:
        return _fallback_analysis(tweet_text)

    model_name = model or DEFAULT_MODEL

    prompt = f"""Analyze this tweet and provide:
1. A short topic name (3-6 words max) that captures the main idea
2. A concise summary (2-3 sentences) of what this tweet is about
3. A category from this list: [Tech, AI/ML, Business, Science, Politics, Entertainment, Sports, Health, Education, Crypto, Startup, Design, Other]

Tweet by @{author}:
\"\"\"{tweet_text}\"\"\"

Respond in this exact format:
TOPIC: <topic name>
SUMMARY: <summary>
CATEGORY: <category>"""

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        return _parse_analysis(response.text)
    except Exception as e:
        print(f"Gemini text analysis error: {e}")
        return _fallback_analysis(tweet_text)


def analyze_video(video_path, api_key=None, model=None):
    """Use Gemini to analyze a video from a tweet."""
    client = get_client(api_key)
    if not client:
        return "Video analysis unavailable (no API key)"

    if not video_path or not os.path.exists(video_path):
        return "No video file found"

    file_size = os.path.getsize(video_path)
    if file_size > 20 * 1024 * 1024:
        return "Video too large for analysis (>20MB)"

    model_name = model or DEFAULT_MODEL

    try:
        uploaded_file = client.files.upload(file=video_path)

        prompt = """Analyze this video from a tweet. Provide:
1. What is happening in the video (2-3 sentences)
2. Key topics or subjects discussed/shown
3. Any notable details or takeaways

Keep the response concise and informative."""

        response = client.models.generate_content(
            model=model_name,
            contents=[prompt, uploaded_file],
        )

        try:
            client.files.delete(name=uploaded_file.name)
        except Exception:
            pass

        return response.text
    except Exception as e:
        return f"Video analysis failed: {str(e)}"


def _parse_analysis(text):
    result = {"topic_name": "", "summary": "", "category": "Other"}

    for line in text.strip().split("\n"):
        line = line.strip()
        if line.upper().startswith("TOPIC:"):
            result["topic_name"] = line.split(":", 1)[1].strip()
        elif line.upper().startswith("SUMMARY:"):
            result["summary"] = line.split(":", 1)[1].strip()
        elif line.upper().startswith("CATEGORY:"):
            result["category"] = line.split(":", 1)[1].strip()

    return result


def _fallback_analysis(tweet_text):
    """Simple fallback when Gemini is unavailable."""
    words = tweet_text.split()
    topic = " ".join(words[:5]) + ("..." if len(words) > 5 else "")
    summary = tweet_text[:280] + ("..." if len(tweet_text) > 280 else "")
    return {
        "topic_name": topic,
        "summary": summary,
        "category": "Other",
    }
