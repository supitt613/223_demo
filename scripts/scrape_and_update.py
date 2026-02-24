import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
import os
from datetime import datetime

# --- 1. 配置與初始化 ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ 錯誤：請確保已在 GitHub Secrets 設定 SUPABASE_URL 與 SUPABASE_KEY")

# 初始化 Supabase 客戶端
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def loto539_scrape(p: int) -> list:
    """
    從指定頁面爬取 539 數據，並進行強健的日期轉換。
    """
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
            date_raw = tds[i].text.strip()
            # 過濾包含斜線的日期字串
            if "/" in date_raw:
                try:
                    # 處理可能帶有換行符號的日期 (例如 115/02/23 \n 星期一)
                    date_str = date_raw.split()[0].strip()
                    year_roc, month, day = map(int, date_str.split('/'))
                    year_ad = year_roc + 1911 # 民國轉西元
                    formatted_date = f"{year_ad:04d}-{month:02d}-{day:02d}"

                    # 提取號碼
                    nums = [int(tds[i+j].text.strip()) for j in range(1, 6)]

                    rows.append({
                        "draw_date": formatted_date,
                        "n1": nums[0], "n2": nums[1], "n3": nums[2], "n4": nums[3], "n5": nums[4]
                    })
                    i += 6 # 成功處理一組，跳 6 格
                except:
                    i += 1
            else:
                i += 1
    except Exception as e:
        print(f"⚠️ 頁面 {p} 爬取失敗: {e}")
    return rows

def main():
    print(f"[{datetime.now()}] 啟動數據同步任務...")
    
    scraped_data = []
    # 策略：一次抓取前 3 頁，確保即使漏掉前幾天的資料也能補回來
    for page in range(1, 4):
        print(f"🔍 正在掃描第 {page} 頁...")
        data = loto539_scrape(page)
        scraped_data.extend(data)

    if not scraped_data:
        print("🛑 未發現任何數據，請檢查目標網站是否正常。")
        return

    # 按照日期排序
    scraped_data.sort(key=lambda x: x['draw_date'])
    
    print(f"📊 掃描完成，準備處理 {len(scraped_data)} 筆資料...")

    try:
        # --- 關鍵修正：改用 upsert ---
        # upsert 會根據 draw_date (Unique) 判斷，若重複則更新，不重複則新增。
        # 這能完美解決「同步」的問題。
        response = supabase.table('lotto539_data').upsert(
            scraped_data, 
            on_conflict="draw_date" # 確保根據日期來判斷衝突
        ).execute()
        
        print(f"✅ 同步成功！已確認最新資料庫狀態。")
        print(f"最新一筆日期為：{scraped_data[-1]['draw_date']}")
        
    except Exception as e:
        print(f"❌ 寫入 Supabase 失敗: {e}")

if __name__ == "__main__":
    main()
