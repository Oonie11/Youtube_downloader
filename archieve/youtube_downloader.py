import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import os
import logging
from datetime import datetime
import threading
from typing import Optional, List, Tuple
import subprocess
import re
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs
import json

# Constants for UI design
DEFAULT_WINDOW_SIZE = "450x650"
BACKGROUND_COLOR = '#1a1a2e'  # Navy Blue
FOREGROUND_COLOR = '#e5e5e5'  # Light Gray
ACCENT_COLOR = '#00aaff'      # Sky Blue
HOVER_COLOR = '#33bbff'       # Light Sky Blue
FONT_FAMILY = 'Segoe UI'
DEFAULT_FONT_SIZE = 9
TITLE_FONT_SIZE = 16
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
ENTRY_BACKGROUND = '#44475a'  # Dark grayish blue
COMBOBOX_BACKGROUND = '#2f3542'  # Darker grayish blue for better contrast

@dataclass
class DownloadOptions:
    url: str
    quality: str
    format: str
    filename: str
    output_path: str
    subtitle: bool

class YouTubeDownloader:
    def __init__(self, master: tk.Tk):
        self.master = master
        self.setup_window()
        self.setup_logging()
        self.setup_variables()
        self.setup_styles()
        self.create_gui_elements()

    def setup_window(self):
        self.master.title("YouTube Downloader")
        self.master.geometry(DEFAULT_WINDOW_SIZE)
        self.master.configure(bg=BACKGROUND_COLOR)
        self.master.resizable(False, False)

    def setup_logging(self):
        log_folder = "logs"
        os.makedirs(log_folder, exist_ok=True)
        log_file = os.path.join(log_folder, f"youtube_downloader_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        logging.basicConfig(filename=log_file, level=logging.INFO, format=LOG_FORMAT)

    def setup_variables(self):
        self.default_download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "YouTubeDownloader")
        os.makedirs(self.default_download_dir, exist_ok=True)
        self.download_location = self.default_download_dir
        self.download_thread: Optional[threading.Thread] = None
        self.stop_download = threading.Event()
        self.available_formats: List[Tuple[str, str, str]] = []
        self.subtitle_var = tk.BooleanVar(value=False)
        self.total_videos = 0
        self.current_video = 0
        self.is_playlist = False

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background=BACKGROUND_COLOR)
        self.style.configure("TLabel", background=BACKGROUND_COLOR, foreground=FOREGROUND_COLOR, font=(FONT_FAMILY, DEFAULT_FONT_SIZE))
        self.style.configure("TEntry", fieldbackground=ENTRY_BACKGROUND, foreground=FOREGROUND_COLOR, font=(FONT_FAMILY, DEFAULT_FONT_SIZE))
        self.style.configure("TButton", background=ACCENT_COLOR, foreground=BACKGROUND_COLOR, font=(FONT_FAMILY, DEFAULT_FONT_SIZE, 'bold'), padding=5)
        self.style.map("TButton", background=[('active', HOVER_COLOR)])
        self.style.configure("Horizontal.TProgressbar", background=ACCENT_COLOR, troughcolor=ENTRY_BACKGROUND)
        self.style.configure("Title.TLabel", font=(FONT_FAMILY, TITLE_FONT_SIZE, 'bold'), foreground=ACCENT_COLOR)
        self.style.configure("TCombobox", fieldbackground=COMBOBOX_BACKGROUND, foreground=FOREGROUND_COLOR, font=(FONT_FAMILY, DEFAULT_FONT_SIZE))
        self.style.map("TCombobox", fieldbackground=[('readonly', COMBOBOX_BACKGROUND)], selectbackground=[('readonly', COMBOBOX_BACKGROUND)])
        self.style.configure("TCheckbutton", background=BACKGROUND_COLOR, foreground=FOREGROUND_COLOR, font=(FONT_FAMILY, DEFAULT_FONT_SIZE))
        self.style.map("TCheckbutton", background=[('active', BACKGROUND_COLOR)])

    def create_gui_elements(self):
        self.main_frame = ttk.Frame(self.master, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.create_title()
        self.create_input_fields()
        self.create_buttons()
        self.create_progress_indicators()
        self.create_location_widgets()

    def create_title(self):
        ttk.Label(self.main_frame, text="YouTube Downloader", style="Title.TLabel").pack(pady=(0, 10))

    def create_input_fields(self):
        self.create_labeled_entry("YouTube URL:", "url_entry", "Enter YouTube URL here")
        self.create_labeled_entry("Custom Filename:", "filename_entry", "Enter custom filename (optional)")
        self.create_quality_dropdown()
        self.create_subtitle_checkbox()
        
        # Add playlist info label
        self.playlist_info_label = ttk.Label(self.main_frame, text="", font=(FONT_FAMILY, DEFAULT_FONT_SIZE))
        self.playlist_info_label.pack(fill=tk.X, pady=(5, 0))

    def create_labeled_entry(self, label_text: str, entry_name: str, default_text: str):
        frame = ttk.Frame(self.main_frame)
        frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(frame, text=label_text, font=(FONT_FAMILY, DEFAULT_FONT_SIZE, 'bold')).pack(anchor='w')
        entry = ttk.Entry(frame, font=(FONT_FAMILY, DEFAULT_FONT_SIZE))
        entry.pack(fill=tk.X, pady=(2, 0))
        entry.insert(0, default_text)
        entry.bind("<FocusIn>", lambda e: self.on_entry_click(e, default_text))
        entry.bind("<FocusOut>", lambda e: self.on_focus_out(e, default_text))
        setattr(self, entry_name, entry)

    def create_quality_dropdown(self):
        frame = ttk.Frame(self.main_frame)
        frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(frame, text="Quality:", font=(FONT_FAMILY, DEFAULT_FONT_SIZE, 'bold')).pack(side=tk.LEFT)
        self.quality_combobox = ttk.Combobox(frame, values=["Best available"], state="readonly", width=25)
        self.quality_combobox.set("Best available")
        self.quality_combobox.pack(side=tk.LEFT, padx=(5, 0))
        self.quality_combobox.bind("<<ComboboxSelected>>", self.on_quality_selected)

        ttk.Button(frame, text="Fetch Formats", command=self.fetch_formats, width=15).pack(side=tk.RIGHT)

    def create_subtitle_checkbox(self):
        frame = ttk.Frame(self.main_frame)
        frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Checkbutton(frame, text="Download subtitle", variable=self.subtitle_var, style="TCheckbutton").pack(anchor='w')

    def create_buttons(self):
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(pady=10, fill=tk.X)

        self.download_button = ttk.Button(button_frame, text="Download", command=self.download, width=20)
        self.download_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        
        ttk.Button(button_frame, text="Reset", command=self.reset_all, width=20).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5, 0))

    def create_progress_indicators(self):
        self.progress = ttk.Progressbar(self.main_frame, orient="horizontal", length=380, mode="determinate")
        self.progress.pack(pady=(10, 5), fill=tk.X)

        self.progress_label = ttk.Label(self.main_frame, text="", font=(FONT_FAMILY, DEFAULT_FONT_SIZE))
        self.progress_label.pack()

    def create_location_widgets(self):
        location_frame = ttk.Frame(self.main_frame)
        location_frame.pack(fill=tk.X, pady=(10, 0))

        self.location_label = ttk.Label(location_frame, text=f"Download Location: {self.download_location}", wraplength=430, font=(FONT_FAMILY, DEFAULT_FONT_SIZE))
        self.location_label.pack(fill=tk.X)

        button_frame = ttk.Frame(location_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(button_frame, text="Change Location", command=self.select_location, width=20).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        self.open_folder_button = ttk.Button(button_frame, text="Open Folder", command=self.open_download_folder, width=20)
        self.open_folder_button.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5, 0))
        self.open_folder_button.pack_forget()

    def on_entry_click(self, event: tk.Event, default_text: str):
        if event.widget.get() == default_text:
            event.widget.delete(0, tk.END)
            event.widget.config(foreground=FOREGROUND_COLOR)

    def on_focus_out(self, event: tk.Event, default_text: str):
        if event.widget.get() == "":
            event.widget.insert(0, default_text)
            event.widget.config(foreground='#6272a4')

    def select_location(self):
        new_location = filedialog.askdirectory()
        if new_location:
            self.download_location = new_location
            self.location_label.config(text=f"Download Location: {self.download_location}")

    def fetch_formats(self):
        url = self.url_entry.get().strip()
        is_valid, url_type = self.is_valid_youtube_url(url)
        if not is_valid:
            self.show_error("Please enter a valid YouTube URL")
            return

        if url_type == 'playlist':
            self.get_playlist_info(url)

        self.download_button.config(state=tk.DISABLED)
        threading.Thread(target=self._fetch_formats, args=(url,)).start()

    @staticmethod
    def is_valid_youtube_url(url: str) -> Tuple[bool, str]:
        try:
            result = urlparse(url)
            if all([result.scheme, result.netloc]) and 'youtube.com' in result.netloc:
                if '/playlist' in result.path:
                    return ('list' in parse_qs(result.query), 'playlist')
                elif '/watch' in result.path:
                    return (True, 'video')
            return (False, '')
        except ValueError:
            return (False, '')

    def _fetch_formats(self, url: str):
        try:
            command = ['yt-dlp', '-F', url]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            
            self.available_formats = self.parse_formats(result.stdout)
            self.update_quality_options()
        except subprocess.CalledProcessError as e:
            self.show_error(f"yt-dlp error: {e.stderr}")
            logging.error(f"yt-dlp error: {e.stderr}")
        except Exception as e:
            self.show_error(f"Error fetching formats: {str(e)}")
            logging.error(f"Error fetching formats: {str(e)}")
        finally:
            self.master.after(0, lambda: self.download_button.config(state=tk.NORMAL))

    @staticmethod
    def parse_formats(output: str) -> List[Tuple[str, str, str]]:
        formats = []
        seen = set()
        for line in output.split('\n'):
            match = re.search(r'(\d+)\s+(\w+)\s+(\d+x\d+|audio only)', line)
            if match:
                format_id, extension, resolution = match.groups()
                key = (resolution, extension)
                if key not in seen:
                    formats.append((format_id, extension, resolution))
                    seen.add(key)
        return formats

    def update_quality_options(self):
        options = ["Best available"] + [f"{res} ({ext})" for _, ext, res in self.available_formats]
        self.quality_combobox['values'] = options
        self.quality_combobox.set("Best available")

    def on_quality_selected(self, event: tk.Event):
        selected = self.quality_combobox.get()
        if selected != "Best available":
            index = self.quality_combobox.current() - 1
            format_id = self.available_formats[index][0]
            self.show_info(f"Selected format ID: {format_id}")

    def get_playlist_info(self, url: str):
        try:
            command = ['yt-dlp', '--flat-playlist', '--dump-json', url]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            
            videos = [json.loads(line) for line in result.stdout.strip().split('\n')]
            self.total_videos = len(videos)
            
            playlist_title = videos[0].get('playlist_title', 'Unknown Playlist')
            self.update_playlist_info(playlist_title, self.total_videos)
            self.is_playlist = True
        except subprocess.CalledProcessError as e:
            self.show_error(f"Error fetching playlist info: {e.stderr}")
            logging.error(f"Error fetching playlist info: {e.stderr}")
        except Exception as e:
            self.show_error(f"Error processing playlist info: {str(e)}")
            logging.error(f"Error processing playlist info: {str(e)}")

    def update_playlist_info(self, title: str, total_videos: int):
        self.master.after(0, lambda: self.playlist_info_label.config(
            text=f"Playlist: {title} ({total_videos} videos)"
        ))

    def download(self):
        url = self.url_entry.get().strip()
        is_valid, url_type = self.is_valid_youtube_url(url)
        if not is_valid:
            self.show_error("Please enter a valid YouTube URL")
            return

        self.stop_download.clear()
        options = self.get_download_options()
        self.download_thread = threading.Thread(target=self.download_thread_function, args=(options,))
        self.download_thread.start()
        self.download_button.config(text="Stop", command=self.stop_download_thread)

    def get_download_options(self) -> DownloadOptions:
        selected_quality = self.quality_combobox.get()
        format_id = 'bestvideo+bestaudio/best'
        
        if selected_quality != "Best available":
            index = self.quality_combobox.current() - 1
            format_id = f"{self.available_formats[index][0]}+bestaudio"

        return DownloadOptions(
            url=self.url_entry.get().strip(),
            quality=selected_quality,
            format=format_id,
            filename=self.get_filename(),
            output_path=self.download_location,
            subtitle=self.subtitle_var.get()
        )

    def stop_download_thread(self):
        self.stop_download.set()
        self.download_button.config(text="Download", command=self.download)

    def download_thread_function(self, options: DownloadOptions):
        try:
            yt_dlp_command = self.build_yt_dlp_command(options)
            self.start_download_process(yt_dlp_command)
        except Exception as e:
            logging.error(f"Error in download_thread_function: {str(e)}")
            self.show_error(f"Unable to download video: {str(e)}")
        finally:
            self.master.after(0, self.reset_download_button)

    def build_yt_dlp_command(self, options: DownloadOptions) -> List[str]:
        command = [
            'yt-dlp',
            '-f', options.format,
            '-o', options.filename,
        ]
        if self.is_playlist:
            command.append('--yes-playlist')
        else:
            command.append('--no-playlist')
        if options.subtitle:
            command.extend(['--write-auto-sub', '--sub-lang', 'en'])
        command.append(options.url)
        return command

    def start_download_process(self, command: list):
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)
            
            for line in process.stdout:
                if self.stop_download.is_set():
                    process.terminate()
                    self.master.after(0, lambda: self.show_info("Download stopped by user"))
                    break
                
                self.parse_output(line)

            process.wait()
            
            if process.returncode == 0 and not self.stop_download.is_set():
                self.master.after(0, lambda: self.on_download_complete(command[-1]))
            elif process.returncode != 0 and not self.stop_download.is_set():
                error_message = process.stderr.read()
                self.master.after(0, lambda: self.show_error(f"Download failed: {error_message}"))
                logging.error(f"Download failed: {error_message}")
        
        except Exception as e:
            self.master.after(0, lambda: self.show_error(f"An error occurred: {str(e)}"))
            logging.error(f"An error occurred in start_download_process: {str(e)}")

    def parse_output(self, line: str):
        if '[download]' in line:
            if 'Downloading video' in line:
                match = re.search(r'Downloading video (\d+) of (\d+)', line)
                if match:
                    self.current_video = int(match.group(1))
                    self.total_videos = int(match.group(2))
            match = re.search(r'(\d+\.\d+)%', line)
            if match:
                percent = float(match.group(1))
                eta_match = re.search(r'ETA (\S+)', line)
                eta = eta_match.group(1) if eta_match else "Unknown"
                self.master.after(0, lambda: self.update_progress(percent, eta))

    def update_progress(self, percent: float, eta: str):
        self.progress['value'] = percent
        if self.is_playlist:
            progress_text = f"Video {self.current_video}/{self.total_videos} - Progress: {percent:.1f}% (ETA: {eta})"
        else:
            progress_text = f"Progress: {percent:.1f}% (ETA: {eta})"
        self.progress_label.config(text=progress_text)
        self.master.update_idletasks()

    def get_filename(self) -> str:
        custom_filename = self.filename_entry.get().strip()
        if custom_filename and custom_filename != "Enter custom filename (optional)":
            return os.path.join(self.download_location, f"{custom_filename}.%(ext)s")
        return os.path.join(self.download_location, "%(title)s.%(ext)s")

    def on_download_complete(self, url: str):
        self.show_info("Download completed successfully!")
        self.open_folder_button.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5, 0))
        logging.info(f"Download completed for URL: {url}")

    def reset_download_button(self):
        self.download_button.config(text="Download", command=self.download)

    def reset_all(self):
        self.reset_entry(self.url_entry, "Enter YouTube URL here")
        self.reset_entry(self.filename_entry, "Enter custom filename (optional)")
        self.quality_combobox.set("Best available")
        self.subtitle_var.set(False)
        self.progress['value'] = 0
        self.progress_label.config(text="")
        self.playlist_info_label.config(text="")
        self.open_folder_button.pack_forget()
        self.total_videos = 0
        self.current_video = 0
        self.is_playlist = False

    def reset_entry(self, entry: ttk.Entry, default_text: str):
        entry.delete(0, tk.END)
        entry.insert(0, default_text)
        entry.config(foreground='#6272a4')

    def show_error(self, message: str):
        messagebox.showerror("Error", message)

    def show_info(self, message: str):
        messagebox.showinfo("Info", message)

    def open_download_folder(self):
        try:
            os.startfile(self.download_location)
        except AttributeError:
            try:
                subprocess.call(['open', self.download_location])
            except:
                subprocess.call(['xdg-open', self.download_location])

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloader(master=root)
    root.mainloop()
