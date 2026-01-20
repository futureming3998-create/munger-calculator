import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import math
import time

# 页面基础配置
st.set_page_config(page_title="芒格价值线工具", page_icon="📈", layout="wide")

st.title("📈 芒格“价值线”复利回归分析仪")
st.markdown("---")

# 侧边栏：用户输入
with st.sidebar:
    st.header("🔍 配置中心")
    # 修改前：ticker_input = st.text_input("...", "GOOGL").upper()
ticker_input = st.text_input("输入股票代码 (如 AAPL, MSFT, COST)", "").upper()
    target_pe = st.slider("目标合理市盈率 (P/E)", 10.0, 40.0, 20.0)
    st.info("注：若遇到 Rate Limited，请稍等30秒再切换代码。")

# --- 核心数据抓取函数（带缓存逻辑） ---
@st.cache_data(ttl=3600)  # 缓存1小时，减少请求频率
def get_stock_data(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        # 使用 fast_info 或直接从 info 获取，并增加延时重试逻辑
        info = stock.info
        return info
    except Exception:
        return None

@st.cache_data(ttl=3600)
def get_stock_history(ticker_symbol):
    try:
        # 使用 yf.download 并强制平坦化数据
        df = yf.download(ticker_symbol, period="10y", interval="1d", progress=False)
        
        # 处理多层索引 (MultiIndex) 问题
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # 确保索引是干净的日期格式
        df.index = pd.to_datetime(df.index)
        
        # 检查是否真的有数据
        if df.empty or 'Close' not in df.columns:
            return pd.DataFrame()
            
        return df[['Close']] 
    except Exception as e:
        st.error(f"图表数据抓取失败: {e}")
        return pd.DataFrame()

# --- 运行逻辑 ---
if not ticker_input:
    # 🌟 当用户还没输入代码时，显示这段欢迎信息 [cite: 2026-01-05]
    st.info("👋 **欢迎使用芒格复利回归分析仪！**")
    st.markdown("""
    ### 快速上手指南：
    1. **输入代码**：在左侧输入你想研究的股票代码（如 **AAPL**）。
    2. **设定目标**：调整滑块选择你认为合理的“目标市盈率”（通常设为 20）。
    3. **看懂结论**：系统会自动计算并给出“黄金坑”或“过热”诊断。
    """)
else:
    # 只有当用户输入了代码，才会启动下面的分析逻辑 [cite: 2026-01-05]
    time.sleep(0.5)
    info = get_stock_data(ticker_input)
    
    if info and 'trailingPE' in info:
        # 提取指标
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
                st.write(f"当前 P/E 已低于目标值。内在价值极高！")
            elif years < 3:
                st.success(f"✅ **诊断：极具吸引力**")
                st.write(f"回归年数仅为 **{years:.2f}** 年。利润增长极快。")
            elif 3 <= years <= 7:
                st.info(f"⚖️ **诊断：合理区间**")
                st.write(f"回归年数 **{years:.2f}** 年。好公司配好价格。")
            else:
                st.warning(f"⚠️ **诊断：目前明显过热**")
                st.write(f"回归年数长达 **{years:.2f}** 年。建议保持克制。")
        
        # 3. 历史对数图表
        hist = get_stock_history(ticker_input)
        if not hist.empty:
            st.subheader(f"📊 {name} 十年轨迹（对数刻度）")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='股价', line=dict(color='#1f77b4')))
            fig.update_layout(yaxis_type="log", template="plotly_white", height=400)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("🚫 无法抓取数据。")
        st.info("💡 建议：检查代码是否正确（如 AAPL）或 5 分钟后再试。")

st.markdown("---")
st.caption("由 Gemini 思想伙伴助力开发 | 数据源：Yahoo Finance")
