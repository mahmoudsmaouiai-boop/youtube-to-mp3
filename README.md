# YouTube to MP3

A local web app that converts YouTube videos to MP3 files (192kbps, max 30 min).

## Prerequisites

- Python 3.8+
- **ffmpeg** must be installed and available in your PATH

### Install ffmpeg on Windows

Option 1 — via winget:
```
winget install ffmpeg
```

Option 2 — via Chocolatey:
```
choco install ffmpeg
```

Option 3 — manually: download from https://ffmpeg.org/download.html, extract, and add the `bin/` folder to your PATH.

Verify with:
```
ffmpeg -version
```

## Setup & Run

```bash
# 1. Navigate to the project folder
cd youtube-to-mp3

# 2. Create virtual environment
python -m venv venv

# 3. Activate it (Windows CMD)
venv\Scripts\activate

# 3. Activate it (Windows PowerShell)
venv\Scripts\Activate.ps1

# 3. Activate it (Git Bash / WSL)
source venv/Scripts/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the app
python app.py
```

Open your browser at: **http://127.0.0.1:5000**

## Project Structure

```
youtube-to-mp3/
├── app.py              # Flask backend
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Frontend (self-contained)
├── downloads/          # MP3 output files
└── venv/               # Virtual environment (not committed)
```

## Notes

- Downloaded MP3s are saved to the `/downloads` folder on the server.
- The browser also receives the file as a direct download.
- Videos longer than 30 minutes are rejected.
