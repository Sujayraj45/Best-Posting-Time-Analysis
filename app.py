import os
import re
import json
import random
import requests
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()  # Load .env file

app = Flask(__name__)

# ─── YouTube API Key (stays on server, never sent to browser) ─────────────────
YT_API_KEY = os.getenv("YT_API_KEY")

# ─── Platform Benchmark Configuration ────────────────────────────────────────
PLATFORM_CONFIGS = {
    "youtube": {
        "name": "YouTube",
        "labels": ["Views", "Likes", "Comments"],
        "peakDay": "Friday",
        "optimalHours": "2:00 PM – 4:00 PM",
        "recommendedDay": "Thursday / Friday",
        "decayTime": "~48 Hours",
        "chartData": [45, 55, 75, 90, 100, 85, 70],
        "avgEngagement": 3.8,
        "brandColor": "#dc2626",
    },
    "instagram": {
        "name": "Instagram",
        "labels": ["Impressions", "Likes", "Comments"],
        "peakDay": "Wednesday",
        "optimalHours": "11:00 AM – 1:00 PM",
        "recommendedDay": "Wednesday",
        "decayTime": "~24 Hours",
        "chartData": [60, 75, 100, 85, 80, 55, 40],
        "avgEngagement": 4.5,
        "brandColor": "#e11d48",
    },
    "linkedin": {
        "name": "LinkedIn",
        "labels": ["Impressions", "Reactions", "Comments"],
        "peakDay": "Wednesday",
        "optimalHours": "8:00 AM – 10:00 AM",
        "recommendedDay": "Tuesday – Thursday",
        "decayTime": "~72 Hours",
        "chartData": [70, 92, 98, 90, 65, 20, 15],
        "avgEngagement": 3.2,
        "brandColor": "#0284c7",
    },
    "twitter": {
        "name": "X (Twitter)",
        "labels": ["Views", "Likes", "Replies"],
        "peakDay": "Wednesday",
        "optimalHours": "9:00 AM – 11:00 AM",
        "recommendedDay": "Wednesday / Friday",
        "decayTime": "~6 Hours",
        "chartData": [68, 78, 95, 82, 90, 50, 42],
        "avgEngagement": 2.1,
        "brandColor": "#334155",
    },
}


# ─── Helpers ──────────────────────────────────────────────────────────────────
def extract_youtube_video_id(url: str) -> str | None:
    """Extract the 11-character video ID from any YouTube URL format."""
    pattern = (
        r"(?:youtube\.com/(?:[^/]+/.+/|(?:v|e(?:mbed)?)/|.*[?&]v=)"
        r"|youtu\.be/|youtube\.com/shorts/)([^\"&?/\s]{11})"
    )
    match = re.search(pattern, url)
    return match.group(1) if match else None


def compute_timing_verdict(published_at: datetime, platform: str) -> dict:
    """Evaluate whether the post's upload time was optimal, average, or suboptimal."""
    day  = published_at.weekday()   # Monday = 0 … Sunday = 6
    hour = published_at.hour

    is_optimal = is_average = False
    explanation = ""

    if platform == "youtube":
        is_optimal = day in (2, 3, 4) and 13 <= hour <= 17
        is_average = 2 <= day <= 6
        explanation = (
            "Posted inside the prime 1 PM – 5 PM window before evening peak."
            if is_optimal else
            "Posted on an active weekday, slightly outside the ideal indexing window."
            if is_average else
            "Posted during off-peak weekend hours."
        )
    elif platform == "instagram":
        is_optimal = day in (2, 3) and 11 <= hour <= 14
        is_average = 0 <= day <= 4 and 9 <= hour <= 21
        explanation = (
            "Aligned directly with lunch-break browsing peaks."
            if is_optimal else
            "Standard weekday visibility."
            if is_average else
            "Off-peak or late night timing."
        )
    elif platform == "linkedin":
        is_optimal = 1 <= day <= 3 and 8 <= hour <= 11
        is_average = 0 <= day <= 4 and 8 <= hour <= 18
        explanation = (
            "Prime business morning window."
            if is_optimal else
            "Standard business hours."
            if is_average else
            "Low traffic weekend timing."
        )
    else:  # twitter / X
        is_optimal = day in (2, 4) and 9 <= hour <= 11
        is_average = 0 <= day <= 4
        explanation = (
            "Optimal morning news reading period."
            if is_optimal else
            "Standard feed timing."
            if is_average else
            "Off-peak feed decline."
        )

    if is_optimal:
        return {"type": "optimal",    "title": "Optimal Timing",    "summary": explanation}
    if is_average:
        return {"type": "average",    "title": "Average Timing",    "summary": explanation}
    return          {"type": "suboptimal", "title": "Suboptimal Timing", "summary": explanation}


