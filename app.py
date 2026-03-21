import os
import re
import yt_dlp
from flask import Flask, request, jsonify, render_template, send_file

app = Flask(__name__)

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "downloads")
MAX_DURATION_SECONDS = 30 * 60  # 30 minutes

YOUTUBE_URL_PATTERN = re.compile(
    r"^(https?://)?(www\.)?"
    r"(youtube\.com/(watch\?v=|shorts/|embed/)|youtu\.be/)"
    r"[\w\-]{11}"
)


def is_valid_youtube_url(url: str) -> bool:
    return bool(YOUTUBE_URL_PATTERN.match(url.strip()))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():
    data = request.get_json(silent=True)
    if not data or "url" not in data:
        return jsonify({"error": "Missing URL in request body."}), 400

    url = data["url"].strip()

    if not is_valid_youtube_url(url):
        return jsonify({"error": "Invalid YouTube URL. Please enter a valid youtube.com or youtu.be link."}), 400

    # Probe video info before downloading
    probe_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(probe_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        if "Private video" in msg or "This video is private" in msg:
            return jsonify({"error": "This video is private or unavailable."}), 400
        if "Video unavailable" in msg or "removed" in msg.lower():
            return jsonify({"error": "This video is unavailable or has been removed."}), 400
        return jsonify({"error": f"Could not fetch video info: {msg}"}), 400
    except Exception as e:
        return jsonify({"error": f"Network or connection error: {str(e)}"}), 502

    duration = info.get("duration", 0)
    if duration and duration > MAX_DURATION_SECONDS:
        minutes = duration // 60
        return jsonify({
            "error": f"Video is too long ({minutes} min). Maximum allowed duration is 30 minutes."
        }), 400

    title = info.get("title", "audio")
    # Sanitize filename
    safe_title = re.sub(r'[<>:"/\\|?*]', "_", title).strip()
    output_path = os.path.join(DOWNLOADS_DIR, f"{safe_title}.%(ext)s")

    download_opts = {
        # Select the best audio-only stream; never pull a video track
        "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
        "format_sort": ["abr", "asr"],   # rank by audio bitrate, then sample rate
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": True,
        # Skip downloading any video stream entirely
        "skip_download": False,          # we do want the audio file
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    try:
        with yt_dlp.YoutubeDL(download_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Conversion error: {str(e)}"}), 500

    mp3_path = os.path.join(DOWNLOADS_DIR, f"{safe_title}.mp3")
    if not os.path.exists(mp3_path):
        return jsonify({"error": "Conversion failed — MP3 file not found. Make sure ffmpeg is installed."}), 500

    return send_file(
        mp3_path,
        mimetype="audio/mpeg",
        as_attachment=True,
        download_name=f"{safe_title}.mp3",
    )


if __name__ == "__main__":
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    app.run(debug=True)
