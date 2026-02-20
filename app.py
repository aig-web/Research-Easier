import os
import shutil
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

from src.database import init_db, insert_idea, get_all_ideas, get_ideas_by_week, get_category_summary, delete_idea
from src.tweet_extractor import extract_tweet_data, is_twitter_url
from src.analyzer import analyze_tweet_text, analyze_video

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    if not is_twitter_url(url):
        return jsonify({"error": "Please provide a valid Twitter/X link"}), 400

    # Extract tweet data
    tweet_data = extract_tweet_data(url)

    if not tweet_data.get("success"):
        return jsonify({"error": tweet_data.get("error", "Failed to extract tweet")}), 400

    # Analyze tweet text with Gemini
    analysis = analyze_tweet_text(
        tweet_data.get("tweet_text", ""),
        tweet_data.get("author_handle", ""),
    )

    # Analyze video if present
    video_analysis = None
    if tweet_data.get("has_video") and tweet_data.get("video_path"):
        video_analysis = analyze_video(tweet_data["video_path"])

    # Clean up temp files
    temp_dir = tweet_data.get("temp_dir")
    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)

    # Store in database
    idea_data = {
        "tweet_url": tweet_data["tweet_url"],
        "tweet_text": tweet_data.get("tweet_text", ""),
        "author": tweet_data.get("author", ""),
        "author_handle": tweet_data.get("author_handle", ""),
        "topic_name": analysis.get("topic_name", ""),
        "summary": analysis.get("summary", ""),
        "tweet_date": tweet_data.get("tweet_date", ""),
        "view_count": tweet_data.get("view_count", "N/A"),
        "has_video": tweet_data.get("has_video", False),
        "video_analysis": video_analysis,
        "category": analysis.get("category", "Other"),
    }

    idea_id = insert_idea(idea_data)
    idea_data["id"] = idea_id

    return jsonify({"success": True, "idea": idea_data})


@app.route("/api/ideas", methods=["GET"])
def list_ideas():
    ideas = get_all_ideas()
    return jsonify({"ideas": ideas})


@app.route("/api/ideas/weekly", methods=["GET"])
def weekly_ideas():
    weekly = get_ideas_by_week()
    categories = get_category_summary()
    return jsonify({"weekly": weekly, "categories": categories})


@app.route("/api/ideas/<int:idea_id>", methods=["DELETE"])
def remove_idea(idea_id):
    delete_idea(idea_id)
    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