def generate_tailored_insights(data: dict, verdict: dict, engagement: float, config: dict) -> list[dict]:
    """Build three performance-tailored insight cards based on actual post metrics."""
    platform       = data["platform"]
    day_name       = data["publishedAt"].strftime("%A")
    time_string    = data["publishedAt"].strftime("%I:%M %p")
    avg_engagement = config["avgEngagement"]

    # 1 — Timing Diagnosis
    if verdict["type"] == "optimal":
        timing_pill   = {"label": "Prime Timing",   "color": "emerald"}
        timing_detail = (
            f"Your upload on <strong>{day_name} at {time_string}</strong> aligned directly "
            f"with {config['name']}'s peak audience activity window, giving your content "
            f"maximal initial exposure."
        )
    elif verdict["type"] == "average":
        timing_pill   = {"label": "Fair Timing",    "color": "amber"}
        timing_detail = (
            f"Your post landed on <strong>{day_name} at {time_string}</strong>. While weekday "
            f"activity was moderate, posting closer to <strong>{config['optimalHours']}</strong> "
            f"would capture peak audience velocity."
        )
    else:
        timing_pill   = {"label": "Off-Peak",       "color": "rose"}
        timing_detail = (
            f"Your upload on <strong>{day_name} at {time_string}</strong> hit an off-peak "
            f"decay period. Feeds were moving slowly, which likely restrained your reach "
            f"during the initial critical hours."
        )

    # 2 — Engagement Rate Evaluation
    diff = engagement - avg_engagement
    if diff >= 1.0:
        eng_pill   = {"label": "Above Average", "color": "emerald"}
        eng_detail = (
            f"At <strong>{engagement:.2f}%</strong>, your engagement rate outperforms the "
            f"platform benchmark (~{avg_engagement}%). Your hook and content resonate strongly."
        )
    elif diff >= -1.0:
        eng_pill   = {"label": "Healthy Standard", "color": "blue"}
        eng_detail = (
            f"At <strong>{engagement:.2f}%</strong>, your engagement rate sits right on target "
            f"with typical {config['name']} averages (~{avg_engagement}%)."
        )
    else:
        eng_pill   = {"label": "Needs Improvement", "color": "amber"}
        eng_detail = (
            f"At <strong>{engagement:.2f}%</strong>, your engagement is below the "
            f"~{avg_engagement}% average. Focusing on early comments within the first "
            f"60 minutes will help."
        )

    # 3 — Next Post Directive
    directives = {
        "youtube":   f"Upload between <strong>{config['optimalHours']} on {config['peakDay']}</strong> "
                     f"to give YouTube's servers 2 hours to index HD video and generate transcripts "
                     f"before prime evening viewing (7–10 PM).",
        "instagram": f"Aim for <strong>{config['optimalHours']} on Wednesday</strong>. Add an engaging "
                     f"question in the first 2 lines of your caption to trigger lunch-break comment velocity.",
        "linkedin":  f"Publish between <strong>{config['optimalHours']} on {config['recommendedDay']}</strong>. "
                     f"Use high-value professional insights to encourage second-degree network resharing.",
        "twitter":   f"Post between <strong>{config['optimalHours']} on Wednesday or Friday</strong> "
                     f"to ride the morning commute and breaking news cycles.",
    }

    return [
        {
            "title":  "Post Timing Diagnosis",
            "pill":   timing_pill,
            "detail": timing_detail,
        },
        {
            "title":  "Engagement Performance",
            "pill":   eng_pill,
            "detail": eng_detail,
        },
        {
            "title":  "Directive For Your Next Post",
            "pill":   {"label": "Action Step", "color": "sky"},
            "detail": directives.get(platform, ""),
        },
    ]


def simulate_platform_data(platform: str, url: str) -> dict:
    """Generate calibrated benchmark data for non-API platforms."""
    from datetime import timedelta

    offset_days  = random.randint(1, 10)
    offset_hours = random.randint(0, 23)
    offset_mins  = random.randint(0, 59)
    published    = datetime.now(timezone.utc) - timedelta(days=offset_days, hours=offset_hours, minutes=offset_mins)

    if platform == "instagram":
        views    = random.randint(3500,  50000)
        likes    = int(views * random.uniform(0.025, 0.08))
        comments = int(likes * random.uniform(0.02,  0.10))
    elif platform == "linkedin":
        views    = random.randint(1800,  25000)
        likes    = int(views * random.uniform(0.02,  0.05))
        comments = int(likes * random.uniform(0.03,  0.15))
    else:  # twitter
        views    = random.randint(4000,  80000)
        likes    = int(views * random.uniform(0.012, 0.03))
        comments = int(likes * random.uniform(0.01,  0.06))

    author = "@creator_profile"
    try:
        from urllib.parse import urlparse
        parts = urlparse(url if url.startswith("http") else f"https://{url}").path.split("/")
        parts = [p for p in parts if p]
        if parts:
            author = f"@{parts[0]}"
    except Exception:
        pass

    config = PLATFORM_CONFIGS[platform]
    return {
        "platform":    platform,
        "title":       f"{config['name']} Post Sample",
        "author":      author,
        "publishedAt": published,
        "thumb":       None,
        "views":       views,
        "likes":       likes,
        "comments":    comments,
        "isLive":      False,
    }


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    """Serve the main dashboard."""
    return render_template("index.html")


