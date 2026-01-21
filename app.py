import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
import requests

# --- 1. 样式与配置 ---
st.set_page_config(page_title="Munger Value Pro", layout="wide")
st.markdown('''
    <style>
    .stMetric { background: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    .coffee-btn { display: block; width: 100%; border-radius: 10px; overflow: hidden; margin-top: 10px; transition: transform 0.3s; }
    .coffee-btn:hover { transform: scale(1.02); }
    .footer-text { text-align: center; color: #666; padding: 20px; font-size: 0.8rem; border-top: 1px solid #333; margin-top: 50px; }
    </style>
''', unsafe_allow_html=True)

# --- 2. 语言包 ---
LANG = {
    "中文": {
        "title": "📈 芒格“价值线”深度分析仪",
        "welcome": "👋 欢迎！请在左侧输入代码开始分析。",
        "guide_h": "### 📖 快速上手指南：",
        "guide_1": "1. **数据源**：由 Polygon.io 提供官方原始财报。",
        "guide_2": "2. **5年CAGR**：计算5年复合增速，平滑利润波动。",
        "guide_3": "3. **对数曲线**：10年价格轨迹，看清复利斜率。",
        "sb_cfg": "🔍 配置中心",
        "ticker_label": "输入美股代码 (如 AAPL, COST)",
        "target_pe": "目标合理 P/E",
        "metric_price": "当前股价",
        "metric_pe": "真实 P/E (TTM)",
        "metric_growth": "5年复合增速 (CAGR)",
        "diag_years": "⚠️ 诊断：回归合理估值约需 **{:.2f}** 年",
        "diag_gold": "🌟 诊断：当前估值极具吸引力",
        "err_data": "🚫 错误：API限额(每分5次)或财报不全。",
        "coffee": "☕ 请作者喝杯咖啡",
        "footer": "Munger Analysis Tool | Polygon.io Real-Data | 2026"
    },
    "English": {
        "title": "📈 Munger Value Line Pro",
        "welcome": "👋 Welcome! Enter a ticker on the left.",
        "guide_h": "### 📖 Quick Start:",
        "guide_1": "1. **Data Source**: Official Polygon.io API.",
        "guide_2": "2. **5Y CAGR**: Smoothed profit growth rate.",
        "guide_3": "3. **Log Chart**: 10Y compounding trajectory.",
        "sb_cfg": "🔍 Configuration",
        "ticker_label": "Enter Ticker (e.g. AAPL, COST)",
        "target_pe": "Target P/E Ratio",
        "metric_price": "Price",
        "metric_pe": "Real P/E (TTM)",
        "metric_growth": "5Y CAGR",
        "diag_years": "⚠️ Diagnosis: ~**{:.2f}** years to target",
        "diag_gold": "🌟 Diagnosis: Highly Attractive",
        "err_data": "🚫 Error: API rate limit or missing data.",
        "coffee": "☕ Buy me a coffee",
        "footer": "Munger Analysis Tool | Polygon.io Real-Data | 2026"
    }
}

top_col1, top_col2 = st.columns([7, 1.2])
with top_col2:
    sel_lang = st.selectbox("", ["中文", "English"], label_visibility="collapsed")
    t = LANG[sel_lang]
with top_col1:
    st.title(t["title"])

# --- 3. 数据抓取与 CAGR 计算 ---
@st.cache_data(ttl=3600)
def fetch_data(symbol, api_key):
    try:
        # 1. 价格
        p_res = requests.get(f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?apiKey={api_key}").json()
        price = p_res['results'][0]['c']
        # 2. 财报 (取5份年度财报)
        f_res = requests.get(f"https://api.polygon.io/X/reference/financials?ticker={symbol}&timeframe=annual&limit=5&apiKey={api_key}").json()['results']
        if len(f_res) < 2: return None
        # PE 计算
        eps = f_res[0]['financials']['income_statement']['basic_earnings_per_share']['value']
        pe = price / eps if eps > 0 else 0
        # CAGR 计算
        n = len(f_res) - 1
        v_final = f_res[0]['financials']['income_statement']['net_income_loss']['value']
        v_start = f_res[-1]['financials']['income_statement']['net_income_loss']['value']
        growth = (v_final / v_start)**(1/n) - 1 if (v_final > 0 and v_start > 0) else (v_final - v_start)/abs(v_start)
        # 10年价格
        h_res = requests.get(f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/2016-01-01/2026-12-31?apiKey={api_key}").json()['results']
        return {"price": price, "pe": pe, "growth": growth, "history": pd.DataFrame(h_res), "n": n+1}
    except: return None

# --- 4. 侧边栏 ---
with st.sidebar:
    st.header(t["sb_cfg"])
    p_key = st.text_input("Polygon API Key", value=st.secrets.get("POLY_KEY", ""), type="password")
    ticker = st.text_input(t["ticker_label"], "").strip().upper()
    target_pe_val = st.slider(t["target_pe"], 10.0, 50.0, 20.0)
    st.markdown("---")
    st.subheader(t["coffee"])
    st.markdown('<a href="https://www.buymeacoffee.com/vcalculator" target="_blank" class="coffee-btn"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" width="100%"></a>', unsafe_allow_html=True)

# --- 5. 主视图 ---
if not ticker:
    st.info(t["welcome"])
    st.markdown(t["guide_h"])
    st.write(t["guide_1"]); st.write(t["guide_2"]); st.write(t["guide_3"])
elif not p_key:
    st.warning("🔑 请输入 Polygon API Key 以启动数据抓取。")
else:
    with st.spinner('正在分析财报趋势...'):
        data = fetch_data(ticker, p_key)
    if data and data['pe'] > 0:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t["metric_price"], f"${data['price']:.2f}")
        c2.metric(t["metric_pe"], f"{data['pe']:.2f}")
        c3.metric(t["metric_growth"], f"{data['growth']*100:.2f}%", help=f"基于{data['n']}年利润计算")
        c4.metric(t["target_pe"], f"{target_pe_val}")
        if data['growth'] > 0:
            if data['pe'] <= target_pe_val: st.success(t["diag_gold"])
            else:
                y = math.log(data['pe'] / target_pe_val) / math.log(1 + data['growth'])
                st.warning(t["diag_years"].format(y))
        else: st.error("⚠️ 利润增速为负，不适用此模型。")
        st.subheader(f"📊 {ticker} 10Y Price Trajectory (Log)")
        df_h = data['history']
        df_h['t'] = pd.to_datetime(df_h['t'], unit='ms')
        fig = go.Figure(go.Scatter(x=df_h['t'], y=df_h['c'], line=dict(color='#1f77b4', width=2)))
        fig.update_layout(yaxis_type="log", template="plotly_white", height=450, margin=dict(l=0,r=0,t=20,b=0))
        st.plotly_chart(fig, use_container_width=True)
    else: st.error(t["err_data"])

st.markdown(f'<div class="footer-text">{t["footer"]}</div>', unsafe_allow_html=True)
