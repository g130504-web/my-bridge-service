import configparser
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage
import telegram

app = Flask(__name__)

# --- Configuration ---
config = configparser.ConfigParser()
config.read('config.ini')

# LINE Bot
line_bot_api = LineBotApi(config.get('line', 'channel_access_token'))
handler = WebhookHandler(config.get('line', 'channel_secret'))
LINE_USER_ID = config.get('line', 'user_id')

# Telegram Bot
telegram_bot = telegram.Bot(token=config.get('telegram', 'bot_token'))
TELEGRAM_CHAT_ID = config.get('telegram', 'chat_id')
# --- End Configuration ---

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # Forward message from LINE to Telegram
    message_text = f"[LINE] {event.source.user_id}:\n{event.message.text}"
    telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message_text)

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    update = request.get_json()
    if 'message' in update:
        message = update['message']
        # Forward message from Telegram to LINE
        message_text = f"[Telegram] {message['from']['first_name']}:\n{message['text']}"
        line_bot_api.push_message(LINE_USER_ID, TextMessage(text=message_text))
    return 'OK'

if __name__ == "__main__":
    app.run()
