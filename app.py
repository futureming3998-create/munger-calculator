import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math

# --- 1. 基础配置 ---
st.set_page_config(page_title="Munger Analysis", layout="wide")
st.title("📈 芒格“价值线”分析仪")

# --- 2. 核心抓取引擎 (严格对齐官方文档) ---
@st.cache_data(ttl=3600)
def fetch_data_official(symbol, api_key):
    try:
        # A. 获取价格 (URL 直接传参模式，这是最稳的)
        price_url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?adjusted=true&apiKey={api_key}"
        p_data = requests.get(price_url).json()
        
        if 'results' not in p_data:
            return "API限额(每分5次)或代码错误"
        price = p_data['results'][0]['c']

        # B. 获取财报
        f_url = f"https://api.polygon.io/X/reference/financials?ticker={symbol}&timeframe=annual&limit=5&apiKey={api_key}"
        f_data = requests.get(f_url).json().get('results', [])
        
        history = []
        for r in f_data:
            try:
                # 穿透 Polygon 复杂的财务嵌套结构
                val = r['financials']['income_statement']['net_income_loss']['value']
                year = r.get('fiscal_year') or r.get('calendar_year')
                if val is not None and year is not None:
                    history.append({'v': float(val), 'y': int(year)})
            except: continue
        
        if len(history) < 2: return "该股财报数据不全"
        
        # 计算 CAGR         history.sort(key=lambda x: x['y'])
        n = history[-1]['y'] - history[0]['y'] or 1
        growth = (history[-1]['v'] / history[0]['v'])**(1/n) - 1 if history[0]['v'] > 0 else 0
        
        # PE 计算
        eps = f_data[0]['financials']['income_statement']['basic_earnings_per_share']['value']
        pe = price / eps if eps > 0 else 0
        
        # 10年价格曲线
        h_url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/2016-01-01/2026-12-31?apiKey={api_key}"
        h_data = requests.get(h_url).json().get('results', [])

        return {"price": price, "pe": pe, "growth": growth, "history": h_data}
    except Exception as e:
        return f"连接中断: {str(e)}"

# --- 3. 侧边栏 ---
with st.sidebar:
    ticker = st.text_input("输入代码 (AAPL/COST)", "AAPL").strip().upper()
    target_pe = st.slider("目标合理 P/E", 10, 50, 20)
    st.markdown("---")
    st.write("☕ 请作者喝杯咖啡")

# --- 4. 主逻辑渲染 ---
key = st.secrets.get("POLY_KEY")

if not key:
    st.error("🔑 部署错误：请在 Streamlit 后台 Secrets 配置 POLY_KEY")
elif ticker:
    with st.spinner('同步数据中...'):
        res = fetch_data_official(ticker, key)
    
    if isinstance(res, str):
        st.warning(f"💡 {res}")
    else:
        # 指标看板
        c1, c2, c3 = st.columns(3)
        c1.metric("当前价格", f"${res['price']:.2f}")
        c2.metric("P/E (TTM)", f"{res['pe']:.2f}")
        c3.metric("年化增速", f"{res['growth']*100:.2f}%")

        # 诊断
        if res['growth'] > 0 and res['pe'] > target_pe:
            y = math.log(res['pe'] / target_pe) / math.log(1 + res['growth'])
            st.warning(f"⚠️ 诊断：回归合理估值约需 {y:.2f} 年")
        elif res['pe'] <= target_pe:
            st.success("🌟 当前估值具备吸引力")

        # 图表
        if res['history']:
            df = pd.DataFrame(res['history'])
            df['date'] = pd.to_datetime(df['t'], unit='ms')
            fig = go.Figure(go.Scatter(x=df['date'], y=df['c'], name="Price"))
            fig.update_layout(yaxis_type="log", template="plotly_white", height=450)
            st.plotly_chart(fig, use_container_width=True)

st.caption("Munger Multiplier | Official Data Mode | 2026")
