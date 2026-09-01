import sys
import os
from PyQt5 import QtWidgets, QtCore
import yt_dlp


def make_alpha_numeric(string):
    return ''.join(char for char in string if char.isalnum())


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
            # Step 1: lightweight listing first (fast, avoids full metadata fetch per video)
            list_opts = {
                'extract_flat': 'in_playlist',
                'quiet': True,
            }
            if self.ffmpeg_location:
                list_opts['ffmpeg_location'] = self.ffmpeg_location

            with yt_dlp.YoutubeDL(list_opts) as ydl:
                playlist_info = ydl.extract_info(self.link, download=False)

            playlist_title = make_alpha_numeric(playlist_info.get('title', 'playlist'))
            entries = [e for e in playlist_info['entries'] if e]
            total_count = len(entries)

            if not os.path.exists(playlist_title):
                os.mkdir(playlist_title)

            self.progress.emit(f"Total videos: {total_count}")

            if self.file_format == 'mp3':
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(playlist_title, '%(title)s.%(ext)s'),
                    'quiet': False,
                    'ignoreerrors': True,
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
                    'format': 'bestvideo+bestaudio/best',
                    'merge_output_format': 'mp4',
                    'outtmpl': os.path.join(playlist_title, '%(title)s.%(ext)s'),
                    'quiet': False,
                    'ignoreerrors': True,
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
        label = QtWidgets.QLabel("Playlist URL:")
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
            QtWidgets.QMessageBox.warning(self, "Warning", "Please enter a valid playlist URL.")
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