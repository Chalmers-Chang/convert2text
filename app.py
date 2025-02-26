from flask import Flask, request, abort


from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)

app = Flask(__name__)

configuration = Configuration(access_token='jtzDIgiW6V74emUv/awm8R7GLG6UR1c770Kc46YmMIJjzhhnF88+cg3+yBhPO4xpBhNkA3tNa/GCa9+4oMHy4sxKQsaYNCCHXacHFnRvgGf2vCDg8Tedj78BRqeljrCOlCFu034RyqqCh0OjOsPCxwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('f3c72fcc60b3f0c9b112ededdd56a69b')


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=event.message.text)]
            )
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)



