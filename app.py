import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import math
import time

# --- 1. 页面配置与美化 ---
st.set_page_config(page_title="Munger Value Pro", layout="wide", initial_sidebar_state="expanded")

# 自定义 CSS 样式，提升视觉的高级感
st.markdown("""
    <style>
    .metric-card { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4; }
    .footer { text-align: center; color: #888; padding: 20px; font-size: 0.8rem; }
    .stMetric { background-color: #ffffff; border: 1px solid #e0e0e0; padding: 10px; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 侧边栏：配置中心 ---
with st.sidebar:
    st.header("🔍 审查中心")
    ticker_input = st.text_input("输入美股代码", "").upper().strip()
    target_pe = st.slider("目标合理 P/E", 10.0, 40.0, 20.0, help="芒格通常寻找具有护城河且估值合理的公司")
    
    st.markdown("---")
    st.subheader("☕ 支持作者")
    st.write("如果这个工具帮你排除了错误答案：")
    st.markdown("[![Buy Me A Coffee](https://img.shields.io/badge/Donate-Coffee-yellow?style=for-the-badge&logo=buy-me-a-coffee)](https://www.buymeacoffee.com/)")
    
    st.markdown("---")
    st.caption("注：数据源自 Yahoo Finance 实时接口。")

# --- 3. 高性能数据抓取（带缓存） ---
@st.cache_data(ttl=3600)
def get_full_data(ticker):
    try:
        tk = yf.Ticker(ticker)
        # 抓取基础信息、历史价格、以及股本变动
        info = tk.info
        hist = tk.history(period="10y")
        # 尝试获取股本变动趋势
        shares = tk.get_shares_full(start="2020-01-01") 
        return info, hist, shares
    except:
        return None, None, None

# --- 4. 界面渲染逻辑 ---
if not ticker_input:
    # 🌟 初始状态：欢迎指南
    st.title("📈 芒格“价值线”：商业本质审计工具")
    st.info("👋 **法律人，欢迎执行“跨时空合规审查”。**")
    st.markdown("""
    ### 为什么使用本工具？
    芒格认为，长期投资的收益率很难超过业务本身的收益率。本工具不只是看股价，更在审查：
    - **盈利的真实性**：是否有真金白银的现金流支撑？
    - **护城河的厚度**：毛利率是否具备定价权？
    - **管理层的克制**：他们是在乱花钱，还是在回购股票注销？
    
    **在左侧输入代码（如 COST, AAPL, MSFT）开启审查。**
    """)
else:
    with st.spinner(f'正在透视 {ticker_input} 的财务证据链...'):
        info, hist, shares = get_full_data(ticker_input)
        
        if info and 'trailingPE' in info:
            # 提取核心数据
            name = info.get('longName', ticker_input)
            price = info.get('currentPrice', 0)
            pe = info.get('trailingPE')
            growth = info.get('earningsGrowth')
            
            # --- A. 估值看板 (Valuation) ---
            st.subheader(f"⚖️ 估值审查：{name}")
            v1, v2, v3, v4 = st.columns(4)
            v1.metric("当前股价", f"${price:.2f}")
            v2.metric("当前 P/E (TTM)", f"{pe:.2f}")
            v3.metric("预期利润增速", f"{growth*100:.1f}%" if growth else "缺失")
            v4.metric("目标 P/E", f"{target_pe}")

            # --- B. 核心：芒格商业本质审计 (Quality Audit) ---
            st.markdown("---")
            st.subheader("🛡️ 商业本质：核心审计指标")
            
            q1, q2, q3, q4 = st.columns(4)
            
            # 1. 资本效率 (ROE/ROA 初筛)
            roe = info.get('returnOnEquity', 0)
            q1.metric("ROE (净资产收益率)", f"{roe*100:.1f}%", help="芒格认为长期回报率趋同于ROE")
            
            # 2. 定价权 (Gross Margin)
            margin = info.get('grossMargins', 0)
            q2.metric("毛利率 (Margin)", f"{margin*100:.1f}%", help="定价权是抵御通胀的终极武器")
            
            # 3. 净利润含金量 (Cash Quality)
            # 经营现金流 / 净利润
            ocf = info.get('operatingCashflow', 0)
            ni = info.get('netIncomeToCommon', 1)
            fcf_quality = ocf / ni if ni else 0
            q3.metric("利润含金量", f"{fcf_quality:.2f}", help=">1.0 说明利润有充足现金流支持")
            
            # 4. 资本配置 (Capital Allocation)
            # 检查股本变动
            share_trend = "持平"
            if shares is not None and not shares.empty:
                latest_shares = shares.iloc[-1]
                earliest_shares = shares.iloc[0]
                if latest_shares < earliest_shares:
                    share_trend = "持续回购 ✅"
                elif latest_shares > earliest_shares:
                    share_trend = "增发稀释 ⚠️"
            q4.metric("股本变动", share_trend, help="回购注销是管理层对股东负责的表现")

            # --- C. 诊断结论 ---
            st.markdown("---")
            if growth is None or growth <= 0:
                st.error(f"🚫 **推测终止**：由于 {ticker_input} 的利润增速数据缺失或为负，本工具拒绝进行复利回归推测。")
                st.info("💡 芒格教训：如果一家公司不增长或亏损，它不属于“伟大的商业”范畴。")
            else:
                # 芒格回归公式
                years = math.log(pe / target_pe) / math.log(1 + growth) if pe > target_pe else 0
                
                if pe <= target_pe:
                    st.success(f"🌟 **审计结果：极具吸引力**。当前估值已在“击球区”。")
                elif years < 3:
                    st.success(f"✅ **审计结果：优秀**。回归目标估值仅需 **{years:.2f}** 年。")
                elif years < 7:
                    st.info(f"⚖️ **审计结果：合理**。回归目标估值需 **{years:.2f}** 年。")
                else:
                    st.warning(f"⚠️ **审计结果：过热**。回归目标估值需 **{years:.2f}** 年。建议等待更厚的安全边际。")

            # --- D. 价格轨迹 (Log Chart) ---
            if not hist.empty:
                st.subheader("📊 十年价格增长轨迹 (对数刻度)")
                fig = go.Figure()
                # 兼容 yfinance 多层索引
                y_data = hist['Close'] if isinstance(hist['Close'], pd.Series) else hist['Close'].iloc[:, 0]
                fig.add_trace(go.Scatter(x=hist.index, y=y_data, name='股价', line=dict(color='#1f77b4', width=2.5)))
                fig.update_layout(
                    yaxis_type="log", 
                    template="plotly_white", 
                    height=500,
                    margin=dict(l=0, r=0, t=20, b=0),
                    xaxis_title="年份",
                    yaxis_title="价格 (Log Scale)"
                )
                st.plotly_chart(fig, use_container_width=True)
                
        else:
            st.error("🚫 无法抓取该代码的财务证据。请确认代码正确且该股有公开财报。")

# --- 5. 页脚 ---
st.markdown(f'<div class="footer">Munger Value Pro | 2026 法律人深度审计版</div>', unsafe_allow_html=True)
