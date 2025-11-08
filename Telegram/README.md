# 🤖 Smart Pole Telegram Bot - Screen Control System

A comprehensive Telegram bot for controlling Raspberry Pi display settings including screen orientation, resolution, and configuration management with multi-environment support.

## 📋 Table of Contents

1. [Features](#-features)
2. [Installation](#-installation)
3. [Configuration](#-configuration)
4. [Commands](#-commands)
5. [Screen Control Functionality](#-screen-control-functionality)
6. [Environment Support](#-environment-support)
7. [Debug Information](#-debug-information)
8. [Troubleshooting](#-troubleshooting)
9. [API Reference](#-api-reference)

---

## 🚀 Features

- **Screen Orientation Control**: Rotate display (0°, 90°, 180°, 270°)
- **Resolution Management**: Change display resolution with available modes
- **Multi-Environment Support**: Works with Wayland, X11, and headless systems
- **Real-time Status**: Check current display configuration
- **Debug Logging**: Comprehensive error tracking and method detection
- **Fallback System**: Automatic method selection based on environment
- **Telegram Integration**: Easy-to-use inline keyboard interface

---

## 📦 Installation

### Prerequisites

```bash
sudo apt update
sudo apt install python3 python3-pip wlr-randr
```

### Python Dependencies

```bash
pip3 install -r requirements.txt
```

**requirements.txt:**
```
pyTelegramBotAPI==4.14.0
requests>=2.25.1
```

### Clone Repository

```bash
git clone <repository-url>
cd Smart-Pole/Telegram
```

---

## ⚙️ Configuration

### 1. Telegram Bot Setup

1. Create a new bot with [@BotFather](https://t.me/BotFather)
2. Get your bot token
3. Update `telegramBot.py` with your bot token:

```python
bot = telebot.TeleBot("YOUR_BOT_TOKEN_HERE")
```

### 2. System Service (Optional)

Create a systemd service for automatic startup:

```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

```ini
[Unit]
Description=Smart Pole Telegram Bot
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Smart-Pole/Telegram
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
ExecStart=/usr/bin/python3 /home/pi/Smart-Pole/Telegram/telegramBot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable telegram-bot.service
sudo systemctl start telegram-bot.service
```

---

## 📱 Commands

### Basic Commands

- `/start` - Initialize bot and show welcome message
- `/help` - Display available commands
- `/screen` - Open screen control interface

### Screen Control Interface

When you use `/screen`, you'll get an inline keyboard with:

- **Orientation Options**: Normal, 90°, 180°, 270°
- **Resolution Options**: All available display modes
- **Status**: Check current display configuration

---

## 🖥️ Screen Control Functionality

### Supported Display Methods

The bot automatically detects and uses the best available method:

1. **wlr-randr** (Wayland) - Primary method
2. **xrandr** (X11) - Secondary method  
3. **RPi config.txt + fbcon** - Fallback for headless systems

### Available Orientations

- **Normal** (0°) - Default landscape orientation
- **90°** - Portrait (rotated right)
- **180°** - Inverted landscape
- **270°** - Portrait (rotated left)

### Resolution Support

The bot dynamically detects available resolutions from your display:

Example supported resolutions:
- 1024x600 @ 59.82Hz
- 1280x720 @ 60.00Hz  
- 1920x1080 @ 60.00Hz
- Custom resolutions via config.txt

---

## 🔧 Environment Support

### Wayland Environment (Primary)

Uses `wlr-randr` for display control:

```bash
# Check current configuration
wlr-randr

# Change orientation
wlr-randr --output HDMI-A-1 --transform 90

# Change resolution
wlr-randr --output HDMI-A-1 --mode 1920x1080
```

### X11 Environment (Secondary)

Uses `xrandr` when available:

```bash
# Check displays
xrandr

# Rotate display
xrandr --output HDMI-1 --rotate left

# Change resolution
xrandr --output HDMI-1 --mode 1920x1080
```

### Headless/Fallback Mode

Uses Raspberry Pi configuration files:

```bash
# Modify /boot/firmware/config.txt
display_rotate=1  # 90 degrees
hdmi_group=2
hdmi_mode=82      # 1920x1080 60Hz

# Apply via framebuffer
echo 1 > /sys/class/graphics/fbcon/rotate_all
```

---

## 🐛 Debug Information

### Debug Output Examples

The bot provides comprehensive debug logging:

```
DEBUG: Environment check - DISPLAY: :0
DEBUG: Environment check - XAUTHORITY: /home/pi/.Xauthority
DEBUG: wlr-randr available: True
DEBUG: Using wlr-randr method for display control
DEBUG: Executing: wlr-randr --output HDMI-A-1 --transform 90
DEBUG: Command output: <command result>
DEBUG: Display change successful
```

### Debug Commands

Check if methods are available:
```bash
# Check wlr-randr
which wlr-randr

# Check xrandr
which xrandr

# Check environment
echo $DISPLAY
echo $XAUTHORITY
```

---

## 🔍 Troubleshooting

### Common Issues

#### 1. "wlr-randr not found" or Installation Issues

If you get dpkg errors during installation:
```bash
# Fix broken packages first
sudo dpkg --configure -a
sudo apt update

# Then install wlr-randr
sudo apt install wlr-randr
```

If you still get dependency errors:
```bash
sudo apt --fix-broken install
sudo apt clean
sudo apt update
sudo apt upgrade -y
sudo apt install wlr-randr
```

Verify installation:
```bash
wlr-randr
```

Expected output:
```
XWAYLAND0 "Some Display" 600x1024+0+0
  Modes:
    1024x600 (preferred)
    800x600
    640x480
    ...
```

#### 2. "xrandr: cannot find display"
Check environment variables:
```bash
export DISPLAY=:0
export XAUTHORITY=/home/pi/.Xauthority
```

#### 3. "Changes not applying"
The bot uses fallback methods automatically. Check debug output for method selection.

#### 4. Bot not responding
Check bot token and network connectivity:
```bash
# Test bot
curl -X GET "https://api.telegram.org/bot<TOKEN>/getMe"
```

### Detecting Available Resolutions Programmatically

You can detect available resolutions using Python:

```python
import subprocess

# Method 1: Using xrandr (works on Wayland via XWAYLAND)
try:
    output = subprocess.check_output("xrandr", shell=True).decode()
    print("Available resolutions:")
    print(output)
except:
    print("xrandr not available")

# Method 2: Using wlr-randr (Wayland native)
try:
    output = subprocess.check_output("wlr-randr", shell=True).decode()
    print("Display info:")
    print(output)
except:
    print("wlr-randr not available")
```

Example xrandr output on Wayland:
```
screen 0: minimum 16 x 16, current 600 x 1024, maximum 32767 x 32767 
XWAYLAND0 connected 600x1024+0+0 left (normal left inverted right x axis y axis) 150mm x 100mm
   1024x600      59.55*+
   800x600       59.47  
   640x480       59.38  
   320x240       59.52  
   720x480       59.71  
   640x400       59.20  
   320x200       58.96  
   1024x576      59.58  
   864x486       59.45  
   720x400       59.55  
   640x350       58.91
```

### Method Priority

The bot follows this priority order:
1. **wlr-randr** (if available and working)
2. **xrandr** (if DISPLAY available)
3. **RPi config.txt** (fallback method)

---

## 📖 API Reference

### Core Functions

#### `screen_keyboard()`
Creates inline keyboard for screen controls.

**Returns:** `InlineKeyboardMarkup`

#### `change_display_settings(orientation, resolution=None)`
Main function to change display settings with automatic method detection.

**Parameters:**
- `orientation` (str): 'normal', '90', '180', '270'
- `resolution` (str, optional): Resolution in format 'WIDTHxHEIGHT'

**Returns:** `bool` - Success status

#### `get_display_info()`
Retrieves current display configuration using wlr-randr.

**Returns:** `str` - Formatted display information

#### `resolution_keyboard()`
Generates keyboard with available resolution options.

**Returns:** `InlineKeyboardMarkup`

### Environment Detection

```python
# Check wlr-randr availability
wlr_available = shutil.which('wlr-randr') is not None

# Check X11 environment  
display_available = os.environ.get('DISPLAY') is not None
xauth_available = os.environ.get('XAUTHORITY') is not None
```

### Command Examples

```python
# Change orientation to 90 degrees
change_display_settings('90')

# Change resolution and orientation
change_display_settings('normal', '1920x1080')

# Get current status
status = get_display_info()
```

### Manual Display Control

For direct control outside the bot, you can use these methods:

#### Method 1: wlr-randr (Recommended for Wayland)

```bash
# Check current display configuration
wlr-randr

# Change resolution instantly
wlr-randr --output XWAYLAND0 --mode 1024x600

# Rotate screen
wlr-randr --output XWAYLAND0 --transform 90

# Available transform options:
# normal, 90, 180, 270, flipped, flipped-90, flipped-180, flipped-270

# Reset to normal
wlr-randr --output XWAYLAND0 --transform normal
```

#### Method 2: Python Control Script

Create a simple display control script:

```python
import os

def set_display(resolution="1024x600", rotation="normal"):
    """
    Control display resolution and rotation
    
    Args:
        resolution (str): Resolution in format "WIDTHxHEIGHT" (e.g., "1024x600")
        rotation (str): Transform option ("normal", "90", "180", "270")
    """
    # Change resolution
    os.system(f"wlr-randr --output XWAYLAND0 --mode {resolution}")
    # Change rotation
    os.system(f"wlr-randr --output XWAYLAND0 --transform {rotation}")
    print(f"Display set to {resolution} with {rotation} rotation")

# Example usage
set_display("1024x600", "90")
set_display("800x600", "normal")
set_display("640x480", "180")
```

Save as `display_control.py` and run:
```bash
python3 display_control.py
```

#### Method 3: Advanced Resolution Detection

```python
import subprocess
import re

def get_available_resolutions():
    """Get all available resolutions from xrandr output"""
    try:
        output = subprocess.check_output("xrandr", shell=True).decode()
        # Extract resolution lines (contain x and numbers)
        resolutions = re.findall(r'(\d+x\d+)\s+[\d.]+', output)
        return list(set(resolutions))  # Remove duplicates
    except:
        return []

def get_current_resolution():
    """Get current active resolution"""
    try:
        output = subprocess.check_output("xrandr", shell=True).decode()
        # Look for line with * (current) or + (preferred)
        current = re.search(r'(\d+x\d+).*\*', output)
        return current.group(1) if current else None
    except:
        return None

# Example usage
available = get_available_resolutions()
current = get_current_resolution()

print(f"Available resolutions: {available}")
print(f"Current resolution: {current}")
```

---

## 📊 System Status

### Hardware Requirements
- Raspberry Pi 3/4/5
- HDMI display connection
- Network connectivity for Telegram

### Software Requirements
- Raspberry Pi OS (Bookworm recommended)
- Python 3.7+
- wlr-randr (for Wayland)
- xrandr (for X11)

### Tested Environments
- ✅ Raspberry Pi OS Bookworm (Wayland)
- ✅ Raspberry Pi OS Bullseye (X11)  
- ✅ Headless systems with SSH
- ✅ Remote VNC connections

---

## 📝 Example Usage

### Complete Workflow

1. **Start the bot:**
   ```bash
   python3 telegramBot.py
   ```

2. **Send `/screen` command in Telegram**

3. **Select orientation (e.g., 90°)**

4. **Choose resolution (e.g., 1920x1080)**

5. **Check status** to verify changes

### Manual Testing

```bash
# Test wlr-randr method
wlr-randr --output HDMI-A-1 --transform 90

# Test xrandr method  
xrandr --output HDMI-1 --rotate left

# Test config.txt method
echo "display_rotate=1" >> /boot/firmware/config.txt
sudo reboot
```

---

**Author:** Smart Pole Development Team  
**Version:** 2.0  
**Last Updated:** November 2025  
**Tested on:** Raspberry Pi 4 (Bookworm/Wayland, Bullseye/X11)  
**Dependencies:** wlr-randr, xrandr, pyTelegramBotAPI

---
