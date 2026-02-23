import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
import os
from datetime import datetime

# 載入環境變數 (在 GitHub Actions 中會直接從 secrets 讀取)
# from dotenv import load_dotenv
# load_dotenv()

# Supabase 連線資訊
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL and Key must be set as environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def loto539_scrape(p: int) -> list:
    """
    從指定頁面爬取大樂透 539 的開獎號碼。
    Args:
        p (int): 頁碼。
    Returns:
        list: 包含開獎日期的列表，每個元素是一個包含 [日期, n1, n2, n3, n4, n5] 的列表。
    """
    rows = []
    url = f"https://www.lotto-8.com/listlto539.asp?indexpage={p}&orderby=new"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status() # 檢查 HTTP 請求是否成功
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")
        tds = soup.find_all("td")

        i = 0
        while i < len(tds) - 5:
            date_str = tds[i].text.strip()
            if "/" in date_str:
                # 修復：把多餘換行、空白都清掉，只留第一行日期
                date_str = date_str.split("\n")[0].strip()
                try:
                    # 將民國年轉換為西元年，並格式化為 YYYY-MM-DD
                    # 網站日期格式為 112/02/23 (民國年)
                    year_roc, month, day = map(int, date_str.split('/'))
                    year_ad = year_roc + 1911
                    formatted_date = f"{year_ad:04d}-{month:02d}-{day:02d}"

                    n1 = int(tds[i+1].text.strip())
                    n2 = int(tds[i+2].text.strip())
                    n3 = int(tds[i+3].text.strip())
                    n4 = int(tds[i+4].text.strip())
                    n5 = int(tds[i+5].text.strip())

                    rows.append({
                        "draw_date": formatted_date,
                        "n1": n1,
                        "n2": n2,
                        "n3": n3,
                        "n4": n4,
                        "n5": n5
                    })
                    i += 6
                except ValueError as e:
                    print(f"Skipping malformed data at index {i}: {date_str}, Error: {e}")
                    i += 1 # 跳過此行，繼續處理下一行
            else:
                i += 1
    except requests.exceptions.RequestException as e:
        print(f"Error during web request: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return rows

def get_existing_dates_from_db() -> set:
    """
    從 Supabase 資料庫中獲取所有已存在的開獎日期。
    Returns:
        set: 包含所有已存在日期的集合 (YYYY-MM-DD 格式)。
    """
    try:
        response = supabase.from_('lotto539_data').select('draw_date').execute()
        if response.data:
            return {row['draw_date'] for row in response.data}
    except Exception as e:
        print(f"Error fetching existing dates from Supabase: {e}")
    return set()

def insert_new_data_to_db(new_data: list):
    """
    將新的樂透數據插入到 Supabase 資料庫中。
    Args:
        new_data (list): 包含要插入數據的列表。
    """
    if not new_data:
        print("No new data to insert.")
        return

    try:
        response = supabase.from_('lotto539_data').insert(new_data).execute()
        if response.data:
            print(f"Successfully inserted {len(response.data)} new records.")
        elif response.count is not None:
            print(f"Successfully inserted {response.count} new records.")
        else:
            print("Insert operation completed, but no data returned in response.")
    except Exception as e:
        print(f"Error inserting data into Supabase: {e}")

def main():
    print("Starting lottery data scraping and update...")
    all_scraped_rows = []
    # 抓取多頁，可以根據需求調整頁數
    # 網站大約每頁有 10 筆資料，抓取 190 頁約 1900 筆資料，足夠應付日常更新
    for page in range(1, 10): # 為了快速測試，先抓取少量頁面，實際部署可增加頁數
        print(f"Scraping page {page}...")
        all_scraped_rows.extend(loto539_scrape(page))

    existing_dates = get_existing_dates_from_db()
    print(f"Found {len(existing_dates)} existing records in database.")

    new_records_to_insert = []
    for row in all_scraped_rows:
        if row['draw_date'] not in existing_dates:
            new_records_to_insert.append(row)

    if new_records_to_insert:
        # 按照日期排序，確保插入順序，避免潛在的資料庫衝突或邏輯問題
        new_records_to_insert.sort(key=lambda x: x['draw_date'])
        print(f"Found {len(new_records_to_insert)} new records to insert.")
        insert_new_data_to_db(new_records_to_insert)
    else:
        print("No new lottery data found to update.")
    print("Lottery data scraping and update finished.")

if __name__ == "__main__":
    main()