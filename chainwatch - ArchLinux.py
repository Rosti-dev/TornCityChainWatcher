import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import time
import threading
import requests
import pygame
import os
import json
import sys
import urllib.request
import platform
import subprocess

# Initialize Pygame mixer for alarm sounds
pygame.mixer.init()

# Directory for storing settings and sounds
DATA_FOLDER = "chainwatch_data"
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# Alarm sounds paths
ALARM_SOUNDS = [
    os.path.join(DATA_FOLDER, "mixkit-classic-alarm-995.wav"),
    "Search File"
]

PRE_ALARM_SOUNDS = [
    os.path.join(DATA_FOLDER, "mixkit-retro-game-emergency-alarm-1000.wav"),
    "Search File"
]

# URLs for downloading default alarm sounds
ALARM_SOUNDS_URLS = {
    os.path.join(DATA_FOLDER, "mixkit-classic-alarm-995.wav"): "https://assets.mixkit.co/active_storage/sfx/995/995.wav",
    os.path.join(DATA_FOLDER, "mixkit-retro-game-emergency-alarm-1000.wav"): "https://assets.mixkit.co/active_storage/sfx/1000/1000.wav"
}

SETTINGS_FILE = os.path.join(DATA_FOLDER, "chain_watcher_settings.json")

class ChainWatcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chain Watcher App")
        
        # Initialize variables
        self.api_interval = tk.IntVar(value=5)
        self.panic_interval = tk.IntVar(value=2)
        self.alarm_trigger_seconds = tk.IntVar(value=60)
        self.pre_alarm_trigger_seconds = tk.IntVar(value=90)
        self.alarm_volume = tk.DoubleVar(value=0.5)
        self.alarm_sound_choice = tk.StringVar(value=ALARM_SOUNDS[0])
        self.pre_alarm_sound_choice = tk.StringVar(value=PRE_ALARM_SOUNDS[0])
        self.api_key = tk.StringVar()
        self.prevent_sleep = tk.BooleanVar(value=False)
        self.keep_on_top = tk.BooleanVar(value=False)
        self.backup_timer_enabled = tk.BooleanVar(value=False)
        self.running = False
        self.panic_mode = False

        self.caffeinate_process = None

        # Load settings and GUI setup
        self.load_settings()
        self.ensure_alarm_files_exist()
        self.setup_gui()

    def prevent_sleep_mode(self, enable=True):
        if platform.system() == 'Linux':
            if enable:
                self.caffeinate_process = subprocess.Popen(['caffeinate'])
            elif self.caffeinate_process:
                self.caffeinate_process.terminate()

    def setup_gui(self):
        self.time_label = tk.Label(self.root, text="T-: 00:00", font=("Helvetica", 60))
        self.time_label.pack(pady=10)
        self.diagnostics_box = tk.Label(self.root, text="Backup Timer: Disabled", font=("Helvetica", 12))
        self.diagnostics_box.pack(pady=5)
        
        volume_frame = tk.Frame(self.root)
        volume_frame.pack(pady=5)
        tk.Label(volume_frame, text="Volume:").pack(side=tk.LEFT)
        volume_slider = ttk.Scale(volume_frame, from_=0, to=1, orient="horizontal", variable=self.alarm_volume)
        volume_slider.pack(side=tk.LEFT)
        
        trigger_frame = tk.Frame(self.root)
        trigger_frame.pack(pady=5)
        tk.Label(trigger_frame, text="Trigger at seconds left:").pack(side=tk.LEFT)
        trigger_entry = ttk.Entry(trigger_frame, textvariable=self.alarm_trigger_seconds)
        trigger_entry.pack(side=tk.LEFT)
        
        pre_trigger_frame = tk.Frame(self.root)
        pre_trigger_frame.pack(pady=5)
        tk.Label(pre_trigger_frame, text="Pre-Alarm at seconds left:").pack(side=tk.LEFT)
        pre_trigger_entry = ttk.Entry(pre_trigger_frame, textvariable=self.pre_alarm_trigger_seconds)
        pre_trigger_entry.pack(side=tk.LEFT)

        # Additional GUI elements for API Key, Prevent Sleep, etc.
        prevent_sleep_frame = tk.Frame(self.root)
        prevent_sleep_frame.pack(pady=5)
        prevent_sleep_checkbox = ttk.Checkbutton(prevent_sleep_frame, text="Prevent Sleep", variable=self.prevent_sleep)
        prevent_sleep_checkbox.pack(side=tk.LEFT)
        
        keep_on_top_frame = tk.Frame(self.root)
        keep_on_top_frame.pack(pady=5)
        keep_on_top_checkbox = ttk.Checkbutton(keep_on_top_frame, text="Keep On Top", variable=self.keep_on_top, command=self.update_keep_on_top)
        keep_on_top_checkbox.pack(side=tk.LEFT)

    def update_keep_on_top(self):
        self.root.attributes('-topmost', self.keep_on_top.get())

    def watch_chain(self):
        api_failed = False
        while self.running:
            interval = self.panic_interval.get() if api_failed else self.api_interval.get()
            if self.prevent_sleep.get():
                self.prevent_sleep_mode(True)

            try:
                response = requests.get(api_url)
                response.raise_for_status()
                data = response.json()
                self.chain_end_time = data["chain"]["end"] - 1
                api_failed = False
                self.root.config(bg="#F0F0F0")
            except Exception as e:
                print(f"API request failed: {e}", file=sys.stderr)
                api_failed = True
                self.flash_failure()

            time.sleep(interval)

    def flash_failure(self):
        for _ in range(3):
            self.root.config(bg="yellow")
            self.root.update()
            time.sleep(0.2)
            self.root.config(bg="red")
            self.root.update()
            time.sleep(0.2)

    def stop_watching(self):
        self.running = False
        self.prevent_sleep_mode(False)

    # (Other methods, e.g., play_alarm, stop_alarm, load_settings, etc.)

# Main Application
if __name__ == "__main__":
    root = tk.Tk()
    app = ChainWatcherApp(root)
    root.mainloop()
