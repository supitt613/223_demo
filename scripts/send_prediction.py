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
            # --- 這是您問的「要加在哪邊」的修正核心區塊 ---
            date_raw = tds[i].text.strip()
            
            # 使用 Regex 精確找尋 xxx/xx/xx 格式，無視前後雜訊
            match = re.search(r"(\d{2,3}/\d{1,2}/\d{1,2})", date_raw)
            
            if match:
                try:
                    date_clean = match.group(1)
                    parts = date_clean.split('/')
                    year_roc = int(parts[0])
                    month = int(parts[1])
                    day = int(parts[2])
                    
                    # 只有在月份日期合理時才轉換，避免 00-00 出現
                    if month > 0 and month <= 12 and day > 0 and day <= 31:
                        year_ad = year_roc + 1911
                        formatted_date = f"{year_ad:04d}-{month:02d}-{day:02d}"

                        # 提取號碼
                        n1 = int(tds[i+1].text.strip())
                        n2 = int(tds[i+2].text.strip())
                        n3 = int(tds[i+3].text.strip())
                        n4 = int(tds[i+4].text.strip())
                        n5 = int(tds[i+5].text.strip())

                        rows.append({
                            "draw_date": formatted_date,
                            "n1": n1, "n2": n2, "n3": n3, "n4": n4, "n5": n5
                        })
                        i += 6 # 成功處理一組
                        continue
                except:
                    pass
            i += 1 # 如果沒對到日期格式，往後看一格
    except Exception as e:
        print(f"⚠️ 頁面 {p} 爬取失敗: {e}")
    return rows

def main():
    print(f"[{datetime.now()}] 啟動數據同步任務...")
    
    scraped_data = []
    # 掃描前 5 頁，確保 2/23 與之前的資料都能補齊
    for page in range(1, 6):
        print(f"🔍 正在掃描第 {page} 頁...")
        scraped_data.extend(loto539_scrape(page))

    if not scraped_data:
        print("🛑 未發現數據。")
        return

    # 確保按日期排序
    scraped_data.sort(key=lambda x: x['draw_date'])
    
    try:
        # 使用 upsert，重複日期會自動更新，不重複會新增
        supabase.table('lotto539_data').upsert(
            scraped_data, 
            on_conflict="draw_date"
        ).execute()
        
        print(f"✅ 同步成功！最新一筆日期：{scraped_data[-1]['draw_date']}")
    except Exception as e:
        print(f"❌ 寫入失敗: {e}")

if __name__ == "__main__":
    main()
