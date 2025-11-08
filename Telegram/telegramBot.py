import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from gtts import gTTS
import os
import socket
import subprocess
import oneM2Mget
import time
from dotenv import load_dotenv
import shutil

# Load variables from .env file
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing in the .env file.")

bot = telebot.TeleBot(BOT_TOKEN)

# Function to send IP and Wi-Fi info at startup
def send_ip_at_startup():
    try:
        ip_address = get_ip_address()
        wifi_status = check_wifi_connection()
        startup_message = f"Startup Info:\nIP Address: {ip_address}\nWiFi Status: {wifi_status}"
        bot.send_message(chat_id='1137118390', text=startup_message)
    except Exception as e:
        print(f"Failed to send startup message: {str(e)}")

# Function to convert text to speech and play it
def text_to_speech(text, language='en', filename='output.mp3', play=True):
    try:
        tts = gTTS(text=text, lang=language, slow=False)
        tts.save(filename)
        if play and os.system("command -v mpg321") == 0:
            os.system(f"mpg321 {filename}")
        else:
            print("mpg321 not found or playback disabled.")
    except Exception as e:
        print(f"Error generating speech: {str(e)}")

# Define a function to handle the /start command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Hello! Use /play to play predefined text or /playcustom : your text to play.")

# Define a function to handle the /play command (predefined text)
@bot.message_handler(commands=['play'])
def play_audio(message):
    response_data = oneM2Mget.getTemperature()
    con_value = response_data
    predefined_text = f"Welcome to Smart City Living Lab. The current value of CO2 is {con_value[1]}, temperature is {con_value[2]}, and humidity is {con_value[3]}."
    bot.reply_to(message, "Playing predefined text.")
    text_to_speech(predefined_text)

# Define a function to handle the /playcustom command (custom text)
@bot.message_handler(commands=['playcustom'])
def play_custom_audio(message):
    if ':' in message.text:
        custom_text = message.text.split(":", 1)[1].strip()
        if custom_text:
            bot.reply_to(message, f"Playing custom text: {custom_text}")
            text_to_speech(custom_text)
        else:
            bot.reply_to(message, "No custom text provided after /playcustom.")
    else:
        bot.reply_to(message, "Please provide custom text using /playcustom:your text")

# Function to get the IP address
def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address
    except Exception:
        return subprocess.getoutput("hostname -I").strip().split()[0]

# Function to check Wi-Fi connection status
def check_wifi_connection():
    try:
        result = subprocess.run(['iwgetid'], stdout=subprocess.PIPE)
        wifi_info = result.stdout.decode('utf-8').strip()
        return f"Connected to WiFi: {wifi_info}" if wifi_info else "Not connected to any WiFi network"
    except Exception as e:
        return f"Unable to determine WiFi status: {str(e)}"

@bot.message_handler(commands=['ip'])
def send_ip_info(message):
    ip_address = get_ip_address()
    wifi_status = check_wifi_connection()
    bot.reply_to(message, f"IP Address: {ip_address}\nWiFi Status: {wifi_status}")

# Function to manage services
def manage_service(call, service_name, action):
    try:
        subprocess.run(["sudo", "systemctl", action, service_name], check=True)
        bot.send_message(call.message.chat.id, f"Service '{service_name}' {action}ed successfully.")
    except subprocess.CalledProcessError as e:
        bot.send_message(call.message.chat.id, f"Failed to {action} service '{service_name}': {str(e)}")

