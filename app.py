import os
import re
import time
import requests
from flask import Flask, request, jsonify, render_template, redirect

app = Flask(__name__)

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "youtube-mp3-audio-video-downloader.p.rapidapi.com"

YOUTUBE_URL_PATTERN = re.compile(
    r"^(https?://)?(www\.)?"
    r"(youtube\.com/(watch\?v=|shorts/|embed/)|youtu\.be/)"
    r"[\w\-]{11}"
)


def is_valid_youtube_url(url: str) -> bool:
    return bool(YOUTUBE_URL_PATTERN.match(url.strip()))


def extract_video_id(url: str) -> str | None:
    patterns = [
        r"[?&]v=([\w\-]{11})",          # youtube.com/watch?v=ID
        r"youtu\.be/([\w\-]{11})",       # youtu.be/ID
        r"youtube\.com/shorts/([\w\-]{11})",  # youtube.com/shorts/ID
        r"youtube\.com/embed/([\w\-]{11})",   # youtube.com/embed/ID
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():
    if not RAPIDAPI_KEY:
        return jsonify({"error": "Server misconfiguration: RAPIDAPI_KEY is not set."}), 500

    data = request.get_json(silent=True)
    if not data or "url" not in data:
        return jsonify({"error": "Missing URL in request body."}), 400

    url = data["url"].strip()

    if not is_valid_youtube_url(url):
        return jsonify({"error": "Invalid YouTube URL. Please enter a valid youtube.com or youtu.be link."}), 400

    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({"error": "Could not extract video ID from URL."}), 400

    print(f"[RapidAPI] Requesting video_id={video_id}", flush=True)

    try:
        response = requests.get(
            f"https://{RAPIDAPI_HOST}/get_mp3_download_link/{video_id}",
            headers={
                "x-rapidapi-host": RAPIDAPI_HOST,
                "x-rapidapi-key": RAPIDAPI_KEY,
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        print(f"[RapidAPI] status={response.status_code}", flush=True)
        print(f"[RapidAPI] raw body: {response.text}", flush=True)
        response.raise_for_status()
        result = response.json()
        print(f"[RapidAPI] parsed keys: {list(result.keys())}", flush=True)
        print(f"[RapidAPI] parsed result: {result}", flush=True)
    except requests.exceptions.Timeout:
        print("[RapidAPI] Request timed out", flush=True)
        return jsonify({"error": "Request timed out. Please try again."}), 502
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code
        print(f"[RapidAPI] HTTP error {status} body={e.response.text!r}", flush=True)
        if status == 403:
            return jsonify({"error": "API key invalid or quota exceeded."}), 502
        return jsonify({"error": f"API error ({status})."}), 502
    except Exception as e:
        print(f"[RapidAPI] Unexpected error: {e}", flush=True)
        return jsonify({"error": f"Network error: {str(e)}"}), 502

    file_url = result.get("file") or result.get("link") or result.get("download_url") or result.get("url")
    if not file_url:
        return jsonify({"error": "API did not return a file URL. The video may be unavailable.", "raw": result}), 400

    print(f"[RapidAPI] file URL: {file_url} — starting poll", flush=True)

    # Poll until the file is ready (200) or we time out (60 attempts × 5s = 5 min)
    MAX_ATTEMPTS = 60
    POLL_INTERVAL = 5  # seconds

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            poll = requests.get(file_url, timeout=10, allow_redirects=True)
        except Exception as e:
            print(f"[poll {attempt}] request error: {e}", flush=True)
            time.sleep(POLL_INTERVAL)
            continue

        print(f"[poll {attempt}/{MAX_ATTEMPTS}] status={poll.status_code}", flush=True)

        if poll.status_code == 200:
            return jsonify({"download_url": file_url})

        if poll.status_code not in (404, 202, 204):
            # Unexpected status — stop early rather than keep hammering
            return jsonify({"error": f"File URL returned unexpected status {poll.status_code}."}), 502

        time.sleep(POLL_INTERVAL)

    return jsonify({"error": "File was not ready after 5 minutes. Please try again."}), 504


if __name__ == "__main__":
    app.run(debug=True)
