import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import socket
import subprocess
import time
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing in the .env file.")
bot = telebot.TeleBot(BOT_TOKEN)

# Function to handle service actions
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

# Function to generate an inline keyboard
def service_keyboard(service_name):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("Restart", callback_data=f"{service_name}_restart"),
        InlineKeyboardButton("Stop", callback_data=f"{service_name}_stop"),
        InlineKeyboardButton("Status", callback_data=f"{service_name}_status")
    )
    return markup

# Command handler for /gui
@bot.message_handler(commands=['gui'])
def gui_service(message):
    bot.send_message(message.chat.id, "Manage GUI service:", reply_markup=service_keyboard("gui"))

# Command handler for /camera
@bot.message_handler(commands=['camera'])
def camera_service(message):
    bot.send_message(message.chat.id, "Manage Camera service:", reply_markup=service_keyboard("camera"))

# Callback handler for inline buttons
@bot.callback_query_handler(func=lambda call: call.data.startswith(("gui", "camera")))
def callback_inline(call):
    service_name, action = call.data.split("_")
    if action == "status":
        status = check_service_status(service_name)
        bot.answer_callback_query(call.id, f"Service '{service_name}' status: {status}")
    else:
        manage_service(call, service_name, action)

# Start the bot
if __name__ == "__main__":
    bot.polling(none_stop=True)
