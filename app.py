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
    ticker_input = st.text_input("输入股票代码 (如 GOOGL, COST, MSFT)", "GOOGL").upper()
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

# 运行逻辑
if ticker_input:
    # 稍微等一下，避免瞬间多次触发
    time.sleep(0.5)
    
    info = get_stock_data(ticker_input)
    
    if info and 'trailingPE' in info:
        # 提取关键指标
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

# 2. 逻辑计算与自动诊断
        if growth_rate > 0:
            # 计算回归年数
            years = math.log(current_pe / target_pe) / math.log(1 + growth_rate) if current_pe > target_pe else 0
            
            # 这里的标准是你设定的选股逻辑 [cite: 2026-01-05]
            if current_pe <= target_pe:
                st.success(f"🌟 **诊断：极具吸引力（黄金坑）**")
                st.write(f"当前 P/E ({current_pe:.2f}) 已低于目标值 ({target_pe})。内在价值极高！")
            elif years < 3:
                st.success(f"✅ **诊断：极具吸引力**")
                st.write(f"回归年数仅为 **{years:.2f}** 年。利润增长极快，是难得的投资机会。")
            elif 3 <= years <= 7:
                st.info(f"⚖️ **诊断：合理区间**")
                st.write(f"回归年数 **{years:.2f}** 年。好公司配好价格，适合长期持有。")
            else:
                st.warning(f"⚠️ **诊断：目前明显过热**")
                st.write(f"回归年数长达 **{years:.2f}** 年。价格透支了太多增长，建议保持克制。")
        
        # 3. 历史对数图表
        hist = get_stock_history(ticker_input)
        if not hist.empty:
            st.subheader(f"📊 {name} 十年轨迹（对数刻度）")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='股价', line=dict(color='#1f77b4')))
            fig.update_layout(yaxis_type="log", template="plotly_white", height=400)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("🚫 触发了 Yahoo 接口限制 (Rate Limited) 或代码无效。")
        st.info("💡 解决建议：\n1. 请在左侧换一个代码（如输入 AAPL）试试。\n2. 5分钟后再刷新网页。\n3. 如果是 A 股，请确保后缀正确，如 600519.SS。")

st.markdown("---")
st.caption("由 Gemini 思想伙伴助力开发 | 数据源：Yahoo Finance")
