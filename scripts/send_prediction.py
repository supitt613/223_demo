import requests
from supabase import create_client, Client
import os
from collections import Counter
from datetime import datetime, timedelta

# 載入環境變數 (在 GitHub Actions 中會直接從 secrets 讀取)
# from dotenv import load_dotenv
# load_dotenv()

# Supabase 連線資訊
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
LINE_NOTIFY_TOKEN = os.getenv("LINE_NOTIFY_TOKEN")

if not SUPABASE_URL or not SUPABASE_KEY or not LINE_NOTIFY_TOKEN:
    raise ValueError("Supabase URL, Key, and Line Notify Token must be set as environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_recent_lotto_data(days: int = 30) -> list:
    """
    從 Supabase 獲取最近 N 天的樂透數據。
    Args:
        days (int): 要獲取的天數。
    Returns:
        list: 最近的樂透數據列表。
    """
    today = datetime.now()
    # 考慮到開獎日期可能不是連續的，我們獲取最近 N 筆資料而不是 N 天內的資料
    # 這裡假設我們需要足夠的數據來進行頻率分析，所以直接取最新的 N 筆
    try:
        response = supabase.from_('lotto539_data') \
                           .select('n1, n2, n3, n4, n5') \
                           .order('draw_date', desc=True) \
                           .limit(days * 2) \
                           .execute()
        if response.data:
            return response.data
    except Exception as e:
        print(f"Error fetching recent lotto data from Supabase: {e}")
    return []

def predict_lotto_numbers(recent_data: list) -> list:
    """
    根據最近的開獎數據，預測下期可能開出的號碼。
    此為一個簡單的頻率分析模型：找出在最近數據中出現頻率最高的號碼。
    Args:
        recent_data (list): 最近的開獎數據。
    Returns:
        list: 預測的號碼列表。
    """
    if not recent_data:
        return []

    all_numbers = []
    for row in recent_data:
        all_numbers.extend([row['n1'], row['n2'], row['n3'], row['n4'], row['n5']])

    # 計算每個號碼的出現頻率
    number_counts = Counter(all_numbers)

    # 獲取出現頻率最高的 5 個號碼
    # 如果有相同頻率，則取號碼較小的
    predicted_numbers = sorted(number_counts.most_common(5), key=lambda x: (-x[1], x[0]))
    return [num for num, count in predicted_numbers]

def send_line_notification(message: str):
    """
    透過 Line Notify 發送通知。
    Args:
        message (str): 要發送的訊息內容。
    """
    line_notify_api = 'https://notify-api.line.me/api/notify'
    headers = {
        'Authorization': f'Bearer {LINE_NOTIFY_TOKEN}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    payload = {'message': message}

    try:
        response = requests.post(line_notify_api, headers=headers, data=payload, timeout=10)
        response.raise_for_status() # 檢查 HTTP 請求是否成功
        print(f"Line notification sent. Status: {response.status_code}, Response: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Line notification: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during Line notification: {e}")

def main():
    print("Starting lottery prediction and Line notification...")
    recent_data = get_recent_lotto_data(days=60) # 獲取最近 60 期數據進行分析

    if not recent_data:
        message = "[539 預測] 無法獲取足夠的歷史數據進行預測。"
        print(message)
        send_line_notification(message)
        return

    predicted_numbers = predict_lotto_numbers(recent_data)

    if predicted_numbers:
        message = f"\n[539 預測] {datetime.now().strftime('%Y-%m-%d')} 預測號碼：\n{' '.join(map(str, predicted_numbers))}\n(此為基於歷史頻率的簡單預測，僅供參考。)"
    else:
        message = "[539 預測] 無法生成預測號碼。"

    print(message)
    send_line_notification(message)
    print("Lottery prediction and Line notification finished.")

if __name__ == "__main__":
    main()
