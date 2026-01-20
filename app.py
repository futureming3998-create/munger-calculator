import streamlit as st
import yfinance as yf
import math

# 设置页面配置
st.set_page_config(page_title="芒格复利回归计算器", page_icon="📈")

st.title("💡 芒格复利回归计算器")
st.write("输入股票代码，看看盈利增长需要多久能填平目前的估值溢价。")

# 侧边栏设置
st.sidebar.header("计算参数")
target_pe = st.sidebar.slider("目标合理市盈率 (Target P/E)", 10.0, 40.0, 20.0)

# 用户输入股票代码
ticker_input = st.text_input("请输入股票代码 (例如: GOOGL, TSLA, 600519.SS)", "GOOGL")

if ticker_input:
    try:
        # 获取股票数据
        stock = yf.Ticker(ticker_input)
        info = stock.info
        
        # 提取关键指标
        name = info.get('longName', ticker_input)
        current_pe = info.get('trailingPE')
        # 假设预期增长率为历史5年盈利增长率，若无则默认15%
        growth_rate = info.get('earningsGrowth', 0.15) 
        
        if current_pe:
            st.subheader(f"📊 {name} ({ticker_input}) 数据概览")
            col1, col2, col3 = st.columns(3)
            col1.metric("当前 P/E (TTM)", f"{current_pe:.2f}")
            col2.metric("预期增长率", f"{growth_rate*100:.1f}%")
            col3.metric("目标 P/E", f"{target_pe}")

            # 核心计算逻辑
            if growth_rate <= 0:
                st.error("该公司的盈利增长率为负或零，盈利无法追上股价。")
            elif current_pe <= target_pe:
                st.success(f"当前市盈率已经低于目标值 {target_pe}，属于芒格眼中的价值区间！")
            else:
                # 计算回归年数
                years = math.log(current_pe / target_pe) / math.log(1 + growth_rate)
                
                st.divider()
                st.info(f"🚀 **回归结论：** 在保持 {growth_rate*100:.1f}% 增长的前提下，盈利追上股价需要 **{years:.2f}** 年。")
                
                # 可视化进度条或评价
                if years < 3:
                    st.balloons()
                    st.write("✅ **芒格评价：** 这是一个优秀的复利机器，溢价很快就能被消化。")
                elif years < 7:
                    st.write("⚖️ **芒格评价：** 估值适中偏高，需要公司长期保持竞争力。")
                else:
                    st.warning("⚠️ **芒格评价：** 价格严重脱离现实，这可能是一场豪赌。")
        else:
            st.warning("未能获取到该股票的市盈率数据，请检查代码或稍后再试。")
            
    except Exception as e:
        st.error(f"查询出错: {e}")

st.divider()
st.caption("注：数据来源 Yahoo Finance。投资有风险，本工具仅供逻辑参考。")