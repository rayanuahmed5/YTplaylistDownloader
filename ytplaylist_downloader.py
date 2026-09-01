import os
import yt_dlp


def make_alpha_numeric(string):
    return ''.join(char for char in string if char.isalnum())


def get_format_choice():
    while True:
        choice = input("Download as (1) MP3 or (2) MP4? Enter 1 or 2: ").strip()
        if choice in ('1', '2'):
            return 'mp3' if choice == '1' else 'mp4'
        print("Invalid choice. Please enter 1 or 2.")


link = input("Enter YouTube Playlist URL: ✨")
file_format = get_format_choice()

# Step 1: lightweight listing first (fast, avoids full-metadata fetch for every video)
list_opts = {
    'extract_flat': 'in_playlist',
    'quiet': True,
}

with yt_dlp.YoutubeDL(list_opts) as ydl:
    playlist_info = ydl.extract_info(link, download=False)

playlist_title = make_alpha_numeric(playlist_info.get('title', 'playlist'))
entries = [e for e in playlist_info['entries'] if e]  # drop None entries (deleted/private videos)
total = len(entries)
print("Total videos in playlist: 🎦", total)

if not os.path.exists(playlist_title):
    os.mkdir(playlist_title)

if file_format == 'mp3':
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(playlist_title, '%(title)s.%(ext)s'),
        'quiet': False,
        'ignoreerrors': True,
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',  # highest practical mp3 quality
            }
        ],
        # 'cookiesfrombrowser': ('chrome',),  # uncomment if you hit "sign in to confirm" errors
    }
else:
    ydl_opts = {
        # bestvideo+bestaudio picks the highest quality video and audio streams available
        # and merges them, giving you the best possible mp4 quality (often beyond what
        # a single pre-muxed format offers)
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': os.path.join(playlist_title, '%(title)s.%(ext)s'),
        'quiet': False,
        'ignoreerrors': True,
        # 'cookiesfrombrowser': ('chrome',),  # uncomment if you hit "sign in to confirm" errors
    }

with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
    for index, video in enumerate(entries, start=1):
        url = video.get('url') or video.get('webpage_url') or f"https://www.youtube.com/watch?v={video.get('id')}"
        title = video.get('title', url)
        try:
            print(f"\nDownloading: {title}")
            ydl2.download([url])
            print(f"Downloaded: {title} ✨ successfully!")
            print("Remaining Videos:", total - index)
        except Exception as e:
            print(f"Error downloading {title}: {e}")

print("\nAll videos downloaded successfully! 🎉")