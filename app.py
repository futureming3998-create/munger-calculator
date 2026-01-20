import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import math
import time

# 1. 多语言配置
LANG = {
    "中文": {
        "title": "📈 芒格“价值线”分析仪 2.0",
        "sidebar_cfg": "🔍 配置中心",
        "input_label": "输入股票代码 (如 600519.SS / AAPL)",
        "metric_price": "当前股价",
        "metric_pe": "当前 P/E (TTM)",
        "metric_growth": "核心利润增速",
        "metric_target": "目标 P/E",
        "diag_years_msg": "回归年数为 **{:.2f}** 年。",
        "err_no_data": "🚫 无法解析该股财务报表，请确认代码是否正确。"
    },
    "English": {
        "title": "📈 Munger Value Line 2.0",
        "sidebar_cfg": "🔍 Configuration",
        "input_label": "Enter Ticker (e.g., AAPL / 000001.SZ)",
        "metric_price": "Price",
        "metric_pe": "Current P/E",
        "metric_growth": "Earnings Growth",
        "metric_target": "Target P/E",
        "diag_years_msg": "Payback years: **{:.2f}**.",
        "err_no_data": "🚫 Financials unavailable for this ticker."
    }
}

st.set_page_config(page_title="Munger Analysis", layout="wide")

# 主题美化：直接注入 CSS 让控件变黄
st.markdown("""
    <style>
    .stSlider > div > div > div > div { background: #FFC107 !important; }
    .stTextInput > div > div > input { border-color: #FFC107 !important; }
    </style>
""", unsafe_allow_html=True)

# 语言切换
sel_lang = st.sidebar.selectbox("Language", ["中文", "English"])
t = LANG[sel_lang]
st.title(t["title"])

# 侧边栏
with st.sidebar:
    st.header(t["sidebar_cfg"])
    ticker_input = st.text_input(t["input_label"], "").upper()
    target_pe = st.slider(t["metric_target"], 10.0, 40.0, 20.0)
    
    st.markdown("---")
    st.markdown(f'<a href="https://www.buymeacoffee.com/vcalculator" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" style="height: 40px;"></a>', unsafe_allow_html=True)

# 核心引擎
@st.cache_data(ttl=3600)
def get_pro_data(ticker):
    try:
        tk = yf.Ticker(ticker)
        inf = tk.info
        
        # 1. 价格修复逻辑 [cite: 2026-01-05]
        price = inf.get('currentPrice') or inf.get('regularMarketPreviousClose') or 0.0
        
        # 2. 针对 A 股的财务报表深度分析 [cite: 2026-01-05]
        pe = inf.get('trailingPE')
        growth = inf.get('earningsGrowth')
        
        # 如果 info 缺失（A股常见），直接分析利润表
        if not pe or not growth:
            fin = tk.financials
            if not fin.empty:
                # 计算 PE: 市值 / 净利润
                net_income = fin.loc['Net Income'].iloc[0]
                m_cap = inf.get('marketCap')
                if not pe and m_cap and net_income > 0:
                    pe = m_cap / net_income
                # 计算增速: (今年-去年)/去年
                if not growth and len(fin.loc['Net Income']) > 1:
                    growth = (fin.loc['Net Income'].iloc[0] - fin.loc['Net Income'].iloc[1]) / abs(fin.loc['Net Income'].iloc[1])

        if pe and growth:
            return {'pe': float(pe), 'growth': float(growth), 'price': float(price), 'name': inf.get('longName', ticker)}
        return None
    except:
        return None

# 运行渲染
if ticker_input:
    data = get_pro_data(ticker_input)
    if data:
        # 显示指标
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t["metric_price"], f"${data['price']:.2f}")
        c2.metric(t["metric_pe"], f"{data['pe']:.2f}")
        c3.metric(t["metric_growth"], f"{data['growth']*100:.1f}%")
        c4.metric(t["metric_target"], f"{target_pe}")

        # 计算回归年数
        if data['growth'] > 0:
            pe_r = data['pe'] / target_pe
            years = math.log(pe_r) / math.log(1 + data['growth']) if pe_r > 1 else 0
            st.success(t["diag_years_msg"].format(years))
            
            # 绘图（黄色风格） [cite: 2026-01-05]
            hist = yf.download(ticker_input, period="5y")
            if not hist.empty:
                fig = go.Figure(go.Scatter(x=hist.index, y=hist['Close'].iloc[:,0] if len(hist['Close'].shape)>1 else hist['Close'], line=dict(color='#FFC107')))
                fig.update_layout(yaxis_type="log", template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(t["err_no_data"])
