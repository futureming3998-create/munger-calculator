import streamlit as st
import akshare as ak
import pandas as pd
import plotly.graph_objects as go
import math
import requests

# --- 1. 语言包配置 ---
LANG = {
    "中文": {
        "title": "📈 芒格“价值线”复利回归分析仪",
        "welcome": "👋 **欢迎！请在左侧输入股票代码开始分析。**",
        "guide_title": "📖 快速上手指南：",
        "guide_1": "1. **输入代码**：A股(600519), 港股(00700), 美股(NFLX)。",
        "guide_2": "2. **设定目标**：调整侧边栏滑块，选择你心目中的合理市盈率。",
        "guide_3": "3. **看懂结论**：系统自动计算当前估值回归合理区间所需的年数。",
        "sidebar_cfg": "🔍 配置中心",
        "input_label": "输入股票代码 (如 AAPL, MSFT)",
        "slider_label": "目标合理市盈率 (P/E)",
        "metric_price": "实时股价",
        "metric_pe": "当前 P/E (TTM)",
        "metric_growth": "预期利润增速",
        "metric_target": "回本目标 P/E",
        "diag_gold": "🌟 诊断：当前估值极具吸引力（黄金坑）",
        "diag_years": "⚠️ 诊断：回归至合理目标约需 **{:.2f}** 年",
        "footer": "Munger Multiplier Analysis Tool | Powered by Gemini & Yahoo Finance",
        "coffee": "☕ 请作者喝杯咖啡",
        "error": "🚫 无法抓取数据，请检查代码格式（美股需大写）或稍后重试。"
    },
    "English": {
        "title": "📈 Munger Value Line Analysis Tool",
        "welcome": "👋 **Welcome! Enter a ticker on the left to start.**",
        "guide_title": "📖 Quick Start Guide:",
        "guide_1": "1. **Enter Ticker**: A-Shares (600519), HK (00700), US (NFLX).",
        "guide_2": "2. **Set Target**: Use the slider to set your target P/E ratio.",
        "guide_3": "3. **Read Results**: The tool calculates years needed to reach target valuation.",
        "sidebar_cfg": "🔍 Configuration",
        "input_label": "Enter Ticker (e.g., AAPL)",
        "slider_label": "Target P/E Ratio",
        "metric_price": "Real-time Price",
        "metric_pe": "Current P/E (TTM)",
        "metric_growth": "Est. Growth Rate",
        "metric_target": "Target P/E",
        "diag_gold": "🌟 Diagnosis: Highly Attractive (Value Gap)",
        "diag_years": "⚠️ Diagnosis: Approx. **{:.2f}** years to reach target",
        "footer": "Munger Multiplier Analysis Tool | Powered by Gemini & Yahoo Finance",
        "coffee": "☕ Buy me a coffee",
        "error": "🚫 Data fetch failed. Please check ticker or try again later."
    }
}

# --- 2. 界面基础配置 ---
st.set_page_config(page_title="Munger Pro", layout="wide")

# UI 样式修正 (打赏按钮 100% 宽度对齐)
st.markdown('''
    <style>
    .coffee-btn { display: block; width: 100%; border-radius: 8px; overflow: hidden; margin-top: 10px; }
    .coffee-btn img { width: 100%; object-fit: contain; }
    div[data-testid="stMetricValue"] > div { font-size: 1.8rem !important; }
    </style>
''', unsafe_allow_html=True)

# --- 3. 语言切换选择 ---
lang_choice = st.selectbox("", ["中文", "English"], index=0, label_visibility="collapsed")
t = LANG[lang_choice]

# --- 4. 侧边栏布局 ---
with st.sidebar:
    st.header(t["sidebar_cfg"])
    st.caption("⌨️ **A股指南**：\n• 沪市(60)加 .SS; 深市(0/3)加 .SZ") # 增加备用输入建议
    ticker_input = st.text_input(t["input_label"], "").strip().upper()
    target_pe = st.slider(t["slider_label"], 10.0, 50.0, 20.0)
    
    st.info("注：若遇到数据延迟，请稍等30秒再切换代码。")
    st.markdown("---")
    st.subheader(t["coffee"])
    st.markdown('<a href="https://www.buymeacoffee.com/vcalculator" target="_blank" class="coffee-btn"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"></a>', unsafe_allow_html=True)

# --- 5. 核心数据引擎 (差异化抓取) ---
def fetch_real_data(ticker):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        # A股兼容逻辑
        if ticker.isdigit() and len(ticker) == 6:
            df = ak.stock_zh_a_spot_em()
            row = df[df['代码'] == ticker].iloc[0]
            hist = ak.stock_zh_a_hist(symbol=ticker, period="daily", adjust="qfq").tail(200)
            hist.columns = ['Date','Open','Close','High','Low','Volume','Amount','Amplitude','Pct','Change','Turnover']
            hist['Date'] = pd.to_datetime(hist['Date'])
            return {"price": float(row['最新价']), "pe": float(row['市盈率TTM']), "growth": 0.12, "name": row['名称'], "history": hist}
        
        # 美股逻辑 (修复数据雷同问题)
        elif ticker.isalpha():
            # 价格与走势
            c_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1y"
            c_res = requests.get(c_url, headers=headers, timeout=10).json()
            meta = c_res['chart']['result'][0]['meta']
            price = float(meta['regularMarketPrice'])
            ts = c_res['chart']['result'][0]['timestamp']
            closes = c_res['chart']['result'][0]['indicators']['quote'][0]['close']
            hist_df = pd.DataFrame({'Date': pd.to_datetime(ts, unit='s'), 'Close': closes})

            # 真实 PE 与 增速
            q_url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={ticker}"
            q_data = requests.get(q_url, headers=headers, timeout=10).json()['quoteResponse']['result'][0]
            pe = q_data.get('trailingPE') or q_data.get('forwardPE') or 20.0
            
            s_url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=defaultKeyStatistics"
            s_data = requests.get(s_url, headers=headers).json()['quoteSummary']['result'][0]['defaultKeyStatistics']
            growth = s_data.get('earningsQuarterlyGrowth', {}).get('raw') or 0.15
            
            return {"price": price, "pe": float(pe), "growth": float(growth), "name": ticker, "history": hist_df}
    except: return None

# --- 6. 主内容展示 ---
st.title(t["title"])

if not ticker_input:
    # 首页指南
    st.info(t["welcome"])
    st.subheader(t["guide_title"])
    st.write(t["guide_1"])
    st.write(t["guide_2"])
    st.write(t["guide_3"])
else:
    with st.spinner('Fetching real-time data...'):
        data = fetch_real_data(ticker_input)
    
    if data:
        # 指标栏
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t["metric_price"], f"{data['price']:.2f}")
        c2.metric(t["metric_pe"], f"{data['pe']:.2f}")
        c3.metric(t["metric_growth"], f"{data['growth']*100:.1f}%")
        c4.metric(t["metric_target"], f"{target_pe}")

        # 计算诊断
        if data['pe'] > target_pe:
            years = math.log(data['pe'] / target_pe) / math.log(1 + data['growth'])
            st.warning(t["diag_years"].format(years))
        else:
            st.success(t["diag_gold"])

        # 图表
        st.subheader(f"📊 {data['name']} {('History' if lang_choice=='English' else '历史走势')}")
        fig = go.Figure(go.Scatter(x=data['history']['Date'], y=data['history']['Close'], line=dict(color='#1f77b4')))
        fig.update_layout(template="plotly_white", height=400, margin=dict(l=0,r=0,t=20,b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(t["error"])

# --- 7. 底部说明 ---
st.markdown("---")
st.caption(t["footer"])
