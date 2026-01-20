import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import math

# 设置页面
st.set_page_config(page_title="芒格复利分析仪", layout="wide")

# --- 1. 核心计算函数 [cite: 2026-01-05] ---
def calculate_years(current_pe, target_pe, growth_rate):
    if growth_rate <= 0 or current_pe <= target_pe:
        return 0
    # 公式: (1 + g)^n = current_pe / target_pe
    years = math.log(current_pe / target_pe) / math.log(1 + growth_rate)
    return years

# --- 2. 侧边栏：配置中心 ---
with st.sidebar:
    st.header("🔍 配置中心")
    st.markdown("**A股输入指南：**\n* 沪市(6)加 **.SS**; 深市(0/3)加 **.SZ**")
    ticker_input = st.text_input("输入股票代码 (如 AAPL, MSFT)", "AAPL").upper()
    target_pe = st.slider("目标合理市盈率 (P/E)", 10.0, 40.0, 20.0)

# --- 3. 数据抓取与逻辑处理 ---
@st.cache_data(ttl=3600)
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        # 多级保底取价，防止出现 N/A
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        pe = info.get('trailingPE')
        growth = info.get('earningsGrowth') or 0.15 # 若无数据，默认15%增速
        name = info.get('longName', ticker)
        return {"price": price, "pe": pe, "growth": growth, "name": name}
    except:
        return None

# --- 4. 主界面渲染 ---
st.title("📈 芒格“价值线”复利回归分析仪")

data = get_stock_data(ticker_input)

if data and data['pe'] and data['price']:
    # 四个核心指标卡片
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("当前股价", f"${data['price']:.2f}")
    c2.metric("当前 P/E (TTM)", f"{data['pe']:.2f}")
    c3.metric("预期利润增速", f"{data['growth']*100:.1f}%")
    c4.metric("回本目标 P/E", f"{target_pe}")

    # 诊断结论
    years = calculate_years(data['pe'], target_pe, data['growth'])
    if years > 0:
        st.warning(f"⚠️ 诊断：目前股价相对目标估值过热，回归年数为 **{years:.2f}** 年。")
    else:
        st.success("✅ 诊断：当前估值极具吸引力，已处于“黄金坑”区域。")

    # 绘制对数历史走势图
    st.subheader(f"📊 {data['name']} 十年轨迹（对数刻度）")
    hist = yf.download(ticker_input, period="10y")
    if not hist.empty:
        fig = go.Figure(go.Scatter(x=hist.index, y=hist['Close'], name="收盘价"))
        fig.update_layout(
            yaxis_type="log",
            template="plotly_dark",
            xaxis_title="年份",
            yaxis_title="价格 (USD/对数)",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.error("🚫 无法抓取完整数据。请检查代码是否正确，或尝试搜索其他股票。")

# --- 5. 底部信息 ---
st.markdown("---")
st.caption("Munger Multiplier Analysis Tool | Powered by Yahoo Finance")
