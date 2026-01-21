import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Munger Analysis")
st.title("📈 芒格“价值线” (2年稳定版)")

# 侧边栏
ticker = st.sidebar.text_input("代码 (AAPL)", "AAPL").upper().strip()
api_key = st.secrets.get("POLY_KEY")

@st.cache_data(ttl=3600)
def fetch_basic_fixed(symbol, key):
    # 核心改变：只查最近 2 年的数据，严格遵守官方 Basic 计划限制
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/2024-01-01/2026-12-31?apiKey={key}"
    try:
        resp = requests.get(url).json()
        if resp.get("status") == "OK" and "results" in resp:
            return resp["results"]
        else:
            # 返回官方给出的具体错误原因
            return f"API拒绝: {resp.get('error', '原因未知')}. 提示：免费版仅支持2年内历史数据。"
    except Exception as e:
        return f"请求失败: {str(e)}"

if api_key and ticker:
    data = fetch_basic_fixed(ticker, api_key)
    if isinstance(data, str):
        st.error(data)
    else:
        st.success(f"✅ 已成功获取 {ticker} 过去 2 年的数据")
        df = pd.DataFrame(data)
        st.line_chart(df.set_index(pd.to_datetime(df['t'], unit='ms'))['c'])
