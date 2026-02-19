"""Key points and topic extraction module.

Extracts key talking points from text using RAKE (Rapid Automatic
Keyword Extraction) and frequency analysis.
"""

import re
from collections import Counter

from rake_nltk import Rake

import nltk


def _ensure_nltk_data():
    """Download required NLTK data if not present."""
    for resource in ["punkt_tab", "stopwords"]:
        try:
            nltk.data.find(f"tokenizers/{resource}" if "punkt" in resource else f"corpora/{resource}")
        except LookupError:
            nltk.download(resource, quiet=True)


def extract_keywords(text: str, max_keywords: int = 15) -> list[dict]:
    """Extract key phrases from text using RAKE algorithm.

    Args:
        text: Input text to analyze.
        max_keywords: Maximum number of keywords to return.

    Returns:
        List of dicts with 'phrase' and 'score' keys, sorted by relevance.
    """
    _ensure_nltk_data()

    rake = Rake(
        min_length=1,
        max_length=4,
        include_repeated_phrases=False,
    )
    rake.extract_keywords_from_text(text)
    ranked = rake.get_ranked_phrases_with_scores()

    keywords = []
    seen_phrases = set()

    for score, phrase in ranked[:max_keywords * 2]:
        normalized = phrase.lower().strip()
        if normalized in seen_phrases or len(normalized) < 3:
            continue
        seen_phrases.add(normalized)
        keywords.append({"phrase": phrase, "score": round(score, 2)})
        if len(keywords) >= max_keywords:
            break

    return keywords


def extract_key_points_from_comments(
    comments: list[dict],
    max_points: int = 10,
) -> dict:
    """Extract key talking points from a list of comments.

    Analyzes comment text to find recurring themes and topics.

    Args:
        comments: List of comment dicts with 'text' key.
        max_points: Maximum number of key points.

    Returns:
        Dictionary with:
            - key_phrases: Top extracted phrases
            - common_themes: Most frequent meaningful words/phrases
            - summary_points: Human-readable summary points
    """
    _ensure_nltk_data()

    all_text = " ".join(c.get("text", "") for c in comments if c.get("text"))
    if not all_text.strip():
        return {
            "key_phrases": [],
            "common_themes": [],
            "summary_points": ["No comment text available for analysis."],
        }

    # Extract keywords using RAKE
    key_phrases = extract_keywords(all_text, max_keywords=max_points)

    # Find common themes via word frequency
    stop_words = set(nltk.corpus.stopwords.words("english"))
    # Add social media specific stop words
    stop_words.update({
        "like", "just", "get", "got", "one", "would", "could", "also",
        "really", "much", "even", "still", "thing", "things", "way",
        "good", "great", "nice", "lol", "omg", "wow", "yes", "no",
        "please", "thanks", "thank", "love", "amazing", "awesome",
        "http", "https", "www", "com",
    })

    words = re.findall(r'\b[a-zA-Z]{3,}\b', all_text.lower())
    filtered_words = [w for w in words if w not in stop_words]
    word_freq = Counter(filtered_words)
    common_themes = [
        {"word": word, "count": count}
        for word, count in word_freq.most_common(max_points)
    ]

    # Build summary points
    summary_points = []
    if key_phrases:
        top_topics = [kp["phrase"] for kp in key_phrases[:5]]
        summary_points.append(
            f"Top topics discussed: {', '.join(top_topics)}"
        )

    if common_themes:
        top_words = [t["word"] for t in common_themes[:5]]
        summary_points.append(
            f"Most frequently mentioned: {', '.join(top_words)}"
        )

    # Analyze comment engagement patterns
    comments_with_likes = [c for c in comments if c.get("likes", 0) > 0]
    if comments_with_likes:
        top_liked = sorted(
            comments_with_likes, key=lambda x: x.get("likes", 0), reverse=True
        )[:3]
        for c in top_liked:
            text = c["text"][:100] + ("..." if len(c["text"]) > 100 else "")
            summary_points.append(
                f'Popular comment ({c["likes"]} likes): "{text}"'
            )

    if not summary_points:
        summary_points.append("Not enough data to extract meaningful points.")

    return {
        "key_phrases": key_phrases,
        "common_themes": common_themes,
        "summary_points": summary_points,
    }


def extract_key_points_from_transcription(
    transcription_text: str,
    max_points: int = 10,
) -> dict:
    """Extract key talking points from transcription text.

    Args:
        transcription_text: Full transcription text.
        max_points: Maximum number of key points.

    Returns:
        Dictionary with:
            - key_phrases: Top extracted phrases
            - summary_points: Human-readable summary points
    """
    if not transcription_text.strip():
        return {
            "key_phrases": [],
            "summary_points": ["No transcription text available."],
        }

    key_phrases = extract_keywords(transcription_text, max_keywords=max_points)

    summary_points = []
    if key_phrases:
        top_topics = [kp["phrase"] for kp in key_phrases[:5]]
        summary_points.append(
            f"Key topics in the video: {', '.join(top_topics)}"
        )

    # Extract sentences that contain key phrases for context
    sentences = re.split(r'[.!?]+', transcription_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    if key_phrases and sentences:
        top_phrase = key_phrases[0]["phrase"].lower()
        relevant_sentences = [
            s for s in sentences if top_phrase in s.lower()
        ]
        if relevant_sentences:
            summary_points.append(
                f'Context: "{relevant_sentences[0][:150]}..."'
            )

    if not summary_points:
        summary_points.append("Not enough content to extract key points.")

    return {
        "key_phrases": key_phrases,
        "summary_points": summary_points,
    }
