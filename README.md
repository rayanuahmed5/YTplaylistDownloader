# YTplaylistDownloader

Download entire YouTube playlists as high-quality MP4 videos or MP3 audio, using either a command-line script or a simple desktop GUI.

## Features

- Download full YouTube playlists in one go
- Choose between MP3 (audio, 320kbps) or MP4 (best available video + audio quality)
- Automatically organizes downloads into a folder named after the playlist
- Skips/reports errors on individual unavailable videos instead of stopping the whole download
- GUI version with a simple point-and-click interface (PyQt5)

## Requirements

- Python 3.8 or newer
- [ffmpeg](https://ffmpeg.org/download.html) (required for MP4 merging and MP3 conversion)

## Installation

1. **Clone the repository**
   ```
   git clone https://github.com/rayanuahmed5/YTplaylistDownloader.git
   cd YTplaylistDownloader
   ```

2. **Install Python dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Install ffmpeg** (if you don't already have it)

   **Windows:**
   ```
   winget install ffmpeg
   ```
   Or download manually from [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/), extract it, and add the `bin` folder to your PATH.

   **Mac:**
   ```
   brew install ffmpeg
   ```

   **Linux:**
   ```
   sudo apt install ffmpeg
   ```

   Verify it's installed:
   ```
   ffmpeg -version
   ```

## Usage

### CLI version

Run:
```
python ytplaylist_downloader.py
```

You'll be prompted to:
1. Enter the playlist URL
2. Choose MP3 or MP4

The script will create a folder named after the playlist and download every video into it.

### GUI version

Run:
```
python app.py
```

In the window:
1. Paste the playlist URL
2. Select MP3 or MP4
3. (Optional) If ffmpeg isn't on your system PATH, click "Browse..." and select your ffmpeg `bin` folder
4. Click **Download**

Progress and any errors will appear in the log area at the bottom of the window.

## Notes

- If you get a `sign in to confirm you're not a bot` or age-restriction error, you may need to pass cookies from your browser. See the [yt-dlp cookies documentation](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp) for details.
- Downloaded files are excluded from Git via `.gitignore` — this repo is meant to hold the scripts, not the downloaded media.
- MP4 downloads use `bestvideo+bestaudio` to get the highest quality available (often higher than YouTube's default pre-muxed formats).

## Disclaimer

This tool is intended for downloading content you have the right to download (e.g. your own uploads, Creative Commons content, or content where the platform's terms permit it). Respect copyright and YouTube's Terms of Service when using this tool.
