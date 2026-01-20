import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import math
import time

# 1. 语言字典配置 [cite: 2026-01-05]
LANG = {
    "中文": {
        "title": "📈 芒格“价值线”复利回归分析仪",
        "welcome_info": "👋 **欢迎！请在左侧输入股票代码开始分析。**",
        "guide_header": "### 快速上手指南：",
        "guide_1": "1. **输入代码**：在左侧输入股票代码（如 AAPL）。",
        "guide_2": "2. **设定目标**：调整滑块选择你认为合理的“目标市盈率”。",
        "guide_3": "3. **看懂结论**：系统自动计算“黄金坑”或“过热”诊断。",
        "sidebar_cfg": "🔍 配置中心",
        "input_label": "输入股票代码 (如 AAPL, MSFT)",
        "target_pe_label": "目标合理市盈率 (P/E)",
        "rate_limit_info": "注：若遇到限制，请稍等30秒再切换代码。",
        "metric_price": "当前股价",
        "metric_pe": "当前 P/E (TTM)",
        "metric_growth": "预期利润增速",
        "metric_target": "回本目标 P/E",
        "diag_gold_pit": "🌟 诊断：极具吸引力（黄金坑）",
        "diag_gold_msg": "当前 P/E 已低于目标值。内在价值极高！",
        "diag_attractive": "✅ 诊断：极具吸引力",
        "diag_fair": "⚖️ 诊断：合理区间",
        "diag_overheat": "⚠️ 诊断：目前明显过热",
        "diag_years_msg": "回归年数为 **{:.2f}** 年。",
        "chart_header": "📊 {} 十年轨迹（对数刻度）",
        "err_no_data": "🚫 无法抓取数据，请检查代码或稍后再试。",
        "coffee_header": "☕ 请作者喝杯咖啡"
    },
    "English": {
        "title": "📈 Munger Value Line Calculator",
        "welcome_info": "👋 **Welcome! Enter a ticker in the sidebar to start.**",
        "guide_header": "### Quick Start Guide:",
        "guide_1": "1. **Enter Ticker**: Type a stock code (e.g., AAPL).",
        "guide_2": "2. **Set Target**: Adjust the slider for target P/E.",
        "guide_3": "3. **Read Result**: System calculates if it's a 'Value Pit'.",
        "sidebar_cfg": "🔍 Configuration",
        "input_label": "Enter Ticker (e.g., AAPL, MSFT)",
        "target_pe_label": "Target P/E Ratio",
        "coffee_header": "☕ Support the Dev",
        "rate_limit_info": "Note: If Rate Limited, wait 30s before retrying.",
        "metric_price": "Price",
        "metric_pe": "Current P/E (TTM)",
        "metric_growth": "Earnings Growth",
        "metric_target": "Target P/E",
        "diag_gold_pit": "🌟 Diagnosis: Deep Value (Golden Pit)",
        "diag_gold_msg": "Current P/E is below target. High intrinsic value!",
        "diag_attractive": "✅ Diagnosis: Highly Attractive",
        "diag_fair": "⚖️ Diagnosis: Fair Value",
        "diag_overheat": "⚠️ Diagnosis: Currently Overheated",
        "diag_years_msg": "Payback years: **{:.2f}** years.",
        "chart_header": "📊 {} 10-Year Trajectory (Log)",
        "err_no_data": "🚫 Data unavailable. Please check ticker or retry later."
    }
}

st.set_page_config(page_title="Munger Value Line", layout="wide")

# --- 2. 布局逻辑 ---
top_col1, top_col2 = st.columns([8, 2])
with top_col2:
    sel_lang = st.selectbox("", ["中文", "English"], label_visibility="collapsed")
    t = LANG[sel_lang]

with top_col1:
    st.title(t["title"])

# --- 3. 侧边栏配置 ---
with st.sidebar:
    st.header(t["sidebar_cfg"])
    
    if sel_lang == "中文":
        st.caption("⌨️ **A股输入指南：**")
        st.caption("• 沪市(6)加 **.SS**; 深市(0/3)加 **.SZ**")
    
    ticker_input = st.text_input(t["input_label"], "").upper()
    target_pe = st.slider(t["target_pe_label"], 10.0, 40.0, 20.0)
    
    # 蓝色提示框
    st.info(t["rate_limit_info"])

    # --- 打赏按钮尺寸对齐逻辑 ---
    st.markdown("---")
    st.subheader(t["coffee_header"])
    # 通过 CSS 让图片宽度填满侧边栏容器，使其与上面的提示框宽度一致
    st.markdown(f'''
        <style>
        .coffee-btn {{
            display: block;
            width: 100%;
            border-radius: 8px;
            overflow: hidden;
        }}
        .coffee-btn img {{
            width: 100%;
            object-fit: contain;
        }}
        </style>
        <a href="https://www.buymeacoffee.com/vcalculator" target="_blank" class="coffee-btn">
            <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee">
        </a>
    ''', unsafe_allow_html=True)

# --- 数据抓取函数 ---
@st.cache_data(ttl=3600)
def get_stock_data(ticker):
    try:
        tk = yf.Ticker(ticker)
        return tk.info
    except:
        return None

@st.cache_data(ttl=3600)
def get_stock_history(ticker):
    try:
        return yf.download(ticker, period="10y", progress=False)
    except:
        return pd.DataFrame()

# --- 4. 运行逻辑 ---
if not ticker_input:
    st.info(t["welcome_info"])
    st.markdown(t["guide_header"])
    st.write(t["guide_1"])
    st.write(t["guide_2"])
    st.write(t["guide_3"])
else:
    time.sleep(0.5)
    info = get_stock_data(ticker_input)
    
    if info and ('trailingPE' in info or 'forwardPE' in info):
        current_pe = info.get('trailingPE') or info.get('forwardPE')
        growth_rate = info.get('earningsGrowth', 0.15)
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        name = info.get('longName', ticker_input)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric(t["metric_price"], f"${price:.2f}" if price else "N/A")
        col2.metric(t["metric_pe"], f"{current_pe:.2f}" if current_pe else "N/A")
        col3.metric(t["metric_growth"], f"{growth_rate*100:.1f}%")
        col4.metric(t["metric_target"], f"{target_pe}")

        if growth_rate and growth_rate > 0 and current_pe:
            pe_ratio = current_pe / target_pe
            years = math.log(pe_ratio) / math.log(1 + growth_rate) if pe_ratio > 1 else 0
            
            if current_pe <= target_pe:
                st.success(t["diag_gold_pit"])
                st.write(t["diag_gold_msg"])
            elif years < 3:
                st.success(t["diag_attractive"])
                st.write(t["diag_years_msg"].format(years))
            elif 3 <= years <= 7:
                st.info(t["diag_fair"])
                st.write(t["diag_years_msg"].format(years))
            else:
                st.warning(t["diag_overheat"])
                st.write(t["diag_years_msg"].format(years))
        
        st.subheader(t["chart_header"].format(name))
        hist = get_stock_history(ticker_input)
        if not hist.empty:
            fig = go.Figure()
            y_data = hist['Close'] if isinstance(hist['Close'], pd.Series) else hist['Close'].iloc[:, 0]
            # 恢复默认配色
            fig.add_trace(go.Scatter(x=hist.index, y=y_data, name='Price'))
            fig.update_layout(yaxis_type="log", template="plotly_white", height=400)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(t["err_no_data"])

st.markdown("---")
st.caption("Munger Multiplier Analysis Tool | Powered by Gemini & Yahoo Finance")
