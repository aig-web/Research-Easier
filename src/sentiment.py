"""Sentiment analysis module using VADER.

VADER (Valence Aware Dictionary and sEntiment Reasoner) is specifically
designed for social media text, making it ideal for analyzing comments.
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


def get_analyzer() -> SentimentIntensityAnalyzer:
    """Get a VADER sentiment analyzer instance."""
    return SentimentIntensityAnalyzer()


def classify_sentiment(compound_score: float) -> str:
    """Classify a compound score into a sentiment label.

    VADER compound score ranges from -1 (most negative) to +1 (most positive).
    """
    if compound_score >= 0.05:
        return "Positive"
    elif compound_score <= -0.05:
        return "Negative"
    return "Neutral"


def analyze_comments(comments: list[dict]) -> dict:
    """Analyze sentiment of a list of comments.

    Args:
        comments: List of comment dicts, each with a 'text' key.

    Returns:
        Dictionary with:
            - results: List of per-comment sentiment analysis
            - summary: Overall sentiment summary
            - distribution: Count of positive/negative/neutral
            - average_compound: Average compound score
            - most_positive: Top positive comments
            - most_negative: Top negative comments
    """
    analyzer = get_analyzer()
    results = []

    for comment in comments:
        text = comment.get("text", "")
        if not text:
            continue

        scores = analyzer.polarity_scores(text)
        sentiment = classify_sentiment(scores["compound"])

        results.append({
            "text": text,
            "owner": comment.get("owner", ""),
            "likes": comment.get("likes", 0),
            "compound": scores["compound"],
            "positive": scores["pos"],
            "negative": scores["neg"],
            "neutral": scores["neu"],
            "sentiment": sentiment,
        })

    if not results:
        return {
            "results": [],
            "summary": "No comments to analyze",
            "distribution": {"Positive": 0, "Negative": 0, "Neutral": 0},
            "average_compound": 0,
            "most_positive": [],
            "most_negative": [],
        }

    # Distribution
    distribution = {"Positive": 0, "Negative": 0, "Neutral": 0}
    for r in results:
        distribution[r["sentiment"]] += 1

    # Average compound score
    avg_compound = sum(r["compound"] for r in results) / len(results)

    # Sort by compound score
    sorted_results = sorted(results, key=lambda x: x["compound"], reverse=True)
    most_positive = sorted_results[:5]
    most_negative = sorted_results[-5:][::-1]

    # Overall sentiment
    total = len(results)
    pos_pct = (distribution["Positive"] / total) * 100
    neg_pct = (distribution["Negative"] / total) * 100
    neu_pct = (distribution["Neutral"] / total) * 100

    overall = classify_sentiment(avg_compound)
    summary = (
        f"Overall sentiment: {overall} (avg score: {avg_compound:.3f}). "
        f"Distribution: {pos_pct:.1f}% positive, {neg_pct:.1f}% negative, "
        f"{neu_pct:.1f}% neutral across {total} comments."
    )

    return {
        "results": results,
        "summary": summary,
        "distribution": distribution,
        "average_compound": avg_compound,
        "most_positive": most_positive,
        "most_negative": most_negative,
    }


def analyze_text(text: str) -> dict:
    """Analyze sentiment of a single text string.

    Useful for analyzing transcription text or individual passages.
    """
    analyzer = get_analyzer()
    scores = analyzer.polarity_scores(text)

    return {
        "compound": scores["compound"],
        "positive": scores["pos"],
        "negative": scores["neg"],
        "neutral": scores["neu"],
        "sentiment": classify_sentiment(scores["compound"]),
    }
