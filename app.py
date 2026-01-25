import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import math
import time

# 1. 页面配置
st.set_page_config(page_title="芒格价值线工具", layout="wide")
st.title("📈 芒格“价值线”复利回归分析仪")

# --- 2. 侧边栏配置 ---
with st.sidebar:
    st.header("🔍 配置中心")
    # 🌟 静默启动：默认值为空 [cite: 2026-01-05]
    ticker_input = st.text_input("输入股票代码 (如 AAPL, MSFT, COST)", "").upper().strip()
    target_pe = st.slider("目标合理市盈率 (P/E)", 10.0, 40.0, 20.0)
    
    st.markdown("---")
    # ☕ Buy Me a Coffee 模块
    st.subheader("☕ 支持作者")
    st.write("如果你觉得这个工具好用，可以请作者喝杯咖啡：")
    st.markdown("[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Donate-yellow?style=for-the-badge&logo=buy-me-a-coffee)](https://www.buymeacoffee.com/)")
    
    st.info("注：数据由 Yahoo Finance 提供。")

# --- 3. 数据抓取函数 ---
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
    # 初始状态引导 [cite: 2026-01-05]
    st.info("👋 **欢迎！请在左侧侧边栏输入股票代码（如 AAPL）开始分析。**")
    st.markdown("""
    ### 快速上手指南：
    1. **输入代码**：在左侧输入你想研究的股票代码。
    2. **设定目标**：调整滑块选择你认为合理的“目标市盈率”。
    3. **看懂结论**：系统将根据 **利润增速** 自动计算回归年数。
    """)
else:
    time.sleep(0.5)
    with st.spinner(f'正在深度扫描 {ticker_input} 财务数据...'):
        info = get_stock_data(ticker_input)
        
        # 核心检查：必须同时具备 PE 和 利润增速
        if info and 'trailingPE' in info:
            current_pe = info.get('trailingPE')
            growth_rate = info.get('earningsGrowth') # 不再设置默认 0.15
            price = info.get('currentPrice', 0)
            name = info.get('longName', ticker_input)

            # 🚨 增速缺失拦截
            if growth_rate is None:
                st.error(f"🚫 **数据缺失：暂时无法提供 {ticker_input} 的分析。**")
                st.warning(f"由于 Yahoo Finance 暂未公开该股的 `earningsGrowth`（利润增速）数据，系统无法进行复利回归推测。")
            else:
                # 指标看板
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("当前股价", f"${price:.2f}" if price else "N/A")
                col2.metric("当前 P/E (TTM)", f"{current_pe:.2f}")
                col3.metric("预期利润增速", f"{growth_rate*100:.1f}%")
                col4.metric("回本目标 P/E", f"{target_pe}")

                # 逻辑诊断
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
                else:
                    st.error("📉 该公司利润增长为负，不符合芒格复利增长模型。")

            # 无论增速是否缺失，都尝试显示历史曲线（增加工具可用性）
            hist = get_stock_history(ticker_input)
            if not hist.empty:
                st.subheader(f"📊 {name} 十年增长轨迹（对数刻度）")
                fig = go.Figure()
                y_data = hist['Close'] if isinstance(hist['Close'], pd.Series) else hist['Close'].iloc[:, 0]
                fig.add_trace(go.Scatter(x=hist.index, y=y_data, name='股价', line=dict(color='#1f77b4')))
                fig.update_layout(yaxis_type="log", template="plotly_white", height=450)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(f"🚫 无法获取 {ticker_input} 的关键估值数据 (P/E)。")
            st.info("提示：请确认代码是否正确，或尝试其他流动性较好的股票。")

st.markdown("---")
st.caption("由 Gemini 思想伙伴助力开发 | 2026")
