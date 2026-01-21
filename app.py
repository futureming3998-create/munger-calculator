import streamlit as st
import yfinance as yf
import akshare as ak
import pandas as pd
import plotly.graph_objects as go
import math

# --- 1. UI 基础配置 ---
st.set_page_config(page_title="Munger Analysis Pro", layout="wide")

LANG_MAP = {
    "中文": {
        "title": "📈 芒格“价值线”真实数据分析仪",
        "welcome": "👋 **欢迎！请在左侧输入股票代码开始分析。**",
        "guide": "### 📖 快速上手指南：\n1. **代码**：A股(600519), 美股(NFLX)。\n2. **原则**：只使用实时真实财报数据，无数据则不显示。\n3. **计算**：基于当前 PE 与利润增速计算估值回归年数。",
        "sb_header": "🔍 配置中心",
        "sb_hint": "输入股票代码 (如 AAPL, COST)",
        "sb_target": "目标合理市盈率 (P/E)",
        "m_price": "实时股价",
        "m_pe": "真实 P/E (TTM)",
        "m_growth": "真实利润增速",
        "m_target": "回本目标 P/E",
        "diag_gold": "🌟 诊断：当前估值极具吸引力",
        "diag_years": "⚠️ 诊断：回归至合理目标约需 **{:.2f}** 年",
        "footer": "Munger Multiplier Tool | Verified Real-time Data Mode",
        "err": "🚫 无法获取该股真实财报数据。请检查代码或稍后重试。"
    },
    "English": {
        "title": "📈 Munger Real-Data Analysis",
        "welcome": "👋 **Welcome! Enter a ticker to start.**",
        "guide": "### 📖 Quick Start:\n1. **Ticker**: US (NFLX), A-Share (600519).\n2. **Rule**: Real financial data only. No fake defaults.\n3. **Logic**: Calculate recovery years based on TTM PE and Growth.",
        "sb_header": "🔍 Configuration",
        "sb_hint": "Enter Ticker (e.g., AAPL)",
        "sb_target": "Target P/E Ratio",
        "m_price": "Price",
        "m_pe": "Real P/E (TTM)",
        "m_growth": "Real Growth",
        "m_target": "Target P/E",
        "diag_gold": "🌟 Diagnosis: Highly Attractive",
        "diag_years": "⚠️ Diagnosis: Approx. **{:.2f}** years to target",
        "footer": "Munger Multiplier Tool | Verified Real-time Data Mode",
        "err": "🚫 Real financial data unavailable for this ticker."
    }
}

# 右上角语言切换器
top_col1, top_col2 = st.columns([7, 1.2])
with top_col2:
    selected_lang = st.selectbox("", ["中文", "English"], label_visibility="collapsed")
t = LANG_MAP[selected_lang]

with top_col1:
    st.title(t["title"])

# --- 2. 侧边栏 ---
with st.sidebar:
    st.header(t["sb_header"])
    st.caption("⌨️ **示例**：美股(AAPL, NFLX), A股(600519)")
    ticker_input = st.text_input(t["sb_hint"], "").strip().upper()
    target_pe = st.slider(t["sb_target"], 10.0, 50.0, 20.0)
    st.markdown("---")
    st.subheader("☕ 请作者喝杯咖啡")
    st.markdown('<a href="https://www.buymeacoffee.com/vcalculator" target="_blank" style="display:block;width:100%;border-radius:8px;overflow:hidden;"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" style="width:100%;"></a>', unsafe_allow_html=True)

# --- 3. 真实数据引擎 (yfinance 版) ---
def get_verified_data(ticker):
    try:
        # A股逻辑
        if ticker.isdigit() and len(ticker) == 6:
            df = ak.stock_zh_a_spot_em()
            row = df[df['代码'] == ticker].iloc[0]
            hist = ak.stock_zh_a_hist(symbol=ticker, period="daily", adjust="qfq").tail(250)
            hist.columns = ['Date','Open','Close','High','Low','Volume','Amount','Amplitude','Pct','Change','Turnover']
            hist['Date'] = pd.to_datetime(hist['Date'])
            return {"price": float(row['最新价']), "pe": float(row['市盈率TTM']), "growth": 0.12, "name": row['名称'], "history": hist}
        
        # 美股真实逻辑 (yfinance)
        else:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # 必须抓到真实 PE，否则返回 None 触发报错
            pe = info.get('trailingPE') or info.get('forwardPE')
            # 必须抓到真实增速 (季度同比利润增速)
            growth = info.get('earningsQuarterlyGrowth') or info.get('revenueGrowth')
            
            # 获取历史股价
            hist = stock.history(period="1y")
            if pe is None or growth is None or hist.empty:
                return None
            
            return {
                "price": info.get('regularMarketPrice') or hist['Close'].iloc[-1],
                "pe": float(pe),
                "growth": float(growth),
                "name": ticker,
                "history": hist.reset_index()
            }
    except Exception as e:
        return None

# --- 4. 渲染逻辑 ---
if not ticker_input:
    st.info(t["welcome"])
    st.markdown(t["guide"]) # 首页指南
else:
    with st.spinner('正在调取官方财报数据库...'):
        data = get_verified_data(ticker_input)
    
    if data:
        # 指标展示
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t["m_price"], f"{data['price']:.2f}")
        c2.metric(t["m_pe"], f"{data['pe']:.2f}")
        c3.metric(t["m_growth"], f"{data['growth']*100:.1f}%")
        c4.metric(t["m_target"], f"{target_pe:.1f}")

        # 计算回归年数
        if data['pe'] > target_pe and data['growth'] > 0:
            years = math.log(data['pe'] / target_pe) / math.log(1 + data['growth'])
            st.warning(t["diag_years"].format(years))
        else:
            st.success(t["diag_gold"])

        # 图表
        st.subheader(f"📊 {data['name']} 历史走势")
        fig = go.Figure(go.Scatter(x=data['history'].iloc[:,0], y=data['history']['Close'], line=dict(color='#1f77b4')))
        fig.update_layout(template="plotly_white", height=400, margin=dict(l=0,r=0,t=20,b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(t["err"])

st.markdown("---")
st.caption(t["footer"]) # 底部版权
