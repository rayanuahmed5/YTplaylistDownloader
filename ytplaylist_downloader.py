import os
import platform
import shutil
import subprocess
import yt_dlp


def make_alpha_numeric(string):
    return ''.join(char for char in string if char.isalnum())


def ensure_deno():
    """
    Make sure a JS runtime (deno) is available for yt-dlp so YouTube extraction
    doesn't fall back to a degraded mode. Returns the path to the deno
    executable if available (after installing it if needed), or None if it
    could not be found/installed.
    """
    deno_path = shutil.which('deno')
    if deno_path:
        return deno_path

    print("No JS runtime found — attempting to install Deno automatically...")
    system = platform.system()

    try:
        if system == 'Windows':
            # winget ships with modern Windows 10/11
            subprocess.run(
                ['winget', 'install', '-e', '--id', 'DenoLand.Deno', '--accept-package-agreements',
                 '--accept-source-agreements'],
                check=True,
            )
        elif system == 'Darwin':
            if shutil.which('brew'):
                subprocess.run(['brew', 'install', 'deno'], check=True)
            else:
                subprocess.run(
                    ['sh', '-c', 'curl -fsSL https://deno.land/install.sh | sh'],
                    check=True,
                )
        elif system == 'Linux':
            subprocess.run(
                ['sh', '-c', 'curl -fsSL https://deno.land/install.sh | sh'],
                check=True,
            )
        else:
            print(f"Unrecognized OS '{system}' — please install Deno manually: "
                  f"https://docs.deno.com/runtime/getting_started/installation/")
            return None
    except Exception as e:
        print(f"Automatic Deno install failed ({e}). "
              f"Install it manually from https://docs.deno.com/runtime/getting_started/installation/ "
              f"and re-run this script.")
        return None

    # winget/curl installers may not update PATH for the current process,
    # so check the common install locations as a fallback.
    deno_path = shutil.which('deno')
    if deno_path:
        return deno_path

    candidates = [
        os.path.expanduser('~/.deno/bin/deno.exe'),
        os.path.expanduser('~/.deno/bin/deno'),
        os.path.expandvars(r'%USERPROFILE%\.deno\bin\deno.exe'),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    print("Deno was installed but couldn't be located automatically. "
          "You may need to restart your terminal for PATH changes to take effect. "
          "Continuing without a JS runtime for now.")
    return None


deno_path = ensure_deno()
js_runtime_opts = {'js_runtimes': [f'deno:{deno_path}']} if deno_path else {}
if deno_path:
    print(f"Using JS runtime: {deno_path}")
else:
    print("Continuing without a JS runtime — some formats may be unavailable.")


def get_format_choice():
    while True:
        choice = input("Download as (1) MP3 or (2) MP4? Enter 1 or 2: ").strip()
        if choice in ('1', '2'):
            return 'mp3' if choice == '1' else 'mp4'
        print("Invalid choice. Please enter 1 or 2.")


link = input("Enter YouTube URL (playlist or single video): ✨").strip()
file_format = get_format_choice()

# Step 1: lightweight listing first (fast, avoids full-metadata fetch for every video)
list_opts = {
    'extract_flat': 'in_playlist',
    'quiet': True,
    **js_runtime_opts,
}

try:
    with yt_dlp.YoutubeDL(list_opts) as ydl:
        playlist_info = ydl.extract_info(link, download=False)
except Exception as e:
    print(f"Failed to fetch info for that URL: {e}")
    raise SystemExit(1)

if playlist_info is None:
    print("Could not extract any info from that URL. Is it valid/public?")
    raise SystemExit(1)

# Handle both playlists (have 'entries') and single videos (no 'entries' key)
raw_entries = playlist_info.get('entries')
if raw_entries is None:
    # Single video — treat it as a one-item list
    entries = [playlist_info]
    folder_title = playlist_info.get('title', 'video')
else:
    entries = [e for e in raw_entries if e]  # drop None entries (deleted/private videos)
    folder_title = playlist_info.get('title', 'playlist')

folder_title = make_alpha_numeric(folder_title) or 'downloads'
total = len(entries)

if total == 0:
    print("No downloadable videos found at that URL (all entries may be private/deleted).")
    raise SystemExit(1)

print("Total videos to download: 🎦", total)

os.makedirs(folder_title, exist_ok=True)

common_opts = {
    'outtmpl': os.path.join(folder_title, '%(title)s.%(ext)s'),
    'quiet': False,
    'ignoreerrors': True,
    'restrictfilenames': True,  # sanitize video titles for safe cross-platform filenames
    # 'cookiesfrombrowser': ('chrome',),  # uncomment if you hit "sign in to confirm" errors
    **js_runtime_opts,
}

if file_format == 'mp3':
    ydl_opts = {
        **common_opts,
        'format': 'bestaudio/best',
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',  # highest practical mp3 quality
            }
        ],
    }
else:
    ydl_opts = {
        **common_opts,
        # bestvideo+bestaudio picks the highest quality video and audio streams available
        # and merges them, giving you the best possible mp4 quality (often beyond what
        # a single pre-muxed format offers)
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
    }

with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
    for index, video in enumerate(entries, start=1):
        url = video.get('url') or video.get('webpage_url') or f"https://www.youtube.com/watch?v={video.get('id')}"
        title = video.get('title', url)
        try:
            print(f"\nDownloading: {title}")
            ydl2.download([url])
            print(f"Downloaded: {title} ✨ successfully!")
            print("Remaining videos:", total - index)
        except Exception as e:
            print(f"Error downloading {title}: {e}")

print("\nAll videos downloaded successfully! 🎉")