# Function to check service status
def check_service_status(service_name):
    try:
        result = subprocess.run(["systemctl", "is-active", service_name], capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error checking status: {str(e)}"


# --- Display (orientation/resolution) helpers ---
def get_primary_output():
    """Return the first connected display output name using xrandr."""
    try:
        # Only try xrandr if we have a display environment
        if not os.environ.get("DISPLAY"):
            return None
        x = subprocess.run(["xrandr", "--query"], capture_output=True, text=True, check=True, env=get_x_env())
        for line in x.stdout.splitlines():
            if " connected" in line:
                return line.split()[0]
    except Exception:
        return None


def find_xauthority():
    """Try to locate a valid XAUTHORITY file for the running X server.

    Returns path or None.
    """
    # First check environment
    xa = os.environ.get("XAUTHORITY")
    if xa and os.path.exists(xa):
        return xa

    # Try common home locations
    try:
        for user in os.listdir("/home"):
            candidate = f"/home/{user}/.Xauthority"
            if os.path.exists(candidate):
                return candidate
    except Exception:
        pass

    # Last-resort: look for any .Xauthority file under /run or /var
    possibles = ["/run/user/1000/gdm/Xauthority", "/run/lightdm/root/:0", "/var/run/gdm3/auth-for-1000-db/users/1000"]
    for p in possibles:
        if os.path.exists(p):
            return p

    return None


def get_x_env():
    """Return an environment dict suitable for xrandr calls (DISPLAY and XAUTHORITY).

    Uses current process env as base and sets DISPLAY=:0 if missing.
    """
    env = os.environ.copy()
    if "DISPLAY" not in env or not env.get("DISPLAY"):
        env["DISPLAY"] = os.environ.get("DISPLAY", ":0")
    xa = find_xauthority()
    if xa:
        env["XAUTHORITY"] = xa
    return env


def ensure_mode_available(output, resolution, env=None):
    """Ensure the given resolution/mode is available for the output.

    If not present, try to create it using cvt -> xrandr --newmode/--addmode.
    Returns (True, msg) if mode available or added, (False, err) on failure.
    """
    if not env:
        env = get_x_env()
    try:
        q = subprocess.run(["xrandr", "--query"], capture_output=True, text=True, env=env)
        out = q.stdout
        # Check if resolution already present for any mode line
        if resolution in out:
            return True, "Mode already available"

        # Generate modeline with cvt
        parts = resolution.split('x')
        if len(parts) != 2:
            return False, "Invalid resolution format"
        w, h = parts
        cvt = subprocess.run(["cvt", w, h], capture_output=True, text=True)
        if cvt.returncode != 0:
            return False, f"cvt failed: {cvt.stderr.strip() or cvt.stdout.strip()}"
        # cvt output contains a Modeline line
        for line in cvt.stdout.splitlines():
            if line.strip().startswith("Modeline"):
                modeline = line.strip().split(' ', 1)[1]
                break
        else:
            return False, "Failed to parse cvt output"

        # Create a name for the mode
        mode_name = resolution
        # Run xrandr --newmode <name> <params>
        newmode_cmd = ["xrandr", "--newmode"] + modeline.split()
        r1 = subprocess.run(newmode_cmd, capture_output=True, text=True, env=env)
        if r1.returncode != 0:
            return False, f"xrandr --newmode failed: {r1.stderr.strip() or r1.stdout.strip()}"

        # Add mode to output
        r2 = subprocess.run(["xrandr", "--addmode", output, mode_name], capture_output=True, text=True, env=env)
        if r2.returncode != 0:
            return False, f"xrandr --addmode failed: {r2.stderr.strip() or r2.stdout.strip()}"

        return True, "Mode added"
    except FileNotFoundError:
        return False, "xrandr or cvt not installed"
    except Exception as e:
        return False, str(e)


def is_wlr_available():
    """Return True if wlr-randr is installed."""
    return shutil.which("wlr-randr") is not None


def map_rotation_for_wlr(rotation):
    """Map friendly rotation names to wlr-randr transform values.

    Accepts: 'normal','left','right','inverted' or numeric strings '90','180','270'.
    Returns string suitable for --transform or None if invalid.
    """
    if not rotation:
        return None
    rot = str(rotation).lower()
    mapping = {
        'normal': 'normal',
        'left': '90',
        'right': '270',
        'inverted': '180',
        '90': '90',
        '180': '180',
        '270': '270'
    }
    return mapping.get(rot, None)


def change_display_settings_wayland(output=None, resolution=None, rotation=None):
    """Change display settings using wlr-randr (Wayland compositor helper).

    Tries to run wlr-randr commands and returns (success, message).
    """
    try:
        if not is_wlr_available():
            return False, "wlr-randr not installed"

        # Prefer a supplied output, otherwise try to fall back
        if not output:
            # user can set a sensible default; try a common name
            output = os.environ.get('WLR_OUTPUT') or os.environ.get('WLR_RANDR_OUTPUT') or 'HDMI-A-1'

        msgs = []
        # Apply resolution first (if provided)
        if resolution:
            cmd = ["wlr-randr", "--output", output, "--mode", resolution]
            print(f"DEBUG: Running wlr-randr command: {' '.join(cmd)}")
            r = subprocess.run(cmd, capture_output=True, text=True)
            msgs.append(f"resolution: returncode={r.returncode}, stderr={r.stderr.strip()}")
            if r.returncode != 0:
                return False, f"wlr-randr resolution failed: {r.stderr.strip() or r.stdout.strip()}"

        # Apply rotation/transform
        if rotation:
            tr = map_rotation_for_wlr(rotation)
            if not tr:
                return False, f"Invalid rotation value for Wayland: {rotation}"
            cmd = ["wlr-randr", "--output", output, "--transform", tr]
            print(f"DEBUG: Running wlr-randr command: {' '.join(cmd)}")
            r = subprocess.run(cmd, capture_output=True, text=True)
            msgs.append(f"transform: returncode={r.returncode}, stderr={r.stderr.strip()}")
            if r.returncode != 0:
                return False, f"wlr-randr transform failed: {r.stderr.strip() or r.stdout.strip()}"

        return True, "; ".join(msgs) if msgs else "No changes specified"
    except Exception as e:
        return False, f"Wayland change error: {str(e)}"


def change_display_settings_rpi(resolution=None, rotation=None):
    """Fallback method for Raspberry Pi using config.txt and fbcon.
    
    - resolution: string like '1280x720' or None
    - rotation: one of 'normal', 'left', 'right', 'inverted' or None
    Returns (success, message)
    """
    print(f"DEBUG: change_display_settings_rpi called with resolution={resolution}, rotation={rotation}")
    
    try:
        changes_made = []
        
        # Handle rotation via fbcon if available (immediate effect)
        if rotation:
            print(f"DEBUG: Processing rotation change to {rotation}")
            rotation_map = {
                'normal': '0',
                'right': '1', 
                'inverted': '2',
                'left': '3'
            }
            
            if rotation in rotation_map:
                fbcon_path = "/sys/class/graphics/fbcon/rotate_all"
                print(f"DEBUG: Checking fbcon path: {fbcon_path}, exists={os.path.exists(fbcon_path)}")
                
                try:
                    # Try to apply rotation immediately via fbcon
                    if os.path.exists(fbcon_path):
                        cmd = ["sudo", "sh", "-c", f"echo {rotation_map[rotation]} > {fbcon_path}"]
                        print(f"DEBUG: Running rotation command: {' '.join(cmd)}")
                        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                        print(f"DEBUG: Rotation command result: returncode={result.returncode}, stdout='{result.stdout}', stderr='{result.stderr}'")
                        changes_made.append(f"rotation={rotation} (applied immediately)")
                        print(f"DEBUG: Rotation applied successfully")
                    else:
                        print(f"DEBUG: fbcon path not found: {fbcon_path}")
                        changes_made.append(f"rotation={rotation} (fbcon not available)")
                except Exception as e:
                    print(f"DEBUG: Rotation command failed: {str(e)}")
                    changes_made.append(f"rotation={rotation} (failed: {str(e)})")
            else:
                print(f"DEBUG: Invalid rotation value: {rotation}")
        
        # Handle resolution by modifying config.txt (requires reboot)
        if resolution:
            print(f"DEBUG: Processing resolution change to {resolution}")
            config_path = "/boot/config.txt"
            
            # Check if we can access config.txt
            if not os.path.exists(config_path):
                config_path = "/boot/firmware/config.txt"  # newer Pi OS location
            
            print(f"DEBUG: Using config path: {config_path}, exists={os.path.exists(config_path)}")
            
            if not os.path.exists(config_path):
                if changes_made:
                    return True, f"Applied: {', '.join(changes_made)}"
                print(f"DEBUG: Config file not found at either location")
                return False, "Cannot find config.txt for resolution changes."
            
            try:
                width, height = resolution.split('x')
                print(f"DEBUG: Parsed resolution: width={width}, height={height}")
                
                # Read current config
                print(f"DEBUG: Reading config file: {config_path}")
                with open(config_path, 'r') as f:
                    lines = f.readlines()
                print(f"DEBUG: Read {len(lines)} lines from config file")
                
                # Prepare new config lines
                new_lines = []
                removed_lines = []
                
                for line in lines:
                    # Remove existing hdmi settings
                    if (line.strip().startswith('hdmi_mode=') or 
                        line.strip().startswith('hdmi_group=') or
                        line.strip().startswith('hdmi_cvt=')):
                        removed_lines.append(line.strip())
                        continue
                    new_lines.append(line)
                
                print(f"DEBUG: Removed {len(removed_lines)} existing HDMI lines: {removed_lines}")
                
                # Add new resolution settings
                new_lines.append(f"hdmi_group=2\n")
                new_lines.append(f"hdmi_mode=87\n") 
                new_lines.append(f"hdmi_cvt={width} {height} 60\n")
                print(f"DEBUG: Added new HDMI settings: hdmi_group=2, hdmi_mode=87, hdmi_cvt={width} {height} 60")
                
                # Write back to config.txt
                print(f"DEBUG: Creating backup: {config_path}.backup")
                subprocess.run(["sudo", "cp", config_path, f"{config_path}.backup"], check=True)
                
                print(f"DEBUG: Writing new config to /tmp/new_config.txt")
                with open("/tmp/new_config.txt", 'w') as f:
                    f.writelines(new_lines)
                
                print(f"DEBUG: Moving new config to {config_path}")
                subprocess.run(["sudo", "mv", "/tmp/new_config.txt", config_path], check=True)
                
                changes_made.append(f"resolution={resolution} (requires reboot)")
                print(f"DEBUG: Resolution config updated successfully")
                
            except Exception as e:
                print(f"DEBUG: Resolution config update failed: {str(e)}")
                if changes_made:
                    return True, f"Applied: {', '.join(changes_made)}. Resolution failed: {str(e)}"
                return False, f"Failed to update config.txt: {str(e)}"
        
        if changes_made:
            msg = f"Applied: {', '.join(changes_made)}"
            if "requires reboot" in msg:
                msg += "\n\n⚠️ Use /reboot to apply resolution changes."
            print(f"DEBUG: RPi method SUCCESS: {msg}")
            return True, msg
        else:
            print(f"DEBUG: No changes were specified")
            return False, "No changes specified"
            
    except Exception as e:
        print(f"DEBUG: RPi method EXCEPTION: {str(e)}")
        return False, f"Error in RPi display config: {str(e)}"


def change_display_settings(output=None, resolution=None, rotation=None):
    """Change display resolution/rotation via xrandr or RPi fallback.

    - output: display output name (if None, autodetected)
    - resolution: string like '1280x720' or None to keep current
    - rotation: one of 'normal', 'left', 'right', 'inverted' or None
    Returns (success, message)
    """
    print(f"DEBUG: change_display_settings called with output={output}, resolution={resolution}, rotation={rotation}")
    
    # Prefer Wayland (wlr-randr) if available
    has_wlr = is_wlr_available()
    print(f"DEBUG: has_wlr={has_wlr}")
    if has_wlr:
        print("DEBUG: Attempting Wayland (wlr-randr) method...")
        # attempt Wayland method
        way_success, way_msg = change_display_settings_wayland(output=output, resolution=resolution, rotation=rotation)
        print(f"DEBUG: Wayland result: success={way_success}, msg={way_msg}")
        if way_success:
            return True, f"Applied via wlr-randr: {way_msg}"
        # else fall through to X or RPi fallback

    # Check if we have X environment and xrandr available
    display_env = os.environ.get("DISPLAY")
    has_xrandr = subprocess.run(["which", "xrandr"], capture_output=True).returncode == 0
    
    print(f"DEBUG: DISPLAY={display_env}, has_xrandr={has_xrandr}")
    
    if display_env and has_xrandr:
        print("DEBUG: Attempting xrandr method...")
        # Try xrandr first (GUI environment)
        try:
            if not output:
                output = get_primary_output()
                print(f"DEBUG: Detected output: {output}")
            if output:
                env = get_x_env()
                print(f"DEBUG: X environment: DISPLAY={env.get('DISPLAY')}, XAUTHORITY={env.get('XAUTHORITY')}")
                
                # If resolution not present, try to add the mode
                if resolution:
                    print(f"DEBUG: Ensuring mode {resolution} is available...")
                    ok, msg = ensure_mode_available(output, resolution, env=env)
                    print(f"DEBUG: Mode check result: ok={ok}, msg={msg}")
                    if not ok:
                        print("DEBUG: Mode unavailable, falling back to RPi method")
                        return change_display_settings_rpi(resolution, rotation)

                cmd = ["xrandr", "--output", output]
                if resolution:
                    cmd += ["--mode", resolution]
                if rotation:
                    cmd += ["--rotate", rotation]

                print(f"DEBUG: Running xrandr command: {' '.join(cmd)}")
                # run command with X environment
                r = subprocess.run(cmd, capture_output=True, text=True, env=env)
                print(f"DEBUG: xrandr result: returncode={r.returncode}, stdout='{r.stdout.strip()}', stderr='{r.stderr.strip()}'")
                
                if r.returncode == 0:
                    success_msg = f"Applied via xrandr on {output}: resolution={resolution or 'unchanged'}, rotation={rotation or 'unchanged'}."
                    print(f"DEBUG: xrandr SUCCESS: {success_msg}")
                    return True, success_msg
                else:
                    print("DEBUG: xrandr failed, falling back to RPi method")
                    return change_display_settings_rpi(resolution, rotation)
        except Exception as e:
            print(f"DEBUG: xrandr exception: {str(e)}, falling back to RPi method")
            pass
    else:
        print("DEBUG: No X environment or xrandr, using RPi method directly")
    
    # Fallback to Raspberry Pi method (headless/no X environment)
    print("DEBUG: Using RPi fallback method")
    return change_display_settings_rpi(resolution, rotation)


def get_display_info():
    """Get detailed display information using wlr-randr when available, fallback to other methods."""
    try:
        info = {"output": None, "resolution": None, "orientation": None, "frequency": None}
        
        # Try wlr-randr first (best for Wayland)
        if is_wlr_available():
            try:
                print("DEBUG: Getting display info via wlr-randr")
                result = subprocess.run(["wlr-randr"], capture_output=True, text=True, check=True)
                output_name = None
                current_mode = None
                transform = None
                
                for line in result.stdout.splitlines():
                    line = line.strip()
                    # Output line like: HDMI-A-1 "Lenovo Group Limited..."
                    if line and not line.startswith(' ') and '"' in line:
                        output_name = line.split()[0]
                        print(f"DEBUG: Found output: {output_name}")
                    # Current mode line like: 800x450 px, 60.049000 Hz (current)
                    elif "(current)" in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            current_mode = parts[0]  # e.g., "800x450"
                            freq_part = parts[2]  # e.g., "60.049000"
                            info["frequency"] = f"{freq_part}Hz"
                            print(f"DEBUG: Current mode: {current_mode}, freq: {freq_part}")
                    # Transform line like: Transform: 270
                    elif line.startswith("Transform:"):
                        transform_val = line.split(":")[1].strip()
                        # Map transform values back to friendly names
                        transform_map = {
                            'normal': 'normal',
                            '90': 'left', 
                            '180': 'inverted',
                            '270': 'right'
                        }
                        transform = transform_map.get(transform_val, transform_val)
                        print(f"DEBUG: Transform: {transform_val} -> {transform}")
                
                if output_name:
                    info["output"] = output_name
                if current_mode:
                    info["resolution"] = current_mode
                if transform:
                    info["orientation"] = transform
                
                # If we got good info from wlr-randr, return it
                if info["output"] and info["resolution"]:
                    info["output"] = info["output"] or "Unknown"
                    info["resolution"] = info["resolution"] or "Unknown" 
                    info["orientation"] = info["orientation"] or "normal"
                    info["frequency"] = info["frequency"] or "60Hz (estimated)"
                    print(f"DEBUG: wlr-randr info: {info}")
                    return info
                    
            except Exception as e:
                print(f"DEBUG: wlr-randr failed: {str(e)}")
                pass
        
        # Try xrandr if we have X environment
        if os.environ.get("DISPLAY"):
            try:
                print("DEBUG: Getting display info via xrandr")
                x = subprocess.run(["xrandr", "--query"], capture_output=True, text=True, check=True, env=get_x_env())
                current_line = None
                for line in x.stdout.splitlines():
                    if " connected" in line and " primary " in line:
                        info["output"] = line.split()[0]
                        # Extract current resolution and orientation
                        if "+" in line:
                            res_part = line.split()[2] if len(line.split()) > 2 else ""
                            if "x" in res_part:
                                info["resolution"] = res_part.split("+")[0]
                            # Check for rotation info
                            if " left " in line:
                                info["orientation"] = "left"
                            elif " right " in line:
                                info["orientation"] = "right"
                            elif " inverted " in line:
                                info["orientation"] = "inverted"
                            else:
                                info["orientation"] = "normal"
                    elif line.startswith("   ") and "*" in line and "+" in line:
                        # Current mode line like "   1920x1080     60.00*+  59.93"
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            freq = parts[1].replace("*", "").replace("+", "")
                            info["frequency"] = f"{freq}Hz"
                        break
                if info["output"]:
                    print(f"DEBUG: xrandr info: {info}")
                    return info
            except Exception as e:
                print(f"DEBUG: xrandr failed: {str(e)}")
                pass
        
        # Fallback to RPi methods (for headless systems)
        print("DEBUG: Using RPi fallback methods")
        try:
            # Get framebuffer resolution
            fb_info = subprocess.run(["fbset"], capture_output=True, text=True)
            if fb_info.returncode == 0:
                for line in fb_info.stdout.splitlines():
                    if "geometry" in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            info["resolution"] = f"{parts[1]}x{parts[2]}"
                        break
        except:
            pass
        
        # Get rotation from fbcon
        try:
            if os.path.exists("/sys/class/graphics/fbcon/rotate_all"):
                with open("/sys/class/graphics/fbcon/rotate_all", 'r') as f:
                    rotate_val = f.read().strip()
                    rotate_map = {'0': 'normal', '1': 'right', '2': 'inverted', '3': 'left'}
                    info["orientation"] = rotate_map.get(rotate_val, 'normal')
        except:
            info["orientation"] = "normal"
        
        # Set defaults for missing info
        info["output"] = info["output"] or "HDMI (RPi)"
        info["resolution"] = info["resolution"] or "Unknown"
        info["frequency"] = info["frequency"] or "60Hz (estimated)"
        info["orientation"] = info["orientation"] or "normal"
        
        print(f"DEBUG: Final fallback info: {info}")
        return info
        
    except Exception as e:
        print(f"DEBUG: get_display_info exception: {str(e)}")
        return {"output": "Error", "resolution": "Unknown", "orientation": "normal", "frequency": "Unknown"}

# Function to generate an inline keyboard
def service_keyboard(service_name):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("🔄Restart", callback_data=f"{service_name}_restart"),
        InlineKeyboardButton("⛔Stop", callback_data=f"{service_name}_stop"),
        InlineKeyboardButton("🟡Status", callback_data=f"{service_name}_status")
    )
    return markup


