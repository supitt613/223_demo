import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
import os
from datetime import datetime
import re

# --- 1. 配置與初始化 ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ 錯誤：請確保已在 GitHub Secrets 設定環境變數")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def loto539_scrape(p: int) -> list:
    rows = []
    url = f"https://www.lotto-8.com/listlto539.asp?indexpage={p}&orderby=new"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")
        tds = soup.find_all("td")

        i = 0
        while i < len(tds) - 5:
            raw_text = tds[i].text.strip()
            # 使用正則表達式精確抓取日期格式 (xxx/xx/xx)
            date_match = re.search(r"(\d{2,3}/\d{2}/\d{2})", raw_text)
            
            if date_match:
                try:
                    date_str = date_match.group(1)
                    year_roc, month, day = map(int, date_str.split('/'))
                    year_ad = year_roc + 1911 # 115 -> 2026
                    formatted_date = f"{year_ad:04d}-{month:02d}-{day:02d}"

                    # 提取號碼
                    nums = [int(tds[i+j].text.strip()) for j in range(1, 6)]

                    rows.append({
                        "draw_date": formatted_date,
                        "n1": nums[0], "n2": nums[1], "n3": nums[2], "n4": nums[3], "n5": nums[4]
                    })
                    i += 6 
                except Exception as e:
                    i += 1
            else:
                i += 1
    except Exception as e:
        print(f"⚠️ 頁面 {p} 爬取失敗: {e}")
    return rows

def main():
    print(f"[{datetime.now()}] 啟動數據同步任務...")
    
    scraped_data = []
    # 掃描前 5 頁確保補足遺漏資料
    for page in range(1, 6):
        print(f"🔍 正在掃描第 {page} 頁...")
        scraped_data.extend(loto539_scrape(page))

    if not scraped_data:
        print("🛑 未發現任何數據。")
        return

    # 確保按日期排序
    scraped_data.sort(key=lambda x: x['draw_date'])
    
    try:
        # 使用 upsert 解決日期衝突問題
        supabase.table('lotto539_data').upsert(
            scraped_data, 
            on_conflict="draw_date"
        ).execute()
        
        print(f"✅ 同步成功！最新資料日期：{scraped_data[-1]['draw_date']}")
    except Exception as e:
        print(f"❌ 寫入失敗: {e}")

if __name__ == "__main__":
    main()
