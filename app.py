# app.py
from flask import Flask, request, abort
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient, TextMessage, ReplyMessageRequest
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.exceptions import InvalidSignatureError
from rag_chain import answer_query
from dotenv import load_dotenv
import os
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

load_dotenv(".env")
app = Flask(__name__)

configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
api_client = ApiClient(configuration)
messaging_api = MessagingApi(api_client)
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@app.route("/callback", methods=['POST'])
def callback():
    # print("Webhook 收到請求")
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_text = event.message.text
    reply_token = event.reply_token
    reply_text = answer_query(user_text)

    print(f"User: {user_text}")
    print(f"Bot : {reply_text}")

    reply = ReplyMessageRequest(
        reply_token=reply_token,
        messages=[TextMessage(text=reply_text)]
    )

    messaging_api.reply_message(reply)

if __name__ == "__main__":
    app.run(host=os.getenv("LOCAL_HOST"), 
            port=os.getenv("LOCAL_PORT"))
