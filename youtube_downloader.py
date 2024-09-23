import os
import sys
import re
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, messagebox
import subprocess
import requests

# Configuration
CONFIG_FILE = 'config.json'
DEFAULT_CONFIG = {
    'output_path': str(Path.home() / 'Downloads'),
    'quality': 'Best available',
    'download_captions': False,
    'dark_mode': False
}

class YouTubeDownloader:
    def __init__(self, master):
        self.master = master
        self.master.title("YouTube Downloader")
        self.master.geometry("700x600")
        
        self.config = self.load_config()
        self.setup_ui()
        self.logger = self.setup_logger()

    def load_config(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return DEFAULT_CONFIG

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f)

    def setup_ui(self):
        self.style = ttk.Style()
        self.apply_theme()

        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        # URL input
        ttk.Label(main_frame, text="YouTube URL:").grid(column=0, row=0, sticky=tk.W, pady=5)
        self.url_entry = ttk.Entry(main_frame, width=60)
        self.url_entry.grid(column=1, row=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # Output path
        ttk.Label(main_frame, text="Output Path:").grid(column=0, row=1, sticky=tk.W, pady=5)
        self.output_path_entry = ttk.Entry(main_frame, width=50)
        self.output_path_entry.grid(column=1, row=1, sticky=(tk.W, tk.E), pady=5)
        self.output_path_entry.insert(0, self.config['output_path'])
        ttk.Button(main_frame, text="Browse", command=self.browse_output_path).grid(column=2, row=1, sticky=tk.W, pady=5)

        # Quality selection
        ttk.Label(main_frame, text="Quality:").grid(column=0, row=2, sticky=tk.W, pady=5)
        self.quality_combobox = ttk.Combobox(main_frame, values=["Best available", "1080p", "720p", "480p", "360p"], state="readonly")
        self.quality_combobox.set(self.config['quality'])
        self.quality_combobox.grid(column=1, row=2, sticky=(tk.W, tk.E), pady=5)

        # Caption checkbox
        self.caption_var = tk.BooleanVar(value=self.config['download_captions'])
        ttk.Checkbutton(main_frame, text="Download captions", variable=self.caption_var).grid(column=0, row=3, columnspan=2, sticky=tk.W, pady=5)

        # Download button
        ttk.Button(main_frame, text="Download", command=self.start_download).grid(column=0, row=4, columnspan=3, pady=10)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(column=0, row=5, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        # Log area
        self.text_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, width=80, height=20)
        self.text_area.grid(column=0, row=6, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.master, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(column=0, row=1, sticky=(tk.W, tk.E))

        # Menu
        self.create_menu()

        # Make the frame expandable
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)

    def create_menu(self):
        menu_bar = tk.Menu(self.master)
        self.master.config(menu=menu_bar)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Check for Updates", command=self.check_for_updates)
        file_menu.add_command(label="Toggle Dark Mode", command=self.toggle_dark_mode)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.master.quit)

    def apply_theme(self):
        if self.config['dark_mode']:
            self.style.theme_use('clam')
            self.style.configure('.', background='#2E2E2E', foreground='white')
            self.style.configure('TEntry', fieldbackground='#3E3E3E', foreground='white')
            self.style.map('TCombobox', fieldbackground=[('readonly', '#3E3E3E')])
            self.style.map('TCombobox', selectbackground=[('readonly', '#3E3E3E')])
            self.style.map('TCombobox', selectforeground=[('readonly', 'white')])
        else:
            self.style.theme_use('clam')
            self.style.configure('.', background='#F0F0F0', foreground='black')
            self.style.configure('TEntry', fieldbackground='white', foreground='black')
            self.style.map('TCombobox', fieldbackground=[('readonly', 'white')])
            self.style.map('TCombobox', selectbackground=[('readonly', 'white')])
            self.style.map('TCombobox', selectforeground=[('readonly', 'black')])

    def toggle_dark_mode(self):
        self.config['dark_mode'] = not self.config['dark_mode']
        self.apply_theme()
        self.save_config()

    def setup_logger(self):
        logger = logging.getLogger('youtube_downloader')
        logger.setLevel(logging.INFO)

        log_dir = Path(__file__).parent / 'logs'
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f'download_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        text_area_handler = TextAreaHandler(self.text_area)
        text_area_handler.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        text_area_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.addHandler(text_area_handler)

        return logger

    def browse_output_path(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_path_entry.delete(0, tk.END)
            self.output_path_entry.insert(0, folder_selected)
            self.config['output_path'] = folder_selected
            self.save_config()

    def validate_url(self, url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and 'youtube.com' in result.netloc
        except ValueError:
            return False

    def start_download(self):
        url = self.url_entry.get().strip()
        output_path = self.output_path_entry.get().strip()
        quality = self.quality_combobox.get()
        download_captions = self.caption_var.get()

        if not self.validate_url(url):
            messagebox.showerror("Error", "Please enter a valid YouTube URL.")
            return

        if not output_path:
            output_path = self.config['output_path']

        self.text_area.delete('1.0', tk.END)
        self.progress_var.set(0)
        
        threading.Thread(target=self.download_youtube_video, 
                         args=(url, output_path, quality, download_captions), 
                         daemon=True).start()

    def download_youtube_video(self, url, output_path, quality, download_captions, retry_count=3):
        quality_options = {
            "1080p": "1920x1080",
            "720p": "1280x720",
            "480p": "854x480",
            "360p": "640x360",
            "Best available": "bestvideo+bestaudio/best"
        }

        for attempt in range(retry_count):
            try:
                if quality == "Best available":
                    format_id, container, width, height = self.get_best_format(url)
                    format_spec = format_id
                    quality_label = f"{height}p" if height else "best"
                else:
                    resolution = quality_options[quality]
                    format_spec = f'bestvideo[height<={resolution.split("x")[1]}]+bestaudio/best'
                    quality_label = quality

                filename = f'%(title)s_[{quality_label}].%(ext)s'
                full_path = os.path.join(output_path, filename)

                yt_dlp_command = [
                    'yt-dlp',
                    '-f', format_spec,
                    '-o', full_path,
                    '--embed-metadata',
                    '--embed-thumbnail',
                    url
                ]

                if download_captions:
                    yt_dlp_command.extend(['--write-auto-sub', '--sub-lang', 'en'])

                self.logger.info(f"Running yt-dlp command: {' '.join(yt_dlp_command)}")
                
                process = subprocess.Popen(yt_dlp_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)
                
                for line in process.stdout:
                    self.logger.info(line.strip())
                    if 'download' in line.lower():
                        match = re.search(r'(\d+\.\d+)%', line)
                        if match:
                            progress = float(match.group(1))
                            self.progress_var.set(progress)

                process.wait()

                if process.returncode == 0:
                    self.logger.info("Download completed successfully!")
                    self.progress_var.set(100)
                    self.status_var.set("Download completed successfully!")
                    return True
                else:
                    self.logger.error(f"Download failed with return code {process.returncode}")
                    if attempt < retry_count - 1:
                        self.logger.info(f"Retrying... (Attempt {attempt + 2}/{retry_count})")
                    else:
                        self.logger.error("Max retry attempts reached. Download failed.")
                        self.status_var.set("Download failed. Check logs for details.")
                        return False

            except Exception as e:
                self.logger.error(f"An error occurred: {str(e)}")
                self.logger.error(f"Error type: {type(e).__name__}")
                self.logger.error(f"Python version: {sys.version}")
                self.logger.error("Detailed traceback:", exc_info=True)
                if attempt < retry_count - 1:
                    self.logger.info(f"Retrying... (Attempt {attempt + 2}/{retry_count})")
                else:
                    self.logger.error("Max retry attempts reached. Download failed.")
                    self.status_var.set("Download failed. Check logs for details.")
                    return False

        return False

    def get_best_format(self, url):
        try:
            command = ['yt-dlp', '-F', url]
            result = subprocess.run(command, capture_output=True, text=True)
            output = result.stdout

            best_format = re.search(r'(\d+)\s+(\w+)\s+(\d+x\d+)\s+.*best', output)
            if best_format:
                format_id = best_format.group(1)
                container = best_format.group(2)
                resolution = best_format.group(3)
                width, height = map(int, resolution.split('x'))
                return format_id, container, width, height

            self.logger.warning("Couldn't determine best format. Defaulting to 'best'.")
            return 'best', 'mp4', None, None
        except Exception as e:
            self.logger.error(f"Error determining best format: {str(e)}")
            return 'best', 'mp4', None, None

    def check_for_updates(self):
        try:
            result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
            current_version = result.stdout.strip()
            
            response = requests.get('https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest', timeout=10)
            response.raise_for_status()
            latest_version = response.json()['tag_name']
            
            if current_version != latest_version:
                messagebox.showinfo("Update Available", f"A new version of yt-dlp is available.\nCurrent: {current_version}\nLatest: {latest_version}")
            else:
                messagebox.showinfo("Up to Date", "You are using the latest version of yt-dlp.")
        except requests.RequestException as e:
            messagebox.showerror("Error", f"Failed to check for updates: {str(e)}")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to get current yt-dlp version: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")

class TextAreaHandler(logging.Handler):
    def __init__(self, text_area):
        super().__init__()
        self.text_area = text_area

    def emit(self, record):
        msg = self.format(record)
        self.text_area.insert(tk.END, msg + "\n")
        self.text_area.see(tk.END)

def main():
    root = tk.Tk()
    YouTubeDownloader(root)
    root.mainloop()

if __name__ == "__main__":
    main()
