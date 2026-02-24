import requests
from supabase import create_client, Client
import os
from collections import Counter
from datetime import datetime

# --- 1. 配置與驗證區 ---
# 這些環境變數必須在 GitHub Secrets 中設定
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

def validate_config():
    """驗證必要的環境變數"""
    missing = [k for k, v in {
        "SUPABASE_URL": SUPABASE_URL, 
        "SUPABASE_KEY": SUPABASE_KEY, 
        "LINE_ACCESS_TOKEN": LINE_ACCESS_TOKEN, 
        "LINE_USER_ID": LINE_USER_ID
    }.items() if not v]
    
    if missing:
        raise ValueError(f"❌ 錯誤：缺少環境變數：{', '.join(missing)}")

validate_config()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. 核心功能函式 ---

def get_recent_lotto_data(limit: int = 60):
    """
    從 Supabase 獲取最新開獎數據。
    關鍵：使用 order('draw_date', desc=True) 確保 2026-02-23 排在最前面。
    """
    try:
        # 您剛才問的這段程式碼就在這裡執行
        response = (
            supabase.table('lotto539_data')
            .select('*')
            .order('draw_date', desc=True) 
            .limit(limit)
            .execute()
        )
        return response.data if response.data else []
    except Exception as e:
        print(f"❌ 數據讀取失敗: {e}")
        return []

def predict_lotto_numbers(recent_data: list) -> list:
    """基於熱門頻率的預測模型"""
    if not recent_data:
        return []

    all_numbers = []
    for row in recent_data:
        # 確保抓取 n1~n5 欄位
        all_numbers.extend([row['n1'], row['n2'], row['n3'], row['n4'], row['n5']])

    # 計算頻率
    number_counts = Counter(all_numbers)

    # 獲取出現頻率最高的 5 個號碼
    # 排序規則：頻率由高到低 (-x[1])，若頻率相同則按號碼由小到大 (x[0])
    predicted = sorted(number_counts.most_common(5), key=lambda x: (-x[1], x[0]))
    return [num for num, count in predicted]

def send_line_msg(text: str):
    """使用 LINE Messaging API 發送 Push Message"""
    if not LINE_ACCESS_TOKEN: return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": text}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        print(f"✅ LINE 通知發送成功 (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ LINE 發送失敗: {e}")

# --- 3. 主執行流程 ---

def main():
    print(f"[{datetime.now()}] 啟動 539 預測任務...")
    
    # 1. 抓取最新 60 期資料 (包含剛剛補進去的 2/23)
    recent_data = get_recent_lotto_data(limit=60)
    
    if not recent_data:
        msg = "⚠️ 預測失敗：無法從資料庫獲取足夠的歷史資料。"
        print(msg)
        send_line_msg(msg)
        return

    # 取得資料庫中最新一筆資料的日期 (用來確認資料是否有同步)
    latest_db_date = recent_data[0]['draw_date']
    
    # 2. 生成預測號碼
    predicted_numbers = predict_lotto_numbers(recent_data)

    if predicted_numbers:
        # 格式化號碼，例如 8 變成 08
        formatted_nums = ", ".join(map(lambda x: f"{int(x):02d}", predicted_numbers))
        message = (
            f"🎯 今彩 539 數據預測 ({datetime.now().strftime('%Y-%m-%d')})\n"
            f"📈 數據統計截止至：{latest_db_date}\n"
            f"✨ 推薦熱門號碼：{formatted_nums}\n\n"
            f"💡 說明：此結果基於最近 60 期開獎頻率統計。"
        )
    else:
        message = "❌ 警告：無法產出預測號碼，請檢查資料格式。"

    print(message)
    # 3. 發送 LINE
    send_line_msg(message)
    print("任務結束。")

if __name__ == "__main__":
    main()
