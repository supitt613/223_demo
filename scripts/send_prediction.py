import requests
from supabase import create_client, Client
import os
from collections import Counter
from datetime import datetime

# --- 配置 ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

def validate_config():
    missing = [k for k, v in {"SUPABASE_URL": SUPABASE_URL, "SUPABASE_KEY": SUPABASE_KEY, "LINE_ACCESS_TOKEN": LINE_ACCESS_TOKEN, "LINE_USER_ID": LINE_USER_ID}.items() if not v]
    if missing: raise ValueError(f"缺少環境變數：{', '.join(missing)}")

validate_config()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_recent_lotto_data(limit: int = 60):
    try:
        # 關鍵修正：確保 order(draw_date, desc=True) 抓取最新資料
        response = (
            supabase.table('lotto539_data')
            .select('n1, n2, n3, n4, n5, draw_date')
            .order('draw_date', desc=True)
            .limit(limit)
            .execute()
        )
        return response.data if response.data else []
    except Exception as e:
        print(f"數據讀取失敗: {e}")
        return []

def predict_lotto_numbers(recent_data):
    if not recent_data: return []
    all_numbers = []
    for row in recent_data:
        all_numbers.extend([row['n1'], row['n2'], row['n3'], row['n4'], row['n5']])
    
    counts = Counter(all_numbers)
    # 頻率高者優先，頻率相同則號碼小者優先
    predicted = sorted(counts.most_common(5), key=lambda x: (-x[1], x[0]))
    return [num for num, count in predicted]

def send_line_msg(text):
    if not LINE_ACCESS_TOKEN: return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": text}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"✅ LINE 成功 ({response.status_code})")
    except Exception as e: 
        print(f"❌ LINE 失敗: {e}")

def main():
    print(f"[{datetime.now()}] 啟動預測任務...")
    recent_data = get_recent_lotto_data(limit=60)
    
    if not recent_data:
        send_line_msg("⚠️ 預測失敗：資料庫無數據。")
        return

    # 取得最新一筆資料的日期
    latest_date = recent_data[0]['draw_date']
    predicted_nums = predict_lotto_numbers(recent_data)

    if predicted_nums:
        formatted_nums = ", ".join(map(lambda x: f"{int(x):02d}", predicted_nums))
        message = (
            f"🎯 今彩 539 預測 ({datetime.now().strftime('%m/%d')})\n"
            f"📈 數據統計至：{latest_date}\n"
            f"✨ 推薦熱門號：{formatted_nums}\n\n"
            f"💡 說明：取近 60 期頻率最高之號碼。"
        )
    else:
        message = "❌ 無法生成預測。"

    print(message)
    send_line_msg(message)

if __name__ == "__main__":
    main()