def screen_keyboard():
    """Inline keyboard for screen orientation/resolution matching the Screen Configuration GUI."""
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    # Orientation buttons (matching the GUI options)
    markup.add(
        InlineKeyboardButton("� Normal", callback_data="screen_orient_normal"),
        InlineKeyboardButton("↪️ Left", callback_data="screen_orient_left")
    )
    markup.add(
        InlineKeyboardButton("🔄 Inverted", callback_data="screen_orient_inverted"),
        InlineKeyboardButton("↩️ Right", callback_data="screen_orient_right")
    )
    # Resolution options
    markup.add(
        InlineKeyboardButton("🖥️ Resolution", callback_data="screen_resolution_menu")
    )
    # Current configuration (status)
    markup.add(
        InlineKeyboardButton("� Current screen config", callback_data="screen_status")
    )
    return markup


def resolution_keyboard():
    """Inline keyboard for resolution selection."""
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("1920x1080", callback_data="screen_res_1920x1080"),
        InlineKeyboardButton("1440x900", callback_data="screen_res_1440x900")
    )
    markup.add(
        InlineKeyboardButton("1280x1024", callback_data="screen_res_1280x1024"),
        InlineKeyboardButton("1280x720", callback_data="screen_res_1280x720")
    )
    markup.add(
        InlineKeyboardButton("1024x768", callback_data="screen_res_1024x768"),
        InlineKeyboardButton("1024x600", callback_data="screen_res_1024x600")
    )
    
    # Standard resolutions
    markup.add(
        InlineKeyboardButton("800x600", callback_data="screen_res_800x600"),
        InlineKeyboardButton("800x450", callback_data="screen_res_800x450")
    )
    markup.add(
        InlineKeyboardButton("832x624", callback_data="screen_res_832x624"),
        InlineKeyboardButton("720x576", callback_data="screen_res_720x576")
    )
    markup.add(
        InlineKeyboardButton("720x480", callback_data="screen_res_720x480"),
        InlineKeyboardButton("720x400", callback_data="screen_res_720x400")
    )
    markup.add(
        InlineKeyboardButton("640x480", callback_data="screen_res_640x480"),
        InlineKeyboardButton("🔙 Back", callback_data="screen_main_menu")
    )
    return markup

