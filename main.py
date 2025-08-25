import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, JoinEvent
import telegram

app = Flask(__name__)

# --- Read credentials from Environment Variables ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# This variable will hold the destination for TG messages
# It will be set when the bot is first added to a LINE group
line_destination_id = None

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
telegram_bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

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
    global line_destination_id
    # When bot joins a group, set that group as the destination
    if hasattr(event.source, 'group_id'):
        line_destination_id = event.source.group_id
    elif hasattr(event.source, 'user_id'):
        line_destination_id = event.source.user_id
    app.logger.info(f"LINE destination set to: {line_destination_id}")
    line_bot_api.reply_message(
        event.reply_token,
        TextMessage(text='[Bridge Bot] 已將此處設為Telegram訊息目的地。')
    )

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    global line_destination_id
    if not line_destination_id:
        app.logger.warning("Telegram message received, but no LINE destination is set.")
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
