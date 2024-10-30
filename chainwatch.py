import tkinter as tk
from tkinter import ttk, filedialog
from tkinter import messagebox
import time
import threading
import requests
import pygame
import os
import json
import ctypes
import sys
import urllib.request

# Initialize Pygame mixer for alarm sounds
pygame.mixer.init()

# Directory for storing settings and sounds
DATA_FOLDER = "chainwatch_data"
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# Alarm sounds paths (You can add your own paths to sounds here)
ALARM_SOUNDS = [
    os.path.join(DATA_FOLDER, "mixkit-classic-alarm-995.wav"),  # Default alarm sound
    "Search File"
]

PRE_ALARM_SOUNDS = [
    os.path.join(DATA_FOLDER, "mixkit-retro-game-emergency-alarm-1000.wav"),  # Default pre-alarm sound
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
        
        self.api_interval = tk.IntVar(value=5)  # Default API call interval in seconds
        self.panic_interval = tk.IntVar(value=2)  # API call interval while in panic mode
        self.alarm_trigger_seconds = tk.IntVar(value=60)  # Alarm trigger threshold in seconds
        self.pre_alarm_trigger_seconds = tk.IntVar(value=90)  # Pre-Alarm trigger threshold in seconds (updated to 90 seconds)
        self.alarm_volume = tk.DoubleVar(value=0.5)  # Volume control for alarm
        self.alarm_sound_choice = tk.StringVar(value=ALARM_SOUNDS[0])
        self.pre_alarm_sound_choice = tk.StringVar(value=PRE_ALARM_SOUNDS[0])
        self.api_key = tk.StringVar()  # API Key (no default value set in script)
        self.prevent_sleep = tk.BooleanVar(value=False)  # Prevent PC from going to sleep
        self.keep_on_top = tk.BooleanVar(value=False)  # Keep window on top of all others
        
        self.remaining_seconds = 0
        self.chain_end_time = 0
        self.running = False
        self.panic_mode = False  # Track if we are in panic mode
        
        # Load previous settings
        self.load_settings()
        
        # Ensure alarm files are present
        self.ensure_alarm_files_exist()
        
        # GUI Setup
        self.setup_gui()
        
        # Thread for background API calls
        self.thread = None
        
    def ensure_alarm_files_exist(self):
        for sound, url in ALARM_SOUNDS_URLS.items():
            if not os.path.exists(sound):
                try:
                    print(f"Downloading {sound}...")
                    urllib.request.urlretrieve(url, sound)
                    print(f"Downloaded {sound} successfully.")
                except Exception as e:
                    print(f"Failed to download {sound}: {e}", file=sys.stderr)
                    messagebox.showerror("Error", f"Failed to download {sound}: {e}")
        
    def setup_gui(self):
        # Time left label
        self.time_label = tk.Label(self.root, text="Time Left: 00:00", font=("Helvetica", 24))
        self.time_label.pack(pady=10)
        
        # Volume control
        volume_frame = tk.Frame(self.root)
        volume_frame.pack(pady=5)
        tk.Label(volume_frame, text="Volume:").pack(side=tk.LEFT)
        volume_slider = ttk.Scale(volume_frame, from_=0, to=1, orient="horizontal", variable=self.alarm_volume)
        volume_slider.pack(side=tk.LEFT)
        
        # Alarm trigger time field
        trigger_frame = tk.Frame(self.root)
        trigger_frame.pack(pady=5)
        tk.Label(trigger_frame, text="Trigger at seconds left:").pack(side=tk.LEFT)
        trigger_entry = ttk.Entry(trigger_frame, textvariable=self.alarm_trigger_seconds)
        trigger_entry.pack(side=tk.LEFT)
        
        # Pre-Alarm trigger time field
        pre_trigger_frame = tk.Frame(self.root)
        pre_trigger_frame.pack(pady=5)
        tk.Label(pre_trigger_frame, text="Pre-Alarm at seconds left:").pack(side=tk.LEFT)
        pre_trigger_entry = ttk.Entry(pre_trigger_frame, textvariable=self.pre_alarm_trigger_seconds)
        pre_trigger_entry.pack(side=tk.LEFT)
        
        # API interval field
        interval_frame = tk.Frame(self.root)
        interval_frame.pack(pady=5)
        tk.Label(interval_frame, text="API Call Interval (seconds):").pack(side=tk.LEFT)
        interval_entry = ttk.Entry(interval_frame, textvariable=self.api_interval)
        interval_entry.pack(side=tk.LEFT)
        
        # Panic mode API interval field
        panic_interval_frame = tk.Frame(self.root)
        panic_interval_frame.pack(pady=5)
        tk.Label(panic_interval_frame, text="Panic Mode API Interval (seconds):").pack(side=tk.LEFT)
        panic_interval_entry = ttk.Entry(panic_interval_frame, textvariable=self.panic_interval)
        panic_interval_entry.pack(side=tk.LEFT)
        
        # Alarm sound picker
        sound_frame = tk.Frame(self.root)
        sound_frame.pack(pady=5)
        tk.Label(sound_frame, text="Alarm Sound:").pack(side=tk.LEFT)
        sound_picker = ttk.Combobox(sound_frame, textvariable=self.alarm_sound_choice, values=ALARM_SOUNDS)
        sound_picker.pack(side=tk.LEFT)
        sound_picker.bind("<<ComboboxSelected>>", self.select_alarm_file)
        
        # Pre-Alarm sound picker
        pre_alarm_frame = tk.Frame(self.root)
        pre_alarm_frame.pack(pady=5)
        tk.Label(pre_alarm_frame, text="Pre-Alarm Sound:").pack(side=tk.LEFT)
        pre_alarm_picker = ttk.Combobox(pre_alarm_frame, textvariable=self.pre_alarm_sound_choice, values=PRE_ALARM_SOUNDS)
        pre_alarm_picker.pack(side=tk.LEFT)
        pre_alarm_picker.bind("<<ComboboxSelected>>", self.select_pre_alarm_file)
        
        # API Key setting button
        api_key_frame = tk.Frame(self.root)
        api_key_frame.pack(pady=5)
        api_key_button = ttk.Button(api_key_frame, text="Set API Key", command=self.open_api_key_window)
        api_key_button.pack(side=tk.LEFT)
        
        # Prevent Sleep checkbox
        prevent_sleep_frame = tk.Frame(self.root)
        prevent_sleep_frame.pack(pady=5)
        prevent_sleep_checkbox = ttk.Checkbutton(prevent_sleep_frame, text="Prevent Sleep", variable=self.prevent_sleep)
        prevent_sleep_checkbox.pack(side=tk.LEFT)
        
        # Keep on Top checkbox
        keep_on_top_frame = tk.Frame(self.root)
        keep_on_top_frame.pack(pady=5)
        keep_on_top_checkbox = ttk.Checkbutton(keep_on_top_frame, text="Keep On Top", variable=self.keep_on_top, command=self.update_keep_on_top)
        keep_on_top_checkbox.pack(side=tk.LEFT)
        
        # Start and Stop buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        start_button = ttk.Button(button_frame, text="Start", command=self.start_watching)
        start_button.pack(side=tk.LEFT, padx=5)
        stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_watching)
        stop_button.pack(side=tk.LEFT, padx=5)

    def open_api_key_window(self):
        # New window for setting the API Key
        api_key_window = tk.Toplevel(self.root)
        api_key_window.title("Set API Key")
        api_key_window.geometry("300x100")
        
        tk.Label(api_key_window, text="API Key:").pack(pady=10)
        api_key_entry = ttk.Entry(api_key_window, textvariable=self.api_key, width=40)
        api_key_entry.pack(pady=5)
        save_button = ttk.Button(api_key_window, text="Save", command=api_key_window.destroy)
        save_button.pack(pady=5)
        
    def select_alarm_file(self, event):
        if self.alarm_sound_choice.get() == "Search File":
            file_path = filedialog.askopenfilename()
            if file_path:
                self.alarm_sound_choice.set(file_path)

    def select_pre_alarm_file(self, event):
        if self.pre_alarm_sound_choice.get() == "Search File":
            file_path = filedialog.askopenfilename()
            if file_path:
                self.pre_alarm_sound_choice.set(file_path)
        
    def start_watching(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.watch_chain)
            self.thread.daemon = True
            self.thread.start()

    def stop_watching(self):
        self.running = False
        self.panic_mode = False  # Reset panic mode on stop
        self.save_settings()
        pygame.mixer.music.stop()

    def update_keep_on_top(self):
        self.root.attributes('-topmost', self.keep_on_top.get())

    def flash_window(self):
        for _ in range(3):
            self.root.config(bg="yellow")
            self.root.update()
            time.sleep(0.1)
            self.root.config(bg="SystemButtonFace")
            self.root.update()
            time.sleep(0.1)

    def watch_chain(self):
        while self.running:
            if self.prevent_sleep.get():
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)
            else:
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            
            try:
                # Call the API
                response = requests.get(f"https://api.torn.com/faction/?selections=chain&key={self.api_key.get()}&comment=PyChainwatcher")
                response.raise_for_status()
                data = response.json()
                
                self.chain_end_time = data["chain"]["end"]
                self.remaining_seconds = max(0, self.chain_end_time - int(time.time()))
                
                # Enter panic mode if needed
                self.panic_mode = self.remaining_seconds <= self.alarm_trigger_seconds.get()
                
                # Update the GUI clock every second until the next API call
                interval = self.panic_interval.get() if self.panic_mode else self.api_interval.get()
                for _ in range(interval):
                    if not self.running:
                        break
                    self.update_clock()
                    time.sleep(1)
            except Exception as e:
                print(f"API request failed: {e}", file=sys.stderr)
                self.flash_window()

    def update_clock(self):
        if self.remaining_seconds <= 0:
            self.time_label.config(text="Time Left: 00:00")
        else:
            minutes, seconds = divmod(self.remaining_seconds, 60)
            self.time_label.config(text=f"Time Left: {minutes:02}:{seconds:02}")
            
            if self.remaining_seconds <= self.alarm_trigger_seconds.get():
                self.root.config(bg="red")
                self.play_alarm(loop=True)
            elif self.remaining_seconds <= self.pre_alarm_trigger_seconds.get():
                self.root.config(bg="yellow")
                self.play_pre_alarm(loop=True)
            else:
                self.root.config(bg="SystemButtonFace")
                self.stop_pre_alarm()
        
        self.remaining_seconds -= 1

    def play_alarm(self, loop=False):
        pygame.mixer.music.load(self.alarm_sound_choice.get())
        pygame.mixer.music.set_volume(self.alarm_volume.get())
        if loop:
            pygame.mixer.music.play(-1)  # Loop indefinitely
        else:
            pygame.mixer.music.play()
    
    def play_pre_alarm(self, loop=False):
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.load(self.pre_alarm_sound_choice.get())
            pygame.mixer.music.set_volume(self.alarm_volume.get())
            if loop:
                pygame.mixer.music.play(-1)  # Loop indefinitely
            else:
                pygame.mixer.music.play()
    
    def stop_pre_alarm(self):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()

    def save_settings(self):
        settings = {
            "api_interval": self.api_interval.get(),
            "panic_interval": self.panic_interval.get(),
            "alarm_trigger_seconds": self.alarm_trigger_seconds.get(),
            "pre_alarm_trigger_seconds": self.pre_alarm_trigger_seconds.get(),
            "alarm_volume": self.alarm_volume.get(),
            "alarm_sound_choice": self.alarm_sound_choice.get(),
            "pre_alarm_sound_choice": self.pre_alarm_sound_choice.get(),
            "api_key": self.api_key.get(),
            "prevent_sleep": self.prevent_sleep.get(),
            "keep_on_top": self.keep_on_top.get()
        }
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                self.api_interval.set(settings.get("api_interval", 5))
                self.panic_interval.set(settings.get("panic_interval", 2))
                self.alarm_trigger_seconds.set(settings.get("alarm_trigger_seconds", 90))
                self.pre_alarm_trigger_seconds.set(settings.get("pre_alarm_trigger_seconds", 90))
                self.alarm_volume.set(settings.get("alarm_volume", 0.5))
                self.alarm_sound_choice.set(settings.get("alarm_sound_choice", ALARM_SOUNDS[0]))
                self.pre_alarm_sound_choice.set(settings.get("pre_alarm_sound_choice", PRE_ALARM_SOUNDS[0]))
                self.api_key.set(settings.get("api_key", ""))
                self.prevent_sleep.set(settings.get("prevent_sleep", False))
                self.keep_on_top.set(settings.get("keep_on_top", False))
                self.update_keep_on_top()

# Main Application
if __name__ == "__main__":
    root = tk.Tk()
    app = ChainWatcherApp(root)
    root.mainloop()