@app.route("/api/platform-config")
def platform_config():
    """Return chart and metadata config for all platforms."""
    return jsonify(PLATFORM_CONFIGS)


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """
    POST  { "platform": "youtube"|"instagram"|"linkedin"|"twitter",
             "url": "https://..." }
    Returns full analysis JSON including stats, timing verdict, and tailored insights.
    """
    body     = request.get_json(silent=True) or {}
    platform = body.get("platform", "youtube")
    url      = (body.get("url") or "").strip()

    if not url:
        return jsonify({"error": "No URL provided."}), 400
    if platform not in PLATFORM_CONFIGS:
        return jsonify({"error": f"Unknown platform: {platform}"}), 400

    config = PLATFORM_CONFIGS[platform]

    # ── YouTube: live API call ────────────────────────────────────────────────
    if platform == "youtube":
        if not YT_API_KEY:
            return jsonify({
                "error": "YouTube API key not configured. "
                         "Add YT_API_KEY to your .env file."
            }), 500

        video_id = extract_youtube_video_id(url)
        if not video_id:
            return jsonify({"error": "Invalid YouTube URL."}), 400

        yt_url = (
            f"https://www.googleapis.com/youtube/v3/videos"
            f"?id={video_id}&key={YT_API_KEY}&part=snippet,statistics"
        )
        try:
            resp = requests.get(yt_url, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as exc:
            return jsonify({"error": f"YouTube API request failed: {exc}"}), 502

        yt_data = resp.json()
        if not yt_data.get("items"):
            return jsonify({"error": "Video not found. It may be private or deleted."}), 404

        item    = yt_data["items"][0]
        snippet = item["snippet"]
        stats   = item.get("statistics", {})

        thumb = (
            snippet.get("thumbnails", {}).get("high",    {}).get("url") or
            snippet.get("thumbnails", {}).get("medium",  {}).get("url") or
            snippet.get("thumbnails", {}).get("default", {}).get("url")
        )

        published_at = datetime.fromisoformat(
            snippet["publishedAt"].replace("Z", "+00:00")
        )

        post_data = {
            "platform":    "youtube",
            "title":       snippet["title"],
            "author":      snippet["channelTitle"],
            "publishedAt": published_at,
            "thumb":       thumb,
            "views":       int(stats.get("viewCount",   0)),
            "likes":       int(stats.get("likeCount",   0)),
            "comments":    int(stats.get("commentCount", 0)),
            "isLive":      True,
        }

    # ── Other platforms: benchmark simulation ─────────────────────────────────
    else:
        post_data = simulate_platform_data(platform, url)

    # ── Compute derived metrics ───────────────────────────────────────────────
    views      = post_data["views"]
    likes      = post_data["likes"]
    comments   = post_data["comments"]
    engagement = ((likes + comments) / views * 100) if views > 0 else 0.0

    verdict  = compute_timing_verdict(post_data["publishedAt"], platform)
    insights = generate_tailored_insights(post_data, verdict, engagement, config)

    published_at     = post_data["publishedAt"]
    published_str    = published_at.strftime("%A, %d %b %Y  %I:%M %p")
    day_name         = published_at.strftime("%A")

    return jsonify({
        "platform":    platform,
        "title":       post_data["title"],
        "author":      post_data["author"],
        "publishedAt": published_str,
        "dayName":     day_name,
        "thumb":       post_data["thumb"],
        "isLive":      post_data["isLive"],
        "stats": {
            "views":      views,
            "likes":      likes,
            "comments":   comments,
            "engagement": round(engagement, 2),
        },
        "verdict":  verdict,
        "insights": insights,
        "chartData":        config["chartData"],
        "peakDay":          config["peakDay"],
        "optimalHours":     config["optimalHours"],
        "recommendedDay":   config["recommendedDay"],
        "decayTime":        config["decayTime"],
        "platformName":     config["name"],
        "brandColor":       config["brandColor"],
        "labels":           config["labels"],
    })


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)
