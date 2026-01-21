import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math

st.set_page_config(page_title="Munger Analysis Pro", layout="wide")
st.title("📈 芒格“价值线”分析仪 (稳定版)")

# --- 核心抓取函数：采用多重兜底逻辑 ---
@st.cache_data(ttl=600)
def fetch_data_robust(symbol, api_key):
    try:
        # 1. 获取股票基础信息 (验证代码是否存在)
        meta_url = f"https://api.polygon.io/v3/reference/tickers/{symbol}?apiKey={api_key}"
        meta_res = requests.get(meta_url).json()
        if meta_res.get('status') != 'OK':
            return "CODE_INVALID"
        
        # 2. 获取价格 (改用 Snapshot 接口，它聚合了最新交易数据，比 prev 更稳)
        price_url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}?apiKey={api_key}"
        p_res = requests.get(price_url).json()
        if 'ticker' not in p_res:
            return "PRICE_ERROR"
        price = p_res['ticker']['day']['c']

        # 3. 获取财报 (只拿 1 份计算 PE，确保不触发次数限制)
        f_url = f"https://api.polygon.io/X/reference/financials?ticker={symbol}&timeframe=annual&limit=1&apiKey={api_key}"
        f_res = requests.get(f_url).json().get('results', [])
        if not f_res:
            return "NO_FINANCIALS"
        
        income_stmt = f_res[0]['financials']['income_statement']
        eps = income_stmt.get('basic_earnings_per_share', {}).get('value', 0)
        net_inc = income_stmt.get('net_income_loss', {}).get('value', 0)

        # 4. 获取历史轨迹 (2年，这是免费版确定的限制范围)
        h_url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/2024-01-01/2026-12-31?apiKey={api_key}"
        h_res = requests.get(h_url).json().get('results', [])

        return {
            "name": meta_res['results']['name'],
            "price": price,
            "pe": price / eps if eps > 0 else 0,
            "net_inc": net_inc,
            "history": h_res
        }
    except Exception as e:
        return f"ERROR: {str(e)}"

# --- 界面展示 ---
ticker = st.sidebar.text_input("代码", "AAPL").upper().strip()
target_pe = st.sidebar.slider("目标 P/E", 10.0, 50.0, 20.0)
api_key = st.secrets.get("POLY_KEY")

if ticker and api_key:
    with st.spinner('调取官方数据中...'):
        data = fetch_data_robust(ticker, api_key)
    
    if isinstance(data, str):
        st.error(f"⚠️ {data}")
    else:
        st.subheader(f"✅ {data['name']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("价格", f"${data['price']:.2f}")
        c2.metric("P/E (TTM)", f"{data['pe']:.2f}")
        c3.metric("净利润 (最新)", f"${data['net_inc']/1e9:.2f}B")

        if data['history']:
            df = pd.DataFrame(data['history'])
            df['date'] = pd.to_datetime(df['t'], unit='ms')
            fig = go.Figure(go.Scatter(x=df['date'], y=df['c'], name="Price"))
            fig.update_layout(yaxis_type="log", template="plotly_white", height=400)
            st.plotly_chart(fig, use_container_width=True)
