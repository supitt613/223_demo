import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
import os
from datetime import datetime
import re

# --- 配置 ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def loto539_scrape(p: int) -> list:
    rows = []
    url = f"https://www.lotto-8.com/listlto539.asp?indexpage={p}&orderby=new"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")
        tds = soup.find_all("td")

        i = 0
        while i < len(tds) - 5:
            date_raw = tds[i].text.strip()
            # 1. 抓取日期格式 (可能包含 / 或 -)
            match = re.search(r"(\d{2,4}[/-]\d{1,2}[/-]\d{1,2})", date_raw)
            if match:
                try:
                    date_str = match.group(1).replace('-', '/')
                    parts = list(map(int, date_str.split('/')))
                    
                    year = parts[0]
                    # --- 核心防錯邏輯 ---
                    if year < 1000: # 代表是民國年 (例如 115)
                        year_ad = year + 1911
                    else:           # 代表已經是西元年 (例如 2026)
                        year_ad = year
                    
                    formatted_date = f"{year_ad:04d}-{parts[1]:02d}-{parts[2]:02d}"
                    
                    # 2. 抓取號碼 (確保是數字)
                    n_list = []
                    for j in range(1, 6):
                        val = tds[i+j].text.strip()
                        if val.isdigit():
                            n_list.append(int(val))
                    
                    if len(n_list) == 5:
                        rows.append({
                            "draw_date": formatted_date,
                            "n1": n_list[0], "n2": n_list[1], "n3": n_list[2], "n4": n_list[3], "n5": n_list[4]
                        })
                        i += 6 # 成功處理一組
                        continue
                except: pass
            i += 1
    except Exception as e:
        print(f"⚠️ 爬取錯誤: {e}")
    return rows

def main():
    print(f"[{datetime.now()}] 執行強效同步...")
    # 抓取第一頁即可
    scraped_data = loto539_scrape(1)

    if scraped_data:
        # 排序確保最新在後 (upsert 習慣)
        scraped_data.sort(key=lambda x: x['draw_date'])
        try:
            # 使用 upsert 並指定衝突欄位
            supabase.table('lotto539_data').upsert(scraped_data, on_conflict="draw_date").execute()
            print(f"✅ 同步成功！最新日期為: {scraped_data[-1]['draw_date']}")
        except Exception as e:
            print(f"❌ 寫入資料庫失敗: {e}")

if __name__ == "__main__":
    main()
