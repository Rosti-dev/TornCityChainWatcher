# Chain Watcher App

The **Chain Watcher App** is a GUI-based Python application that monitors a chain in a Torn faction, issuing alarm notifications when a set time threshold is reached. Users can customize alarm sounds, API intervals, pre-alarm intervals, and other settings.

## Features

- **Configurable Alarm and Pre-Alarm**: Set your own alarm and pre-alarm sounds and timing thresholds.
- **Panic Mode**: Increase API check frequency when the chain is close to ending.
- **GUI Controls**: Adjust alarm intervals, sound volumes, and more within an intuitive GUI.
- **Prevents System Sleep**: Optionally keeps your computer awake while the app is running.
- **Custom API Key Support**: Easily set your API key for accessing the Torn API.

## Installation

### Prerequisites

Ensure you have Python installed (version 3.7+ recommended). 

Install Dependencies
```
pip install -r requirements.txt
```

### Clone the Repository

```bash
git clone https://github.com/yourusername/chain-watcher.git
cd chain-watcher

