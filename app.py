import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import math

# --- 1. 语言与 UI 配置 ---
LANG = {
    "中文": {
        "title": "📈 芒格“价值线”复利回归分析仪",
        "welcome_msg": "👋 **欢迎！请在左侧输入股票代码开始分析。**",
        "guide_title": "快速上手指南：",
        "guide_1": "1. **输入代码**：在左侧输入股票代码（如 AAPL）。",
        "guide_2": "2. **设定目标**：调整滑块选择你认为合理的“目标市盈率”。",
        "guide_3": "3. **看懂结论**：系统自动计算“黄金坑”或“过热”诊断。",
        "sidebar_cfg": "🔍 配置中心",
        "input_guide_header": "⌨️ **A股输入指南：**",
        "input_guide_body": "• 沪市(6)加 **.SS**; 深市(0/3)加 **.SZ**",
        "input_label": "输入股票代码 (如 AAPL, MSFT)",
        "target_pe_label": "目标合理市盈率 (P/E)",
        "coffee_header": "☕ 请作者喝杯咖啡",
        "coffee_body": "如果你觉得这个工具有帮助，欢迎支持！",
        "metric_price": "当前股价",
        "metric_pe": "当前 P/E (TTM)",
        "metric_growth": "预期利润增速",
        "metric_target": "回本目标 P/E",
        "diag_years_msg": "回归年数为 **{:.2f}** 年。",
        "err_no_data": "🚫 数据暂时无法获取，请检查代码或重试。"
    },
    "English": {
        "title": "📈 Munger Value Line Calculator",
        "welcome_msg": "👋 **Welcome! Enter a ticker in the sidebar.**",
        "guide_title": "Quick Start Guide:",
        "guide_1": "1. **Enter Ticker**: Type a stock code (e.g., AAPL).",
        "guide_2": "2. **Set Target**: Adjust the slider for target P/E.",
        "guide_3": "3. **Read Result**: System calculates the 'Value Pit' or 'Overheat'.",
        "sidebar_cfg": "🔍 Configuration",
        "input_guide_header": "⌨️ **Ticker Guide:**",
        "input_guide_body": "• US: AAPL; HK: 0700.HK; CN: 600519.SS",
        "input_label": "Enter Ticker (e.g., AAPL, MSFT)",
        "target_pe_label": "Target P/E Ratio",
        "coffee_header": "☕ Support the Dev",
        "coffee_body": "If you like this tool, consider supporting me!",
        "metric_price": "Price",
        "metric_pe": "Current P/E",
        "metric_growth": "Earnings Growth",
        "metric_target": "Target P/E",
        "diag_years_msg": "Payback years: **{:.2f}**.",
        "err_no_data": "🚫 Data unavailable. Please try again."
    }
}

st.set_page_config(page_title="Munger Analysis", layout="wide")

# CSS 样式：右上角语言框红色边框 + 亮黄色滑块
st.markdown("""
    <style>
    div[data-baseweb="select"] { border: 1px solid #FF4B4B !important; border-radius: 4px; }
    .stSlider > div > div > div > div { background: #FFC107 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 顶部布局 ---
top_col1, top_col2 = st.columns([8, 2])
with top_col2:
    sel_lang = st.selectbox("", ["中文", "English"], label_visibility="collapsed")
    t = LANG[sel_lang]
with top_col1:
    st.title(t["title"])

# --- 3. 侧边栏 ---
with st.sidebar:
    st.header(t["sidebar_cfg"])
    st.caption(t["input_guide_header"])
    st.caption(t["input_guide_body"])
    ticker_input = st.text_input(t["input_label"], "").upper().strip()
    target_pe = st.slider(t["target_pe_label"], 10.0, 40.0, 20.0)
    
    st.markdown("---")
    st.subheader(t["coffee_header"])
    st.caption(t["coffee_body"])
    st.markdown(f'''<a href="https://www.buymeacoffee.com/vcalculator" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" style="height: 45px;"></a>''', unsafe_allow_html=True)

# --- 4. 极致稳健的数据抓取逻辑 ---
@st.cache_data(ttl=600)
def get_safe_stock_data(ticker):
    try:
        tk = yf.Ticker(ticker)
        # 核心改进：优先获取历史行情，因为这个接口最稳定
        hist = tk.history(period="10y")
        if hist.empty: return None
        
        last_price = float(hist['Close'].iloc[-1])
        
        # 尝试获取 PE 和增速，如果失败则给保底值
        try:
            info = tk.info
            pe = info.get('trailingPE') or info.get('forwardPE') or 20.0
            growth = info.get('earningsGrowth') or 0.15
        except:
            pe, growth = 20.0, 0.15
            
        return {"price": last_price, "pe": pe, "growth": growth, "hist": hist}
    except:
        return None

# --- 5. 主界面逻辑 ---
if not ticker_input:
    st.info(t["welcome_msg"])
    st.subheader(t["guide_title"])
    st.write(t["guide_1"])
    st.write(t["guide_2"])
    st.write(t["guide_3"])
else:
    data = get_safe_stock_data(ticker_input)
    
    if data:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t["metric_price"], f"${data['price']:.2f}")
        c2.metric(t["metric_pe"], f"{data['pe']:.2f}")
        c3.metric(t["metric_growth"], f"{data['growth']*100:.1f}%")
        c4.metric(t["metric_target"], f"{target_pe}")

        # 计算回归年数 [cite: 2026-01-05]
        pe_ratio = data['pe'] / target_pe
        if pe_ratio > 1 and data['growth'] > 0:
            years = math.log(pe_ratio) / math.log(1 + data['growth'])
            st.success(t["diag_years_msg"].format(years))
        else:
            st.success(t["diag_years_msg"].format(0.0))

        # 走势图
        fig = go.Figure(go.Scatter(x=data['hist'].index, y=data['hist']['Close'], line=dict(color='#FFC107', width=2)))
        fig.update_layout(yaxis_type="log", template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(t["err_no_data"])

# --- 6. 底部版权 ---
st.markdown("---")
st.caption("Munger Multiplier Tool | Built by Gemini")
