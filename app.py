import sys
import os
import platform
import shutil
import subprocess
from PyQt5 import QtWidgets, QtCore
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

    system = platform.system()

    try:
        if system == 'Windows':
            subprocess.run(
                ['winget', 'install', '-e', '--id', 'DenoLand.Deno', '--accept-package-agreements',
                 '--accept-source-agreements'],
                check=True,
            )
        elif system == 'Darwin':
            if shutil.which('brew'):
                subprocess.run(['brew', 'install', 'deno'], check=True)
            else:
                subprocess.run(['sh', '-c', 'curl -fsSL https://deno.land/install.sh | sh'], check=True)
        elif system == 'Linux':
            subprocess.run(['sh', '-c', 'curl -fsSL https://deno.land/install.sh | sh'], check=True)
        else:
            return None
    except Exception:
        return None

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

    return None


class DownloadWorker(QtCore.QThread):
    progress = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(str)

    def __init__(self, link, file_format, ffmpeg_location=None, parent=None):
        super().__init__(parent)
        self.link = link
        self.file_format = file_format  # 'mp3' or 'mp4'
        self.ffmpeg_location = ffmpeg_location

    def run(self):
        try:
            self.progress.emit("Checking for a JS runtime (deno)...")
            deno_path = ensure_deno()
            js_runtime_opts = {'js_runtimes': [f'deno:{deno_path}']} if deno_path else {}
            if deno_path:
                self.progress.emit(f"Using JS runtime: {deno_path}")
            else:
                self.progress.emit("No JS runtime found/installed — continuing without one "
                                    "(some formats may be unavailable).")

            # Step 1: lightweight listing first (fast, avoids full metadata fetch per video)
            list_opts = {
                'extract_flat': 'in_playlist',
                'quiet': True,
                **js_runtime_opts,
            }
            if self.ffmpeg_location:
                list_opts['ffmpeg_location'] = self.ffmpeg_location

            try:
                with yt_dlp.YoutubeDL(list_opts) as ydl:
                    playlist_info = ydl.extract_info(self.link, download=False)
            except Exception as e:
                self.error.emit(f"Failed to fetch info for that URL: {e}")
                return

            if playlist_info is None:
                self.error.emit("Could not extract any info from that URL. Is it valid/public?")
                return

            # Handle both playlists (have 'entries') and single videos (no 'entries' key)
            raw_entries = playlist_info.get('entries')
            if raw_entries is None:
                entries = [playlist_info]
                folder_title = playlist_info.get('title', 'video')
            else:
                entries = [e for e in raw_entries if e]
                folder_title = playlist_info.get('title', 'playlist')

            folder_title = make_alpha_numeric(folder_title) or 'downloads'
            total_count = len(entries)

            if total_count == 0:
                self.error.emit("No downloadable videos found at that URL "
                                 "(all entries may be private/deleted).")
                return

            os.makedirs(folder_title, exist_ok=True)

            self.progress.emit(f"Total videos: {total_count}")

            common_opts = {
                'outtmpl': os.path.join(folder_title, '%(title)s.%(ext)s'),
                'quiet': False,
                'ignoreerrors': True,
                'restrictfilenames': True,
                **js_runtime_opts,
            }

            if self.file_format == 'mp3':
                ydl_opts = {
                    **common_opts,
                    'format': 'bestaudio/best',
                    'postprocessors': [
                        {
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '320',
                        }
                    ],
                }
            else:
                ydl_opts = {
                    **common_opts,
                    'format': 'bestvideo+bestaudio/best',
                    'merge_output_format': 'mp4',
                }

            if self.ffmpeg_location:
                ydl_opts['ffmpeg_location'] = self.ffmpeg_location

            with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                for i, video in enumerate(entries, start=1):
                    url = video.get('url') or video.get('webpage_url') or f"https://www.youtube.com/watch?v={video.get('id')}"
                    title = video.get('title', url)
                    self.progress.emit(f"Downloading ({i}/{total_count}): {title}")
                    try:
                        ydl2.download([url])
                        self.progress.emit(f"Downloaded: {title} ✨")
                    except Exception as e:
                        self.progress.emit(f"Error downloading {title}: {e}")

            self.finished.emit()
        except Exception as e:
            self.error.emit(f"Download failed: {e}")


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Playlist Downloader")
        self.resize(600, 450)
        self.setup_ui()
        self.worker = None

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout()

        # URL input layout
        url_layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("URL (playlist or single video):")
        self.url_input = QtWidgets.QLineEdit()
        url_layout.addWidget(label)
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)

        # Format choice
        format_layout = QtWidgets.QHBoxLayout()
        format_label = QtWidgets.QLabel("Format:")
        self.mp3_radio = QtWidgets.QRadioButton("MP3 (audio only)")
        self.mp4_radio = QtWidgets.QRadioButton("MP4 (best quality video)")
        self.mp4_radio.setChecked(True)
        format_group = QtWidgets.QButtonGroup(self)
        format_group.addButton(self.mp3_radio)
        format_group.addButton(self.mp4_radio)
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.mp4_radio)
        format_layout.addWidget(self.mp3_radio)
        layout.addLayout(format_layout)

        # Optional ffmpeg location
        ffmpeg_layout = QtWidgets.QHBoxLayout()
        ffmpeg_label = QtWidgets.QLabel("ffmpeg folder (optional):")
        self.ffmpeg_input = QtWidgets.QLineEdit()
        self.ffmpeg_input.setPlaceholderText(r"e.g. C:\ffmpeg\bin  (leave blank if ffmpeg is on PATH)")
        browse_btn = QtWidgets.QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_ffmpeg)
        ffmpeg_layout.addWidget(ffmpeg_label)
        ffmpeg_layout.addWidget(self.ffmpeg_input)
        ffmpeg_layout.addWidget(browse_btn)
        layout.addLayout(ffmpeg_layout)

        # Download button
        self.btn_download = QtWidgets.QPushButton("Download")
        self.btn_download.clicked.connect(self.on_download)
        layout.addWidget(self.btn_download)

        # Log area
        self.log_area = QtWidgets.QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

        self.setLayout(layout)

    def browse_ffmpeg(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select ffmpeg bin folder")
        if folder:
            self.ffmpeg_input.setText(folder)

    def log(self, message):
        self.log_area.append(message)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def on_download(self):
        link = self.url_input.text().strip()
        if not link:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please enter a valid URL.")
            return

        file_format = 'mp3' if self.mp3_radio.isChecked() else 'mp4'
        ffmpeg_location = self.ffmpeg_input.text().strip() or None

        self.btn_download.setEnabled(False)
        self.log(f"Starting download as {file_format.upper()}...")

        self.worker = DownloadWorker(link, file_format, ffmpeg_location)
        self.worker.progress.connect(self.log)
        self.worker.error.connect(self.handle_error)
        self.worker.finished.connect(self.handle_finished)
        self.worker.start()

    def handle_error(self, err_msg):
        QtWidgets.QMessageBox.critical(self, "Error", err_msg)
        self.btn_download.setEnabled(True)

    def handle_finished(self):
        QtWidgets.QMessageBox.information(self, "Success", "All videos downloaded successfully!")
        self.log("Download complete!")
        self.btn_download.setEnabled(True)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())