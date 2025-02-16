from flask import Flask, request, abort
import pandas as pd
import fitz  # PyMuPDF，用於解析 PDF
import io
import os
import requests

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
    TextMessageContent,
    FileMessageContent
)

app = Flask(__name__)

configuration = Configuration(access_token='jtzDIgiW6V74emUv/awm8R7GLG6UR1c770Kc46YmMIJjzhhnF88+cg3+yBhPO4xpBhNkA3tNa/GCa9+4oMHy4sxKQsaYNCCHXacHFnRvgGf2vCDg8Tedj78BRqeljrCOlCFu034RyqqCh0OjOsPCxwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('f3c72fcc60b3f0c9b112ededdd56a69b')

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

# 處理文字訊息
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        reply_text = f"你說了: {event.message.text}"
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

# 處理 PDF 上傳
@handler.add(MessageEvent, message=FileMessageContent)
@handler.add(MessageEvent, message=FileMessageContent)
def handle_pdf_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # 下載 PDF
        message_id = event.message.id
        headers = {"Authorization": f"Bearer {configuration.access_token}"}
        content_url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
        response = requests.get(content_url, headers=headers, stream=True)

        if response.status_code != 200:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="❌ 無法下載 PDF，請稍後再試")]
                )
            )
            return

        # 確保 "pic" 資料夾存在
        save_dir = os.path.join(os.getcwd(), "pic")
        os.makedirs(save_dir, exist_ok=True)

        # 儲存 PDF 到 "pic" 資料夾
        file_path = os.path.join(save_dir, f"{message_id}.pdf")
        with open(file_path, "wb") as f:
            f.write(response.content)

        # 解析 PDF 內容
        pdf_df = extract_text_from_pdf(file_path)

        # 格式化數據
        format_df = format_schedule(pdf_df)

        # **確保訊息長度不超過 5000 字**
        max_length = 5000
        response_text = f"解析內容：\n{format_df.to_string(index=False)}"

        if len(response_text) > max_length:
            response_text = response_text[:max_length]  # 截斷字串避免超過 5000 字

        # **回覆用戶**
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=response_text)]
            )
        )


def extract_text_from_pdf(file_path):
    """從 PDF 解析表格並轉換成 DataFrame"""
    data = []
    doc = fitz.open(file_path)

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("blocks")  # 獲取區塊
        text = sorted(text, key=lambda block: (block[1], block[0]))  # 按照 (y, x) 排序

        for block in text:
            line = block[4].strip()  # 取出文字內容
            columns = line.split()   # 用空格分割欄位
            if len(columns) > 1:
                data.append(columns)

    # 轉換為 DataFrame
    df = pd.DataFrame(data)

    # **顯示前 10 行**
    print("🔍 解析出的原始 DataFrame:")
    print(df.head(10))

    return df

def format_schedule(df):
    """格式化 DataFrame 內的航班資訊"""

    # **合併所有欄位為一行，確保數據不會被拆開**
    df["merged"] = df.apply(lambda row: " ".join(row.dropna().astype(str)), axis=1)

    # **檢查 `df["merged"]` 的前幾行**
    print("🔍 `df['merged']` 內容:")
    print(df["merged"].head(10))

    # **擷取正確的 `company, employee_code, name`**
    company = df.iloc[0, 0] if len(df) > 0 else "Unknown"
    name = f"{df.iloc[1, 1]} {df.iloc[1, 2]} {df.iloc[1, 3]}" if len(df) > 1 else "Unknown"
    employee_code = df.iloc[2, 2] if len(df) > 2 else "Unknown"

    data = []

    # **遍歷 `df["merged"]`，查找班表資訊**
    for _, row in df.iterrows():
        text = row["merged"]
        columns = text.split()

        if len(columns) >= 3 and columns[0] in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            date = f"{columns[1]}-{columns[0]}"  # 例如：01-Jan Wed
            date = date.replace("--", "-").strip()

            duty = columns[2] if len(columns) > 2 else None
            from_location = columns[3] if len(columns) > 3 else None
            report_time = columns[4] if len(columns) > 4 else None
            to_location = columns[5] if len(columns) > 5 else None
            release_time = columns[6] if len(columns) > 6 else None
            scheduled_route_block = columns[7] if len(columns) > 7 else None
            flight_time = columns[8] if len(columns) > 8 else None
            duty_time = columns[9] if len(columns) > 9 else None
            tafb_time = columns[10] if len(columns) > 10 else None
            reset_time = columns[11] if len(columns) > 11 else None

            # **處理 `sector_event` 和 `allowances`**
            sector_event = []
            allowances = None
            remaining_parts = columns[12:] if len(columns) > 12 else []

            for part in remaining_parts:
                if "L" in part or "-" in part:  # 可能是航班資訊
                    sector_event.append(part)
                else:  # 可能是 Allowances
                    allowances = part

            # **存入資料列表**
            data.append([company, employee_code, name, date, duty, from_location, report_time, to_location,
                         release_time, scheduled_route_block, flight_time, duty_time, tafb_time, reset_time, 
                         " | ".join(sector_event), allowances])

    # **轉換為 DataFrame**
    columns = ["company", "employee_code", "name", "date", "duty", "from", "report", "to", "release",
               "scheduled_route_block", "flight_time", "duty_time", "tafb_time", "reset_time", "sector_event", "allowances"]

    format_df = pd.DataFrame(data, columns=columns)

    print("✅ 解析後的 DataFrame：")
    print(format_df.head(10))  # Debugging print
    return format_df


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
