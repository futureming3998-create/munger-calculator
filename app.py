import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import math
import time

# 页面配置
st.set_page_config(page_title="芒格价值线工具", layout="wide")
st.title("📈 芒格“价值线”复利回归分析仪")

# --- 侧边栏配置 ---
st.header("🔍 配置中心")
    
    # 🌟 A股输入指南 [cite: 2026-01-05]
    st.caption("⌨️ **A股输入指南：**")
    st.caption("• 沪市(6开头)加 **.SS** (如 600519.SS)")
    st.caption("• 深市(0/3开头)加 **.SZ** (如 002594.SZ)")
    
    # 唯一的输入组件，默认值为空以实现静默启动 [cite: 2026-01-05]
    ticker_input = st.text_input("输入股票代码 (如 AAPL, MSFT, COST)", "").upper()
    target_pe = st.slider("目标合理市盈率 (P/E)", 10.0, 40.0, 20.0)
    st.info("注：若遇到 Rate Limited，请稍等30秒再切换股票代码。")

# 数据抓取函数（带缓存）
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
        return yf.download(ticker, period="10y")
    except:
        return pd.DataFrame()

# --- 运行逻辑 ---
if not ticker_input:
    # 🌟 初始状态：显示欢迎指南 [cite: 2026-01-05]
    st.info("👋 **欢迎！请在左侧侧边栏输入股票代码（如 AAPL）开始分析。**")
    st.markdown("""
    ### 快速上手指南：
    1. **输入代码**：在左侧输入你想研究的股票代码。
    2. **设定目标**：调整滑块选择你认为合理的“目标市盈率”。
    3. **看懂结论**：系统会自动告诉你这是一家“黄金坑”公司还是处于“过热”状态。
    """)
else:
    # 只有当 ticker_input 不为空时才运行 [cite: 2026-01-05]
    time.sleep(0.5)
    info = get_stock_data(ticker_input)
    
    if info and 'trailingPE' in info:
        current_pe = info.get('trailingPE')
        growth_rate = info.get('earningsGrowth', 0.15)
        price = info.get('currentPrice', 0)
        name = info.get('longName', ticker_input)

        # 1. 顶部指标看板
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("当前股价", f"${price:.2f}" if price else "N/A")
        col2.metric("当前 P/E (TTM)", f"{current_pe:.2f}")
        col3.metric("预期利润增速", f"{growth_rate*100:.1f}%")
        col4.metric("回本目标 P/E", f"{target_pe}")

        # 2. 逻辑计算与自动诊断 [cite: 2026-01-05]
        if growth_rate > 0:
            years = math.log(current_pe / target_pe) / math.log(1 + growth_rate) if current_pe > target_pe else 0
            
            if current_pe <= target_pe:
                st.success(f"🌟 **诊断：极具吸引力（黄金坑）**")
                st.write(f"当前 P/E ({current_pe:.2f}) 已低于目标值。复利机器在为你白干！")
            elif years < 3:
                st.success(f"✅ **诊断：极具吸引力**")
                st.write(f"回归年数仅为 **{years:.2f}** 年。利润增长极快。")
            elif 3 <= years <= 7:
                st.info(f"⚖️ **诊断：合理区间**")
                st.write(f"回归年数 **{years:.2f}** 年。好公司配好价格。")
            else:
                st.warning(f"⚠️ **诊断：目前明显过热**")
                st.write(f"回归年数长达 **{years:.2f}** 年。建议耐心等待。")
        
        # 3. 历史对数图表
        hist = get_stock_history(ticker_input)
        if not hist.empty:
            st.subheader(f"📊 {name} 十年轨迹（对数刻度）")
            fig = go.Figure()
            # 兼容处理 yfinance 的多层索引
            y_data = hist['Close'] if isinstance(hist['Close'], pd.Series) else hist['Close'].iloc[:, 0]
            fig.add_trace(go.Scatter(x=hist.index, y=y_data, name='股价', line=dict(color='#1f77b4')))
            fig.update_layout(yaxis_type="log", template="plotly_white", height=400)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("🚫 无法抓取数据。")
        st.info("💡 建议：检查代码是否正确（如 AAPL）或 5 分钟后再试。")

st.markdown("---")
st.caption("由 Gemini 思想伙伴助力开发 | 数据源：Yahoo Finance")
