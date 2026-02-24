import requests
from supabase import create_client, Client
import os
from collections import Counter
from datetime import datetime

# --- 1. 配置與驗證區 ---
# 這些變數會從 GitHub Actions 的 Secrets 讀取
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

def validate_config():
    """確保所有必要的環境變數都已設定"""
    keys = {
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY": SUPABASE_KEY,
        "LINE_ACCESS_TOKEN": LINE_ACCESS_TOKEN,
        "LINE_USER_ID": LINE_USER_ID
    }
    missing = [k for k, v in keys.items() if not v]
    if missing:
        raise ValueError(f"錯誤：缺少環境變數：{', '.join(missing)}")

validate_config()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. 核心功能函式 ---

def get_recent_lotto_data(limit: int = 60) -> list:
    """從 Supabase 獲取最新開獎數據"""
    try:
        response = (
            supabase.table('lotto539_data')
            .select('n1, n2, n3, n4, n5')
            .order('draw_date', desc=True)
            .limit(limit)
            .execute()
        )
        return response.data if response.data else []
    except Exception as e:
        print(f"Supabase 數據讀取失敗: {e}")
        return []

def predict_lotto_numbers(recent_data: list) -> list:
    """基於出現頻率的簡單預測模型"""
    if not recent_data: return []
    all_numbers = []
    for row in recent_data:
        all_numbers.extend([row['n1'], row['n2'], row['n3'], row['n4'], row['n5']])
    number_counts = Counter(all_numbers)
    # 獲取出現頻率最高的 5 個號碼
    predicted = sorted(number_counts.most_common(5), key=lambda x: (-x[1], x[0]))
    return [num for num, count in predicted]

def send_line_msg(text):
    """使用您提供的 LINE Messaging API 發送通知"""
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
        # 使用 json=payload 自動處理 JSON 格式
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        print(f"✅ LINE 訊息發送成功 (Status: {response.status_code})")
    except Exception as e: 
        print(f"❌ LINE 發送失敗: {e}")

# --- 3. 主執行流程 ---

def main():
    print(f"[{datetime.now()}] 啟動 539 預測任務...")
    recent_data = get_recent_lotto_data(limit=60)
    
    if not recent_data:
        send_line_msg("⚠️ 預測失敗：無法從資料庫獲取歷史資料。")
        return

    predicted_numbers = predict_lotto_numbers(recent_data)

    if predicted_numbers:
        formatted_nums = ", ".join(map(lambda x: f"{int(x):02d}", predicted_numbers))
        message = (
            f"🎯 539 預測通知 ({datetime.now().strftime('%Y-%m-%d')})\n"
            f"✨ 推薦熱門號碼：{formatted_nums}\n\n"
            f"💡 說明：此為基於最近 60 期開獎頻率統計。"
        )
    else:
        message = "❌ 無法產出預測號碼。"

    print(message)
    send_line_msg(message)

if __name__ == "__main__":
    main()
