import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, JoinEvent
import telegram
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- Configuration ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# --- File path for persistence on Render Disk ---
DESTINATION_FILE = '/var/data/line_destination.txt'

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
telegram_bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

def save_destination(dest_id):
    try:
        os.makedirs(os.path.dirname(DESTINATION_FILE), exist_ok=True)
        with open(DESTINATION_FILE, 'w') as f:
            f.write(dest_id)
        app.logger.info(f"Successfully saved destination ID: {dest_id}")
    except Exception as e:
        app.logger.error(f"Failed to save destination ID: {e}")

def load_destination():
    if os.path.exists(DESTINATION_FILE):
        with open(DESTINATION_FILE, 'r') as f:
            return f.read().strip()
    return None

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(JoinEvent)
def handle_join(event):
    dest_id = None
    if hasattr(event.source, 'group_id'):
        dest_id = event.source.group_id
    elif hasattr(event.source, 'user_id'):
        dest_id = event.source.user_id

    if dest_id:
        save_destination(dest_id)
        line_bot_api.reply_message(
            event.reply_token,
            TextMessage(text='[Bridge Bot] 已將此處設為Telegram訊息目的地。')
        )

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    line_destination_id = load_destination()
    if not line_destination_id:
        app.logger.warning("Telegram message received, but no LINE destination is set. Please re-invite the LINE bot to a group.")
        return 'OK'

    update = request.get_json()
    if 'message' in update and 'text' in update['message']:
        sender_name = update['message']['from'].get('first_name', 'Unknown')
        chat_text = update['message']['text']

        message_to_line = f"[Telegram - {sender_name}]:\n{chat_text}"
        line_bot_api.push_message(line_destination_id, TextMessage(text=message_to_line))
    return 'OK'

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
