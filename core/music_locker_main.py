import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yt_dlp
import threading


def get_ffmpeg_path():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(__file__)

    ffmpeg_path = os.path.join(base_dir, 'ffmpeg.exe')
    if os.path.exists(ffmpeg_path):
        return ffmpeg_path
    return "ffmpeg"

FFMPEG_PATH = get_ffmpeg_path()


class YouTubeAudioDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YT Music Locker Downloader")
        self.root.geometry("1280x720")
        self.temp_dir = os.path.join(os.getcwd(), "temp_audio")
        os.makedirs(self.temp_dir, exist_ok=True)

        self.setup_ui()

    def setup_ui(self):
        tk.Label(self.root, text="Add link:").pack(pady=5)
        self.url_entry = tk.Entry(self.root, width=50)
        self.url_entry.pack(pady=5)

        self.find_btn = tk.Button(self.root, text="Find", command=self.start_fetch_video_info)
        self.find_btn.pack(pady=10)

        self.info_frame = tk.LabelFrame(self.root, text="File info")
        self.info_frame.pack(pady=10, fill="x", padx=10)

        self.info_label = tk.Label(self.info_frame, text="Data...", justify="left")
        self.info_label.pack(pady=5, padx=5)

        self.settings_frame = tk.LabelFrame(self.root, text="Audio settings")
        self.settings_frame.pack(pady=10, fill="x", padx=10)

        tk.Label(self.settings_frame, text="Format:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.format_var = tk.StringVar(value="mp3")
        formats = ["mp3", "aac", "opus"]
        for i, fmt in enumerate(formats):
            tk.Radiobutton(self.settings_frame, text=fmt.upper(), variable=self.format_var, value=fmt).grid(row=0,
                                                                                                            column=i + 1,
                                                                                                            padx=5,
                                                                                                            pady=5)

        tk.Label(self.settings_frame, text="Bitrate (kbp/s):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.bitrate_var = tk.StringVar(value="320")
        bitrates = ["128", "192", "256", "320"]
        for i, br in enumerate(bitrates):
            tk.Radiobutton(self.settings_frame, text=br, variable=self.bitrate_var, value=br).grid(row=1, column=i + 1,
                                                                                                   padx=5, pady=5)

        self.download_btn = tk.Button(self.root, text="Download", command=self.download_audio, state="disabled")
        self.download_btn.pack(pady=10)

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=10)

    def start_fetch_video_info(self):
        thread = threading.Thread(target=self.fetch_video_info)
        thread.start()

    def fetch_video_info(self):
        url = self.url_entry.get()
        if not url:
            self.root.after(0, lambda: messagebox.showerror("Error", "Video link is required!"))
            return

        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                print(f"Fetching video info for URL: {url}")
                info = ydl.extract_info(url, download=False)
                print("Video info fetched successfully.")
                audio_info = self.get_best_audio(info)

                info_text = (
                    f"Title: {info.get('title', 'N/A')}\n"
                    f"Origin audio: {audio_info['abr']} kbp/s ({audio_info['acodec']})\n"
                    f"Suggestion: {self.get_recommendation(audio_info['abr'])}"
                )
                self.root.after(0, lambda: self.info_label.config(text=info_text))
                self.root.after(0, lambda: self.download_btn.config(state="normal"))

        except Exception as e:
            print(f"Error fetching video info: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to get data: {e}"))

    def get_best_audio(self, info):
        best_audio = {'abr': 0, 'acodec': 'unknown'}
        for fmt in info.get('formats', []):
            if fmt.get('acodec') != 'none':
                if fmt.get('abr', 0) > best_audio['abr']:
                    best_audio = {
                        'abr': fmt['abr'],
                        'acodec': fmt['acodec'],
                    }
        return best_audio

    def get_recommendation(self, abr):
        if abr >= 256:
            return "Convert to 320 kbp/s (origin has flawless quality)."
        elif abr >= 160:
            return "Convert to 256–320 kbp/s (average quality origin)."
        else:
            return "High bitrate is a placebo (poor quality origin)."

    def download_audio(self):
        save_dir = filedialog.askdirectory(title="Select save directory")
        if not save_dir:
            return
        url = self.url_entry.get()
        format_ = self.format_var.get()
        bitrate = self.bitrate_var.get()
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(self.temp_dir, '%(title)s.%(ext)s'),
            'postprocessors': [],
            'quiet': True,
            'progress_hooks': [self.progress_hook],
            'nocheckcertificate': True,
            'geo_bypass': True,
            'verbose': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"Downloading audio for URL: {url}")
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                ext = '.mp3' if format_ == 'mp3' else '.m4a' if format_ == 'aac' else '.opus'
                final_path = os.path.join(save_dir, os.path.basename(filename).split('.')[0] + ext)
                if os.path.exists(filename):
                    os.rename(filename, final_path)
                    messagebox.showinfo("Success!", f"File saved to:\n{final_path}")
                else:
                    messagebox.showerror("Error", "Failed to save file.")
        except Exception as e:
            print(f"Error during download: {e}")

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            percent = float(d['_percent_str'].replace('%', ''))
            self.progress['value'] = percent
            self.root.update_idletasks()

    def clean_temp_files(self):
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeAudioDownloader(root)
    root.mainloop()
