import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd
from datetime import datetime

# 載入環境變數 (在 Streamlit Cloud 中需設定為 Secrets)
# from dotenv import load_dotenv
# load_dotenv()

# Supabase 連線資訊
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# 檢查環境變數是否設定
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase URL and Key must be set as environment variables.")
    st.stop()

# 初始化 Supabase 客戶端
@st.cache_resource
def init_supabase():
    """
    初始化 Supabase 客戶端並緩存。
    """
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()

@st.cache_data(ttl=3600) # 緩存數據 1 小時
def get_lotto_data():
    """
    從 Supabase 獲取所有樂透 539 開獎數據。
    """
    try:
        response = supabase.from_('lotto539_data') \
                           .select('*') \
                           .order('draw_date', desc=True) \
                           .execute()
        if response.data:
            df = pd.DataFrame(response.data)
            # 將日期欄位轉換為日期時間對象，以便排序和顯示
            df['draw_date'] = pd.to_datetime(df['draw_date'])
            # 確保按照日期降序排列
            df = df.sort_values(by='draw_date', ascending=False)
            return df
    except Exception as e:
        st.error(f"從 Supabase 獲取數據失敗: {e}")
    return pd.DataFrame()

st.set_page_config(page_title="大樂透 539 開獎查詢與預測", layout="wide")

st.title("💰 大樂透 539 開獎查詢與預測")
st.markdown("---")

# 顯示最新開獎數據
st.header("最新開獎數據")
data_df = get_lotto_data()

if not data_df.empty:
    st.dataframe(data_df.head(20).style.format({
        'draw_date': lambda x: x.strftime('%Y-%m-%d')
    }), use_container_width=True)

    st.markdown("--- ")

    # 數據統計與分析 (可擴展)
    st.header("數據統計")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("號碼出現頻率 (近 100 期)")
        recent_numbers = data_df.head(100)[['n1', 'n2', 'n3', 'n4', 'n5']].values.flatten()
        freq_df = pd.Series(recent_numbers).value_counts().reset_index()
        freq_df.columns = ['號碼', '出現次數']
        freq_df = freq_df.sort_values(by='出現次數', ascending=False)
        st.bar_chart(freq_df.set_index('號碼'))

    with col2:
        st.subheader("號碼分佈")
        # 簡單的號碼分佈直方圖
        st.hist_chart(pd.Series(data_df[['n1', 'n2', 'n3', 'n4', 'n5']].values.flatten()))

    st.markdown("--- ")

    # 預測功能 (與 GitHub Action 中的預測邏輯保持一致)
    st.header("預測號碼 (基於歷史頻率)")
    st.info("此預測基於最近開獎號碼的出現頻率，僅供參考，不保證中獎。")

    # 獲取最近數據進行預測
    recent_prediction_data = data_df.head(60)[['n1', 'n2', 'n3', 'n4', 'n5']].values.flatten()
    if len(recent_prediction_data) > 0:
        number_counts = pd.Series(recent_prediction_data).value_counts()
        # 獲取出現頻率最高的 5 個號碼
        # 如果有相同頻率，則取號碼較小的
        predicted_numbers_series = number_counts.sort_values(ascending=False).index.tolist()
        predicted_numbers = sorted(predicted_numbers_series[:5])

        st.success(f"預測號碼：{' '.join(map(str, predicted_numbers))}")
    else:
        st.warning("無法獲取足夠數據進行預測。")

else:
    st.warning("目前沒有可用的樂透數據。請稍後再試或檢查後台數據更新。")

st.markdown("--- ")
st.caption(f"數據最後更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")