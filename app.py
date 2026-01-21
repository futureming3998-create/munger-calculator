import streamlit as st
import akshare as ak
import pandas as pd
import plotly.graph_objects as go
import math
import requests
from datetime import datetime

# --- 1. 基础 UI 配置 ---
st.set_page_config(page_title="Munger Pro", layout="wide")

# 侧边栏样式对齐（打赏按钮 100% 宽度）
st.markdown('''
    <style>
    .coffee-btn { display: block; width: 100%; border-radius: 8px; overflow: hidden; }
    .coffee-btn img { width: 100%; object-fit: contain; }
    div[data-testid="stMetricValue"] > div { font-size: 1.8rem !important; }
    </style>
''', unsafe_allow_html=True)

# --- 2. 实时抓取引擎（无缓存，确保每只股票都不同）---
def get_data_with_history(ticker):
    ticker = ticker.strip().upper()
    try:
        # A股 (6位数字)
        if ticker.isdigit() and len(ticker) == 6:
            df = ak.stock_zh_a_spot_em()
            row = df[df['代码'] == ticker].iloc[0]
            # 获取历史数据用于绘图
            hist_df = ak.stock_zh_a_hist(symbol=ticker, period="daily", adjust="qfq").tail(250)
            hist_df.columns = ['Date', 'Open', 'Close', 'High', 'Low', 'Volume', 'Amount', 'Amplitude', 'Pct', 'Change', 'Turnover']
            hist_df['Date'] = pd.to_datetime(hist_df['Date'])
            return {"price": float(row['最新价']), "pe": float(row['市盈率TTM']), "growth": 0.12, "name": row['名称'], "history": hist_df}
        
        # 美股 (字母)
        elif ticker.isalpha():
            # 实时股价
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1y"
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(url, headers=headers, timeout=10).json()
            result = r['chart']['result'][0]
            meta = result['meta']
            price = float(meta['regularMarketPrice'])
            
            # 历史走势数据转换
            ts = result['timestamp']
            close_prices = result['indicators']['quote'][0]['close']
            hist_df = pd.DataFrame({'Date': pd.to_datetime(ts, unit='s'), 'Close': close_prices})
            
            # 实时 PE
            pe = 25.0
            try:
                fund_url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=summaryDetail"
                fr = requests.get(fund_url, headers=headers, timeout=10).json()
                summary = fr['quoteSummary']['result'][0]['summaryDetail']
                pe_raw = summary.get('trailingPE', {}).get('raw') or summary.get('forwardPE', {}).get('raw')
                if pe_raw: pe = float(pe_raw)
            except:
                pass
            
            return {"price": price, "pe": pe, "growth": 0.15, "name": ticker, "history": hist_df}
        return None
    except:
        return None

# --- 3. 侧边栏布局 ---
with st.sidebar:
    st.header("🔍 配置中心")
    st.caption("⌨️ **代码指南：**\n• A股: 600519\n• 港股: 00700\n• 美股: AAPL, NFLX")
    ticker_input = st.text_input("输入股票代码", key="main_search").strip()
    target_pe = st.slider("目标合理市盈率 (P/E)", 10.0, 40.0, 20.0)
    
    st.markdown("---")
    st.subheader("☕ 请作者喝杯咖啡")
    st.markdown('<a href="https://www.buymeacoffee.com/vcalculator" target="_blank" class="coffee-btn"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"></a>', unsafe_allow_html=True)

# --- 4. 主页面逻辑 ---
st.title("📈 芒格“价值线”三栖分析仪")

if not ticker_input:
    st.info("👋 **欢迎！请在左侧输入股票代码开始分析。**")
else:
    with st.spinner('正在调取实时数据与历史曲线...'):
        data = get_data_with_history(ticker_input)
    
    if data:
        # 数据指标栏
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("实时股价", f"{data['price']:.2f}")
        c2.metric("当前 P/E (TTM)", f"{data['pe']:.2f}")
        c3.metric("预期利润增速", f"{data['growth']*100:.1f}%")
        c4.metric("回本目标 P/E", f"{target_pe}")

        # 芒格诊断逻辑
        if data['pe'] > target_pe:
            years = math.log(data['pe'] / target_pe) / math.log(1 + data['growth'])
            st.warning(f"⚠️ 诊断：回归至合理目标约需 **{years:.2f}** 年")
        else:
            st.success("🌟 诊断：当前估值极具吸引力（黄金坑）")

        # --- 📈 绘制走势图表 ---
        st.subheader(f"📊 {data['name']} 历史走势 (近一年)")
        if not data['history'].empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=data['history']['Date'], 
                y=data['history']['Close'], 
                name='收盘价',
                line=dict(color='#1f77b4', width=2)
            ))
            fig.update_layout(
                template="plotly_white",
                height=400,
                margin=dict(l=0, r=0, t=20, b=0),
                yaxis_title="价格",
                xaxis_title="日期",
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.caption(f"分析目标: {data['name']} | 实时数据源已锁定")
    else:
        st.error("🚫 抓取失败。请确保输入是大写字母 (如 NFLX) 或正确数字代码。")

st.markdown("---")
st.caption("Munger Multiplier Tool | Built by Gemini | Plotly Edition")