@bot.message_handler(commands=['gui'])
def gui_service(message):
    bot.send_message(message.chat.id, "Manage GUI service:", reply_markup=service_keyboard("display"))

@bot.message_handler(commands=['camera'])
def camera_service(message):
    bot.send_message(message.chat.id, "Manage Camera service:", reply_markup=service_keyboard("camera"))


@bot.message_handler(commands=['screen'])
def screen_service(message):
    """Send inline keyboard to allow changing orientation and resolution."""
    print(f"DEBUG: /screen command received from user_id={message.from_user.id}, chat_id={message.chat.id}")
    bot.send_message(message.chat.id, "Manage screen orientation/resolution:", reply_markup=screen_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith(("display", "camera", "screen")))
def callback_inline(call):
    print(f"DEBUG: Callback received: call.data='{call.data}', chat_id={call.message.chat.id}, user_id={call.from_user.id}")
    
    # service callbacks (display/camera)
    if call.data.startswith(("display", "camera")):
        print(f"DEBUG: Processing service callback: {call.data}")
        service_name, action = call.data.split("_")
        if action == "status":
            status = check_service_status(service_name)
            bot.answer_callback_query(call.id, f"Service '{service_name}' status: {status}")
        else:
            manage_service(call, service_name, action)
        return

    # screen callbacks
    if call.data.startswith("screen_"):
        print(f"DEBUG: Processing screen callback: {call.data}")
        parts = call.data.split("_")
        print(f"DEBUG: Parsed callback parts: {parts}")
        
        if parts[1] == "orient":
            # Handle all four orientation options: normal, left, inverted, right
            orient = parts[2]
            print(f"DEBUG: Orientation change requested: {orient}")
            success, msg = change_display_settings(rotation=orient)
            print(f"DEBUG: Orientation change result: success={success}, msg='{msg}'")
            bot.answer_callback_query(call.id, msg)
            bot.send_message(call.message.chat.id, msg)
            
        elif parts[1] == "res":
            # Handle resolution changes
            res = parts[2]
            print(f"DEBUG: Resolution change requested: {res}")
            success, msg = change_display_settings(resolution=res)
            print(f"DEBUG: Resolution change result: success={success}, msg='{msg}'")
            bot.answer_callback_query(call.id, msg)
            bot.send_message(call.message.chat.id, msg)
            
        elif parts[1] == "resolution":
            # Show resolution menu
            if parts[2] == "menu":
                print(f"DEBUG: Showing resolution menu")
                bot.edit_message_text(
                    "Select Resolution:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=resolution_keyboard()
                )
                bot.answer_callback_query(call.id, "Select a resolution")
                
        elif parts[1] == "main":
            # Back to main menu
            if parts[2] == "menu":
                print(f"DEBUG: Returning to main menu")
                bot.edit_message_text(
                    "Manage screen orientation/resolution:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=screen_keyboard()
                )
                bot.answer_callback_query(call.id, "Back to main menu")
                
        elif parts[1] == "status":
            # Show detailed status like the GUI
            print(f"DEBUG: Status request")
            info = get_display_info()
            print(f"DEBUG: Display info retrieved: {info}")
            status_msg = f"📺 Display Information:\n"
            status_msg += f"Output: {info['output']}\n"
            status_msg += f"Resolution: {info['resolution']}\n"
            status_msg += f"Orientation: {info['orientation'].title()}\n"
            status_msg += f"Frequency: {info['frequency']}"
            
            bot.answer_callback_query(call.id, "Showing display status")
            bot.send_message(call.message.chat.id, status_msg)
            
        
        else:
            print(f"DEBUG: Unknown screen action: {parts}")
            bot.answer_callback_query(call.id, "Unknown screen action")

@bot.message_handler(commands=['reboot'])
def reboot_rpi(message):
    bot.reply_to(message, "Rebooting...")
    os.system("sudo reboot")

@bot.message_handler(func=lambda message: True)
def handle_data(message):
    bot.reply_to(message, f"Received data: {message.text}")

# Start bot with automatic retry
def start_bot():
    send_ip_at_startup()
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except telebot.apihelper.ApiException as e:
            print(f"Telegram API error: {e}")
            time.sleep(10)
        except Exception as e:
            print(f"Unhandled error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_bot()