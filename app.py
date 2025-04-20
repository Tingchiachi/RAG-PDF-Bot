# app.py
from flask import Flask, request, abort
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient, TextMessage, ReplyMessageRequest
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.exceptions import InvalidSignatureError
from langchain_community.chat_message_histories import SQLChatMessageHistory
from rag_chain import answer_query
from dotenv import load_dotenv
import os
import logging
from sqlalchemy import create_engine

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

load_dotenv(".env")
app = Flask(__name__)

configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
api_client = ApiClient(configuration)
messaging_api = MessagingApi(api_client)
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
engine = create_engine("sqlite:///./chat_history.db")

def clear_user_history(user_id: str):
    history = SQLChatMessageHistory(session_id=user_id, connection=engine)
    history.clear()
    
def get_user_history(user_id: str, max_turns: int = 5) -> str:
    history = SQLChatMessageHistory(session_id=user_id, connection=engine)
    messages = history.messages[-max_turns * 2:]  # 每輪問答佔 2 筆
    if not messages:
        return "沒有找到您的歷史對話紀錄喔"
    output = []
    for i in range(0, len(messages), 2):
        q = messages[i].content if i < len(messages) else ""
        a = messages[i + 1].content if i + 1 < len(messages) else ""
        output.append(f"Q: {q}\nA: {a}")
    return "最近的對話紀錄：\n\n" + "\n\n".join(output)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    user_text = event.message.text
    reply_token = event.reply_token

    if user_text.strip().lower() == "/clear":
        clear_user_history(user_id)
        reply_text = "已清除您的對話歷史"
    elif user_text.strip().lower() == "/history":
        reply_text = get_user_history(user_id)
    else:
        reply_text = answer_query(user_text, user_id)

    print(f"{user_id}(User ID) : {user_text}")
    print(f"Bot : {reply_text}")

    reply = ReplyMessageRequest(
        reply_token=reply_token,
        messages=[TextMessage(text=reply_text)]
    )

    messaging_api.reply_message(reply)

if __name__ == "__main__":
    app.run(host=os.getenv("LOCAL_HOST"), 
            port=os.getenv("LOCAL_PORT"))
