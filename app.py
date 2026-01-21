import streamlit as st
import akshare as ak
import pandas as pd
import plotly.graph_objects as go
import math
import requests

# --- 1. 语言包与基础配置 ---
LANG_DICT = {
    "中文": {
        "title": "📈 芒格“价值线”复利回归分析仪",
        "welcome": "👋 **欢迎！请在左侧输入股票代码开始分析。**",
        "guide": "### 📖 快速上手指南：\n1. **输入代码**：A股(600519), 美股(NFLX)。\n2. **设定目标**：调整侧边栏合理 P/E 滑块。\n3. **查看结论**：下方自动计算回本年数与趋势图。",
        "sidebar_head": "🔍 配置中心",
        "input_hint": "输入股票代码 (如 AAPL, MSFT)",
        "target_pe": "目标合理市盈率 (P/E)",
        "m_price": "实时股价",
        "m_pe": "当前 P/E (TTM)",
        "m_growth": "预期利润增速",
        "m_target": "回本目标 P/E",
        "diag_years": "⚠️ 诊断：回归至合理目标约需 **{:.2f}** 年",
        "diag_gold": "🌟 诊断：当前估值极具吸引力（黄金坑）",
        "footer": "Munger Multiplier Tool | Powered by Gemini & Yahoo Finance",
        "err": "🚫 无法抓取数据。美股请使用大写字母 (如 NFLX)。"
    },
    "English": {
        "title": "📈 Munger Value Line Analysis Tool",
        "welcome": "👋 **Welcome! Enter a ticker on the left to start.**",
        "guide": "### 📖 Quick Start Guide:\n1. **Ticker**: US (NFLX), A-Share (600519).\n2. **Set Target**: Use slider for target P/E.\n3. **Analysis**: Check the years to reach target valuation.",
        "sidebar_head": "🔍 Configuration",
        "input_hint": "Enter Ticker (e.g., AAPL)",
        "target_pe": "Target P/E Ratio",
        "m_price": "Price",
        "m_pe": "P/E (TTM)",
        "m_growth": "Growth Rate",
        "m_target": "Target P/E",
        "diag_years": "⚠️ Diagnosis: Approx. **{:.2f}** years to target",
        "diag_gold": "🌟 Diagnosis: Highly Attractive",
        "footer": "Munger Multiplier Tool | Powered by Gemini & Yahoo Finance",
        "err": "🚫 Fetch failed. Please use uppercase for US stocks."
    }
}

st.set_page_config(page_title="Munger Pro", layout="wide")

# 侧边栏 CSS 修正
st.markdown('''
    <style>
    .coffee-btn { display: block; width: 100%; border-radius: 8px; overflow: hidden; margin-top: 15px; }
    .coffee-btn img { width: 100%; object-fit: contain; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem !important; }
    </style>
''', unsafe_allow_html=True)

# --- 2. 右上角语言切换器 ---
c_top1, c_top2 = st.columns([8, 1])
with c_top2:
    lang = st.selectbox("", ["中文", "English"], label_visibility="collapsed")
t = LANG_DICT[lang]

# --- 3. 侧边栏 ---
with st.sidebar:
    st.header(t["sidebar_head"])
    st.caption("⌨️ **代码输入指南**：\n• A股：600519\n• 美股：AAPL, NFLX")
    ticker = st.text_input(t["input_hint"], "").strip().upper()
    target_pe = st.slider(t["target_pe"], 10.0, 50.0, 20.0)
    
    st.markdown("---")
    st.subheader("☕ 请作者喝杯咖啡")
    st.markdown('<a href="https://www.buymeacoffee.com/vcalculator" target="_blank" class="coffee-btn"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"></a>', unsafe_allow_html=True)

# --- 4. 实时数据引擎 (无污染版) ---
def get_stock_data_final(ticker):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        # A股
        if ticker.isdigit() and len(ticker) == 6:
            df = ak.stock_zh_a_spot_em()
            row = df[df['代码'] == ticker].iloc[0]
            hist = ak.stock_zh_a_hist(symbol=ticker, period="daily", adjust="qfq").tail(250)
            hist.columns = ['Date','Open','Close','High','Low','Volume','Amount','Amplitude','Pct','Change','Turnover']
            hist['Date'] = pd.to_datetime(hist['Date'])
            return {"price": float(row['最新价']), "pe": float(row['市盈率TTM']), "growth": 0.12, "name": row['名称'], "history": hist}
        
        # 美股 (确保 NFLX 与 COST 数据差异)
        elif ticker.isalpha():
            c_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1y"
            c_res = requests.get(c_url, headers=headers, timeout=10).json()['chart']['result'][0]
            price = float(c_res['meta']['regularMarketPrice'])
            hist_df = pd.DataFrame({'Date': pd.to_datetime(c_res['timestamp'], unit='s'), 'Close': c_res['indicators']['quote'][0]['close']})

            # 获取该股票特有的 PE 和 增速
            q_url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={ticker}"
            q_res = requests.get(q_url, headers=headers).json()['quoteResponse']['result'][0]
            pe = q_res.get('trailingPE') or q_res.get('forwardPE') or 20.0
            
            s_url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=defaultKeyStatistics"
            s_res = requests.get(s_url, headers=headers).json()['quoteSummary']['result'][0]['defaultKeyStatistics']
            growth = s_res.get('earningsQuarterlyGrowth', {}).get('raw') or 0.15
            
            return {"price": price, "pe": float(pe), "growth": float(growth), "name": ticker, "history": hist_df}
    except: return None

# --- 5. 主界面渲染 ---
st.title(t["title"])

if not ticker:
    # 恢复上手指南
    st.info(t["welcome"])
    st.markdown(t["guide"])
else:
    with st.spinner('Connecting...'):
        data = get_stock_data_final(ticker)
    
    if data:
        # 指标展示
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t["m_price"], f"{data['price']:.2f}")
        c2.metric(t["m_pe"], f"{data['pe']:.2f}")
        c3.metric(t["m_growth"], f"{data['growth']*100:.1f}%")
        c4.metric(t["m_target"], f"{target_pe:.1f}")

        # 诊断
        if data['pe'] > target_pe:
            y = math.log(data['pe'] / target_pe) / math.log(1 + data['growth'])
            st.warning(t["diag_years"].format(y))
        else:
            st.success(t["diag_gold"])

        # 图表
        st.subheader(f"📊 {data['name']} {'History' if lang=='English' else '历史走势'}")
        fig = go.Figure(go.Scatter(x=data['history']['Date'], y=data['history']['Close'], line=dict(color='#1f77b4')))
        fig.update_layout(template="plotly_white", height=400, margin=dict(l=0,r=0,t=20,b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(t["err"])

# --- 6. 底部版权 ---
st.markdown("---")
st.caption(t["footer"])
