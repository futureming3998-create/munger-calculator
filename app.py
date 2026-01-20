import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import math
import time

# 1. 语言字典配置 [cite: 2026-01-05]
LANG = {
    "中文": {
        "title": "📈 芒格“价值线”回归分析仪",
        "welcome_info": "👋 **欢迎！请在左侧输入股票代码开始。**",
        "sidebar_cfg": "🔍 配置中心",
        "input_label": "输入代码 (如 AAPL 或 600519.SS)",
        "target_pe_label": "目标 P/E (回本基准)",
        "metric_price": "当前股价",
        "metric_pe": "当前 P/E (TTM)",
        "metric_growth": "预期利润增速",
        "metric_target": "目标 P/E",
        "diag_gold_pit": "🌟 诊断：黄金坑（内在价值极高）",
        "diag_attractive": "✅ 诊断：极具吸引力",
        "diag_fair": "⚖️ 诊断：合理区间",
        "diag_overheat": "⚠️ 诊断：目前明显过热",
        "diag_years_msg": "回归年数为 **{:.2f}** 年。",
        "chart_header": "📊 {} 轨迹图（对数轴）",
        "err_no_data": "🚫 无法抓取数据，请稍后重试。"
    },
    "English": {
        "title": "📈 Munger Value Line Calculator",
        "welcome_info": "👋 **Welcome! Enter ticker in the sidebar.**",
        "sidebar_cfg": "🔍 Configuration",
        "input_label": "Enter Ticker (e.g., AAPL, MSFT)",
        "target_pe_label": "Target P/E Ratio",
        "metric_price": "Price",
        "metric_pe": "Current P/E",
        "metric_growth": "Earnings Growth",
        "metric_target": "Target P/E",
        "diag_gold_pit": "🌟 Diagnosis: Deep Value",
        "diag_attractive": "✅ Diagnosis: Attractive",
        "diag_fair": "⚖️ Diagnosis: Fair Value",
        "diag_overheat": "⚠️ Diagnosis: Overheated",
        "diag_years_msg": "Payback years: **{:.2f}**.",
        "chart_header": "📊 {} Historical Chart",
        "err_no_data": "🚫 Data unavailable. Please try again."
    }
}

st.set_page_config(page_title="Munger Analysis", layout="wide")

# 2. 侧边栏与打赏
with st.sidebar:
    sel_lang = st.selectbox("Language", ["中文", "English"])
    t = LANG[sel_lang]
    st.header(t["sidebar_cfg"])
    
    ticker_input = st.text_input(t["input_label"], "").upper()
    target_pe = st.slider(t["target_pe_label"], 10.0, 40.0, 20.0)
    
    st.markdown("---")
    # 保持黄色品牌一致性
    st.markdown(f'''
    <a href="https://www.buymeacoffee.com/vcalculator" target="_blank">
        <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" style="height: 45px;">
    </a>''', unsafe_allow_html=True)

st.title(t["title"])

# 3. 稳健版抓取引擎 [cite: 2026-01-05]
@st.cache_data(ttl=3600)
def get_stock_data(ticker):
    try:
        tk = yf.Ticker(ticker)
        inf = tk.info
        # 针对 A 股价格缺失的保底方案 [cite: 2026-01-05]
        price = inf.get('currentPrice') or inf.get('regularMarketPrice') or inf.get('previousClose') or 0.0
        pe = inf.get('trailingPE')
        growth = inf.get('earningsGrowth')
        
        if pe and price:
            return {
                "price": price, "pe": pe, "growth": growth, 
                "name": inf.get('longName', ticker)
            }
        return None
    except:
        return None

# 4. 页面运行逻辑 [cite: 2026-01-05]
if not ticker_input:
    st.info(t["welcome_info"])
else:
    data = get_stock_data(ticker_input)
    if data:
        # 容错：如果没抓到增速（A股常见），设为保守的15% [cite: 2026-01-05]
        growth_rate = data['growth'] if data['growth'] else 0.15
        current_pe = data['pe']
        
        # 指标行
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t["metric_price"], f"${data['price']:.2f}")
        c2.metric(t["metric_pe"], f"{current_pe:.2f}")
        c3.metric(t["metric_growth"], f"{growth_rate*100:.1f}%")
        c4.metric(t["metric_target"], f"{target_pe}")

        # 芒格回归核心逻辑 [cite: 2026-01-05]
        if growth_rate > 0:
            pe_ratio = current_pe / target_pe
            years = math.log(pe_ratio) / math.log(1 + growth_rate) if pe_ratio > 1 else 0
            
            if pe_ratio <= 1:
                st.success(t["diag_gold_pit"])
            elif years < 3:
                st.success(t["diag_attractive"])
                st.write(t["diag_years_msg"].format(years))
            elif 3 <= years <= 7:
                st.info(t["diag_fair"])
                st.write(t["diag_years_msg"].format(years))
            else:
                st.warning(t["diag_overheat"])
                st.write(t["diag_years_msg"].format(years))

        # 5. 可视化图表 [cite: 2026-01-05]
        st.subheader(t["chart_header"].format(data['name']))
        hist = yf.download(ticker_input, period="5y")
        if not hist.empty:
            fig = go.Figure()
            # 兼容多级索引 [cite: 2026-01-05]
            y_vals = hist['Close'].iloc[:,0] if len(hist['Close'].shape) > 1 else hist['Close']
            fig.add_trace(go.Scatter(x=hist.index, y=y_vals, line=dict(color='#FFC107', width=2)))
            fig.update_layout(yaxis_type="log", template="plotly_dark", 
                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=450)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(t["err_no_data"])

st.markdown("---")
st.caption("Munger Multiplier Tool | Built by Gemini")
