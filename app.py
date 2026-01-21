import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
import requests

# --- 1. 页面配置与 CSS 样式 ---
st.set_page_config(page_title="Munger Value Pro", layout="wide")

# 强制对齐样式：包含指标卡片、侧边栏打赏、以及底部说明的样式
st.markdown('''
    <style>
    .stMetric { background: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    .coffee-btn { display: block; width: 100%; border-radius: 10px; overflow: hidden; margin-top: 10px; transition: transform 0.3s; }
    .coffee-btn:hover { transform: scale(1.02); }
    .footer-text { text-align: center; color: #666; padding: 20px; font-size: 0.8rem; border-top: 1px solid #333; margin-top: 50px; }
    </style>
''', unsafe_allow_html=True)

# --- 2. 语言字典配置 ---
LANG = {
    "中文": {
        "title": "📈 芒格“价值线”深度分析仪",
        "welcome": "👋 欢迎！请在左侧输入股票代码开始分析。",
        "guide_h": "### 📖 快速上手指南：",
        "guide_1": "1. **真实数据**：由 Polygon.io 提供官方财报数据。",
        "guide_2": "2. **5年CAGR**：系统自动计算过去5年的平滑复合增长率。",
        "guide_3": "3. **对数曲线**：10年股价走势，一眼看清复利斜率。",
        "sb_cfg": "🔍 配置中心",
        "ticker_label": "输入美股代码 (如 COST, AAPL)",
        "target_pe": "目标合理 P/E",
        "metric_price": "当前股价",
        "metric_pe": "真实 P/E (TTM)",
        "metric_growth": "5年复合利润增速 (CAGR)",
        "diag_years": "⚠️ 诊断：回归合理估值约需 **{:.2f}** 年",
        "diag_gold": "🌟 诊断：当前估值已具备极大吸引力",
        "err_data": "🚫 无法分析：财报数据不足（需至少2年历史）或 API 频率超限。",
        "coffee": "☕ 请作者喝杯咖啡",
        "footer": "Munger Multiplier Tool | Official Real-Data Mode | 2026"
    },
    "English": {
        "title": "📈 Munger Value Line Pro",
        "welcome": "👋 Welcome! Enter a ticker on the left.",
        "guide_h": "### 📖 Quick Start:",
        "guide_1": "1. **Real Data**: Official financials via Polygon.io.",
        "guide_2": "2. **5Y CAGR**: Smoothed compound growth rate over 5 years.",
        "guide_3": "3. **Log Chart**: 10Y price history on log scale.",
        "sb_cfg": "🔍 Configuration",
        "ticker_label": "Enter Ticker (e.g. AAPL, COST)",
        "target_pe": "Target P/E Ratio",
        "metric_price": "Price",
        "metric_pe": "Real P/E (TTM)",
        "metric_growth": "5Y Profit CAGR",
        "diag_years": "⚠️ Diagnosis: ~**{:.2f}** years to target",
        "diag_gold": "🌟 Diagnosis: Highly Attractive",
        "err_data": "🚫 Error: Insufficient financial data or rate limit reached.",
        "coffee": "☕ Buy me a coffee",
        "footer": "Munger Multiplier Tool | Official Real-Data Mode | 2026"
    }
}

# --- 3. 顶部布局 (语言切换归位) ---
top_col1, top_col2 = st.columns([7, 1.2])
with top_col2:
    sel_lang = st.selectbox("", ["中文", "English"], label_visibility="collapsed")
    t = LANG[sel_lang]

with top_col1:
    st.title(t["title"])

# --- 4. 核心引擎：CAGR 算法 ---
@st.cache_data(ttl=3600)
def fetch_munger_data(symbol):
    try:
        api_key = st.secrets["POLY_KEY"]
        # 获取价格
        p_url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?apiKey={api_key}"
        p_res = requests.get(p_url).json()
        price = p_res['results'][0]['c']
        # 获取5年年度财报
        f_url = f"https://api.polygon.io/X/reference/financials?ticker={symbol}&timeframe=annual&limit=5&apiKey={api_key}"
        f_res = requests.get(f_url).json()['results']
        
        if len(f_res) < 2: return None
        
        # 计算 PE
        eps = f_res[0]['financials']['income_statement']['basic_earnings_per_share']['value']
        pe = price / eps if eps > 0 else 0
        
        # 计算 CAGR 
        n = len(f_res) - 1
        end_p = f_res[0]['financials']['income_statement']['net_income_loss']['value']
        start_p = f_res[-1]['financials']['income_statement']['net_income_loss']['value']
        
        if end_p > 0 and start_p > 0:
            growth = (end_p / start_p)**(1/n) - 1
        else:
            # 兼容亏损转盈或持续亏损的情况，使用线性增速
            growth = (end_p - start_p)/abs(start_p)
        
        # 获取10年历史数据 (用于画对数图)
        h_url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/2016-01-01/2026-12-31?apiKey={api_key}"
        h_res = requests.get(h_url).json()['results']
        
        return {"price": price, "pe": pe, "growth": growth, "history": pd.DataFrame(h_res), "n": n+1}
    except:
        return None

# --- 5. 侧边栏布局 ---
with st.sidebar:
    st.header(t["sb_cfg"])
    ticker = st.text_input(t["ticker_label"], "").strip().upper()
    target_pe_val = st.slider(t["target_pe"], 10.0, 50.0, 20.0)
    st.markdown("---")
    st.subheader(t["coffee"])
    # 侧边栏打赏按钮
    st.markdown('<a href="https://www.buymeacoffee.com/vcalculator" target="_blank" class="coffee-btn"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" width="100%"></a>', unsafe_allow_html=True)

# --- 6. 主逻辑与视图渲染 ---
if not ticker:
    st.info(t["welcome"])
    st.markdown(t["guide_h"])
    st.write(t["guide_1"]); st.write(t["guide_2"]); st.write(t["guide_3"])
else:
    with st.spinner('正在调取 Polygon.io 官方财报...'):
        data = fetch_munger_data(ticker)
    
    if data and data['pe'] > 0:
        # 1. 顶部指标卡
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t["metric_price"], f"${data['price']:.2f}")
        c2.metric(t["metric_pe"], f"{data['pe']:.2f}")
        c3.metric(t["metric_growth"], f"{data['growth']*100:.2f}%", help=f"基于{data['n']}年历史利润计算的复合年化增长率")
        c4.metric(t["target_pe"], f"{target_pe_val}")

        # 2. 诊断结论
        if data['growth'] > 0:
            if data['pe'] <= target_pe_val:
                st.success(t["diag_gold"])
            else:
                y = math.log(data['pe'] / target_pe_val) / math.log(1 + data['growth'])
                st.warning(t["diag_years"].format(y))
        else:
            st.error("⚠️ 该公司长期利润增速为负，不符合芒格复利回归模型。")
        
        # 3. 历史对数轨迹图
        st.subheader(f"📊 {ticker} 10年价格轨迹 (对数刻度)")
        df_h = data['history']
        df_h['t'] = pd.to_datetime(df_h['t'], unit='ms')
        fig = go.Figure(go.Scatter(x=df_h['t'], y=df_h['c'], line=dict(color='#1f77b4', width=2)))
        fig.update_layout(yaxis_type="log", template="plotly_white", height=450, margin=dict(l=0,r=0,t=20,b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(t["err_data"])

# --- 7. 底部说明栏 (Footer) ---
st.markdown(f'<div class="footer-text">{t["footer"]}</div>', unsafe_allow_html=True)
