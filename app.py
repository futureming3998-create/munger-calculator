import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math

# --- 1. 页面设置 ---
st.set_page_config(page_title="Munger Analysis", layout="wide")
st.title("📈 芒格“价值线”深度分析仪")

# --- 2. 侧边栏 ---
with st.sidebar:
    ticker = st.text_input("输入代码 (如 AAPL)", "AAPL").upper().strip()
    target_pe = st.slider("目标合理 P/E", 10.0, 50.0, 20.0)
    st.markdown("---")
    st.caption("提示：若提示 TICKER_NOT_FOUND，请检查 Key 或稍后刷新。")

# --- 3. 核心抓取函数 (完全对齐 Polygon 官方最简示例) ---
@st.cache_data(ttl=600)
def fetch_data_simple(symbol, api_key):
    try:
        # A. 抓取价格 (使用最原始的 URL 拼接)
        price_url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?adjusted=true&apiKey={api_key}"
        p_data = requests.get(price_url).json()
        
        if 'results' not in p_data or not p_data['results']:
            return "TICKER_NOT_FOUND"
        price = p_data['results'][0]['c']

        # B. 抓取财报 (仅取一份最新数据计算 PE，确保能跑通)
        f_url = f"https://api.polygon.io/X/reference/financials?ticker={symbol}&timeframe=annual&limit=1&apiKey={api_key}"
        f_data = requests.get(f_url).json().get('results', [])
        
        if not f_data:
            return "FINANCIALS_NOT_FOUND"
        
        # 严格按照官方最新 JSON 结构定位
        income_stmt = f_data[0]['financials']['income_statement']
        eps = income_stmt.get('basic_earnings_per_share', {}).get('value', 0)
        net_income = income_stmt.get('net_income_loss', {}).get('value', 0)
        
        # 计算当前 PE
        pe = price / eps if eps > 0 else 0

        # C. 历史 10 年价格轨迹
        h_url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/2016-01-01/2026-12-31?apiKey={api_key}"
        h_results = requests.get(h_url).json().get('results', [])

        return {"price": price, "pe": pe, "history": h_results, "net_income": net_income}
    except Exception as e:
        return f"ERROR: {str(e)}"

# --- 4. 渲染逻辑 ---
key = st.secrets.get("POLY_KEY")

if not key:
    st.error("🔑 Secrets 中未配置 POLY_KEY")
elif ticker:
    with st.spinner('正在同步官方数据...'):
        res = fetch_data_simple(ticker, key)
    
    if isinstance(res, str):
        st.warning(f"⚠️ {res}")
    else:
        # 显示核心看板
        c1, c2, c3 = st.columns(3)
        c1.metric("当前价格", f"${res['price']:.2f}")
        c2.metric("当前 P/E (TTM)", f"{res['pe']:.2f}")
        c3.metric("最新年度利润", f"${res['net_income']/1e9:.2f}B")

        # 估值逻辑 (简版)
        if res['pe'] > 0:
            if res['pe'] <= target_pe:
                st.success("🌟 估值低于目标，具备吸引力")
            else:
                st.info(f"💡 当前 P/E ({res['pe']:.1f}) 高于目标 ({target_pe})")

        # 绘制 10 年对数曲线图
        if res['history']:
            st.subheader(f"📊 {ticker} 10年对数增长轨迹")
            df = pd.DataFrame(res['history'])
            df['date'] = pd.to_datetime(df['t'], unit='ms')
            fig = go.Figure(go.Scatter(x=df['date'], y=df['c'], name="Price", line=dict(color='#1f77b4')))
            fig.update_layout(yaxis_type="log", template="plotly_white", height=500)
            st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption("Munger Multiplier | Official Data Mode | 2026")
