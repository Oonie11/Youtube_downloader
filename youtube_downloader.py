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
from urllib.parse import urlparse

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

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background=BACKGROUND_COLOR)
        self.style.configure("TLabel", background=BACKGROUND_COLOR, foreground=FOREGROUND_COLOR, font=(FONT_FAMILY, DEFAULT_FONT_SIZE))
        self.style.configure("TEntry", fieldbackground='#44475a', foreground=FOREGROUND_COLOR, font=(FONT_FAMILY, DEFAULT_FONT_SIZE))
        self.style.configure("TButton", background=ACCENT_COLOR, foreground=BACKGROUND_COLOR, font=(FONT_FAMILY, DEFAULT_FONT_SIZE, 'bold'), padding=5)
        self.style.map("TButton", background=[('active', HOVER_COLOR)])
        self.style.configure("Horizontal.TProgressbar", background=ACCENT_COLOR, troughcolor='#44475a')
        self.style.configure("Title.TLabel", font=(FONT_FAMILY, TITLE_FONT_SIZE, 'bold'), foreground=ACCENT_COLOR)
        self.style.configure("TCombobox", fieldbackground='#44475a', foreground=FOREGROUND_COLOR, font=(FONT_FAMILY, DEFAULT_FONT_SIZE))
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

    def create_labeled_entry(self, label_text, entry_name, default_text):
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

        ttk.Button(frame, text="Fetch Formats", command=self.fetch_available_formats, width=15).pack(side=tk.RIGHT)

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

    def on_entry_click(self, event, default_text):
        if event.widget.get() == default_text:
            event.widget.delete(0, tk.END)
            event.widget.config(foreground=FOREGROUND_COLOR)

    def on_focus_out(self, event, default_text):
        if event.widget.get() == "":
            event.widget.insert(0, default_text)
            event.widget.config(foreground='#6272a4')

    def select_location(self):
        new_location = filedialog.askdirectory()
        if new_location:
            self.download_location = new_location
            self.location_label.config(text=f"Download Location: {self.download_location}")

    def fetch_available_formats(self):
        url = self.url_entry.get().strip()
        if not self.is_valid_youtube_url(url):
            self.show_error("Please enter a valid YouTube URL")
            return

        self.download_button.config(state=tk.DISABLED)
        threading.Thread(target=self._fetch_formats, args=(url,)).start()

    def is_valid_youtube_url(self, url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and 'youtube.com' in result.netloc
        except ValueError:
            return False

    def _fetch_formats(self, url: str):
        try:
            command = ['yt-dlp', '-F', url]
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"yt-dlp error: {result.stderr}")

            self.available_formats = self.parse_formats(result.stdout)
            self.update_quality_options()
        except Exception as e:
            self.show_error(f"Error fetching formats: {str(e)}")
            logging.error(f"Error fetching formats: {str(e)}")
        finally:
            self.master.after(0, lambda: self.download_button.config(state=tk.NORMAL))

    def parse_formats(self, output: str) -> List[Tuple[str, str, str]]:
        formats = []
        for line in output.split('\n'):
            match = re.search(r'(\d+)\s+(\w+)\s+(\d+x\d+|audio only)', line)
            if match:
                format_id, extension, resolution = match.groups()
                formats.append((format_id, extension, resolution))
        return formats

    def update_quality_options(self):
        options = ["Best available"] + [f"{res} ({ext})" for _, ext, res in self.available_formats]
        self.quality_combobox['values'] = options
        self.quality_combobox.set("Best available")

    def on_quality_selected(self, event):
        selected = self.quality_combobox.get()
        if selected != "Best available":
            index = self.quality_combobox.current() - 1
            format_id = self.available_formats[index][0]
            self.show_info(f"Selected format ID: {format_id}")

    def download(self):
        url = self.url_entry.get().strip()
        if not self.is_valid_youtube_url(url):
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
            format_id = self.available_formats[index][0]

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

    def build_yt_dlp_command(self, options: DownloadOptions) -> list:
        command = [
            'yt-dlp',
            '-f', options.format,
            '-o', options.filename,
            '--newline',
        ]
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
                    break
                self.parse_output(line)

            if not self.stop_download.is_set():
                self.on_download_complete(command[-1])
        except Exception as e:
            logging.error(f"Error during download process: {str(e)}")
            self.show_error(f"Download failed: {str(e)}")

    def parse_output(self, line):
        if '[download]' in line:
            match = re.search(r'(\d+\.\d+)%.*ETA (\d+:\d+)', line)
            if match:
                percent, eta = float(match.group(1)), match.group(2)
                self.update_progress(percent, eta)

    def get_filename(self):
        user_filename = self.filename_entry.get().strip()
        if user_filename and user_filename != "Enter custom filename (optional)":
            if not user_filename.lower().endswith('.mp4'):
                user_filename += '.mp4'
            return os.path.join(self.download_location, user_filename)
        return os.path.join(self.download_location, '%(title)s.%(ext)s')

    def update_progress(self, percent: float, eta: str):
        self.progress['value'] = percent
        self.progress_label.config(text=f"Progress: {percent:.1f}% (ETA: {eta})")
        self.master.update_idletasks()

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
        self.open_folder_button.pack_forget()

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
