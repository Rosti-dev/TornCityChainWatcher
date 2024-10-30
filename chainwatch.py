import tkinter as tk
from tkinter import ttk, filedialog
from tkinter import messagebox
from datetime import datetime
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
    def __init__(self, root):  # Ensure `self` is the first parameter
        self.root = root
        self.root.title("Chain Watcher App")
        
        self.api_interval = tk.IntVar(value=5)  # Default API call interval in seconds
        self.panic_interval = tk.IntVar(value=2)  # API call interval while in panic mode
        self.alarm_trigger_seconds = tk.IntVar(value=60)  # Alarm trigger threshold in seconds
        self.pre_alarm_trigger_seconds = tk.IntVar(value=90)  # Pre-Alarm trigger threshold in seconds
        self.alarm_volume = tk.DoubleVar(value=0.5)  # Volume control for alarm
        self.alarm_sound_choice = tk.StringVar(value=ALARM_SOUNDS[0])
        self.pre_alarm_sound_choice = tk.StringVar(value=PRE_ALARM_SOUNDS[0])
        self.api_key = tk.StringVar()  # API Key (no default value set in script)
        self.prevent_sleep = tk.BooleanVar(value=False)  # Prevent PC from going to sleep
        self.keep_on_top = tk.BooleanVar(value=False)  # Keep window on top of all others
        self.backup_timer_enabled = tk.BooleanVar(value=False)  # Enable or disable backup timer
        self.remaining_seconds = 0
        self.backup_remaining_seconds = 0  # Initialize backup timer countdown
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

        self.last_known_remaining_seconds = 0
        self.last_known_backup_remaining_seconds = 0


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
                    self.backup_timer_enabled.set(settings.get("backup_timer_enabled", False))
                    self.update_keep_on_top()


    def ensure_alarm_files_exist(self):
         # Check if either of the required sound files is missing
         missing_files = [sound for sound, url in ALARM_SOUNDS_URLS.items() if not os.path.exists(sound)]

         if missing_files:
            # Prompt the user to confirm the download
            response = messagebox.askyesno("Missing Sound Files",
                                           "No sound files have been found, would you like to download them? (Two files in total)")
            if response:
                # User chose to download the missing files
                for sound, url in ALARM_SOUNDS_URLS.items():
                    if not os.path.exists(sound):
                        try:
                            print(f"Downloading {sound}...")
                            urllib.request.urlretrieve(url, sound)
                            print(f"Downloaded {sound} successfully.")
                        except Exception as e:
                            print(f"Failed to download {sound}: {e}", file=sys.stderr)
                            messagebox.showerror("Error", f"Failed to download {sound}: {e}")
            else:
                # User chose not to download the files
                print("User opted not to download the missing sound files.")

    def setup_gui(self):
        # Time left label
        self.time_label = tk.Label(self.root, text="T-: 00:00", font=("Helvetica", 60))
        self.time_label.pack(pady=10)
        
        # Diagnostics box for backup timer
        self.diagnostics_box = tk.Label(self.root, text="Backup Timer: Disabled", font=("Helvetica", 12))
        self.diagnostics_box.pack(pady=5)
        
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
        
        # Backup Timer checkbox
        backup_timer_frame = tk.Frame(self.root)
        backup_timer_frame.pack(pady=5)
        backup_timer_checkbox = ttk.Checkbutton(backup_timer_frame, text="Enable Backup Timer", variable=self.backup_timer_enabled, command=self.toggle_backup_timer)
        backup_timer_checkbox.pack(side=tk.LEFT)
        
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

        # Add a debug checkbox to the GUI
        self.debug_mode = tk.BooleanVar(value=False)  # Debug mode toggle
        debug_checkbox = ttk.Checkbutton(self.root, text="Debug", variable=self.debug_mode)
        debug_checkbox.pack(pady=5)

    def toggle_backup_timer(self):
        if self.backup_timer_enabled.get():
            self.diagnostics_box.config(text="Backup Timer: Enabled")
        else:
            self.diagnostics_box.config(text="Backup Timer: Disabled")
    
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
            # Start the API polling loop in one thread
            threading.Thread(target=self.watch_chain, daemon=True).start()
            # Start the continuous timer countdown loop in another thread
            threading.Thread(target=self.update_timer_loop, daemon=True).start()

    def stop_watching(self):
        self.running = False
        self.panic_mode = False  # Reset panic mode on stop
        self.save_settings()
        pygame.mixer.music.stop()

    def update_keep_on_top(self):
        self.root.attributes('-topmost', self.keep_on_top.get())

    def flash_failure(self):
        # Flash between yellow and red to indicate API failure
        for _ in range(3):  # Flash three times for visual feedback
            self.root.config(bg="yellow")
            self.root.update()
            time.sleep(0.2)
            self.root.config(bg="red")
            self.root.update()
            time.sleep(0.2)




    def watch_chain(self):
        api_failed = False  # Track API failure

        while self.running:
            # Determine interval based on API status
            interval = self.panic_interval.get() if api_failed else self.api_interval.get()

            # Prevent sleep if specified
            if self.prevent_sleep.get():
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)
            else:
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)

            # Debug log for API attempt
            if self.debug_mode.get():
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{timestamp}] Attempting API call...")

            try:
                # Make the API call
                response = requests.get(f"https://api.torn.com/faction/?selections=chain&key={self.api_key.get()}&comment=PyChainwatcher")
                response.raise_for_status()
                data = response.json()
                
                # Update `chain_end_time` from the API, applying the 1-second offset
                self.chain_end_time = data["chain"]["end"] - 1  # Apply 1-second offset

                # Set the backup timer timeout if enabled
                if self.backup_timer_enabled.get():
                    self.backup_remaining_seconds = data["chain"]["timeout"]

                # Log success in debug mode
                if self.debug_mode.get():
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{timestamp}] API call successful: Chain end time updated.")

                # Reset failure flag
                api_failed = False
                self.root.config(bg="SystemButtonFace")

                # Enter panic mode if remaining time is below alarm threshold
                self.panic_mode = (self.chain_end_time - int(time.time())) <= self.alarm_trigger_seconds.get()

            except Exception as e:
                # Log error with timestamp, enter panic mode, and flash the screen
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{timestamp}] API request failed: {e}", file=sys.stderr)
                api_failed = True  # Set API failure flag
                self.flash_failure()  # Flash the screen for API failure

            # Wait the interval before the next API call
            time.sleep(interval)
                    

    def update_timer_loop(self):
        while self.running:
            # Calculate main remaining time based on `chain_end_time`
            self.remaining_seconds = max(0, self.chain_end_time - int(time.time()))

            # Update main timer display with "T-:" prefix
            if self.remaining_seconds <= 0:
                self.time_label.config(text="T-: 00:00")
            else:
                minutes, seconds = divmod(self.remaining_seconds, 60)
                self.time_label.config(text=f"T-: {minutes:02}:{seconds:02}")
            
            # Backup timer display in diagnostics box
            if self.backup_timer_enabled.get():
                # Decrement backup timer if enabled
                self.backup_remaining_seconds = max(0, self.backup_remaining_seconds - 1)
                backup_minutes, backup_seconds = divmod(self.backup_remaining_seconds, 60)
                self.diagnostics_box.config(text=f"Backup Timer: {backup_minutes:02}:{backup_seconds:02}")
            else:
                self.diagnostics_box.config(text="Backup Timer: Disabled")
            
            # Handle alarm triggers and color changes for main timer
            if self.remaining_seconds <= self.alarm_trigger_seconds.get():
                self.root.config(bg="red")
                self.play_alarm(loop=True)
            elif self.remaining_seconds <= self.pre_alarm_trigger_seconds.get():
                self.root.config(bg="yellow")
                self.play_pre_alarm(loop=True)
            else:
                self.root.config(bg="SystemButtonFace")
                self.stop_pre_alarm()

            # Wait exactly one second before updating the timer again
            time.sleep(1)




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
            "keep_on_top": self.keep_on_top.get(),
            "backup_timer_enabled": self.backup_timer_enabled.get()
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
                self.backup_timer_enabled.set(settings.get("backup_timer_enabled", False))
                self.update_keep_on_top()

# Main Application
if __name__ == "__main__":
    root = tk.Tk()
    app = ChainWatcherApp(root)
    root.mainloop()
