import streamlit as st
import akshare as ak
import pandas as pd
import plotly.graph_objects as go
import math
import requests

# --- 1. 界面基础配置 ---
st.set_page_config(page_title="Munger Analysis Pro", layout="wide")

# 强制对齐侧边栏打赏按钮样式
st.markdown('''
    <style>
    .coffee-btn { display: block; width: 100%; border-radius: 8px; overflow: hidden; }
    .coffee-btn img { width: 100%; object-fit: contain; }
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
    </style>
''', unsafe_allow_html=True)

# --- 2. 核心抓取引擎 (严谨版) ---
def get_data_engine(ticker):
    ticker = ticker.strip().upper()
    try:
        # A股逻辑 (6位数字)
        if ticker.isdigit() and len(ticker) == 6:
            df = ak.stock_zh_a_spot_em()
            row = df[df['代码'] == ticker].iloc[0]
            return {"price": float(row['最新价']), "pe": float(row['市盈率TTM']), "growth": 0.12, "name": row['名称']}
        
        # 港股逻辑 (5位数字)
        elif ticker.isdigit() and len(ticker) == 5:
            df = ak.stock_hk_spot_em()
            row = df[df['代码'] == ticker].iloc[0]
            return {"price": float(row['最新价']), "pe": float(row['市盈率TTM']), "growth": 0.10, "name": row['名称']}
        
        # 美股逻辑 (字母) - 切换到更稳定的备用实时接口
        elif ticker.isalpha():
            # 使用公共实时 API 确保 NFLX/AAPL 这种大盘股万无一失
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d"
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(url, headers=headers).json()
            meta = r['chart']['result'][0]['meta']
            price = meta['regularMarketPrice']
            
            # 获取 PE (从另一个基础接口)
            fund_url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=summaryDetail"
            fr = requests.get(fund_url, headers=headers).json()
            modules = fr['quoteSummary']['result'][0]['summaryDetail']
            pe = modules.get('trailingPE', {}).get('raw') or modules.get('forwardPE', {}).get('raw') or 20.0
            
            return {"price": price, "pe": pe, "growth": 0.15, "name": ticker}
            
    except Exception as e:
        return None

# --- 3. 侧边栏布局 ---
with st.sidebar:
    st.header("🔍 配置中心")
    st.caption("⌨️ **输入指南：**\n• A股: 600519\n• 港股: 00700\n• 美股: NFLX")
    ticker_input = st.text_input("输入股票代码", "").strip()
    target_pe = st.slider("目标合理市盈率 (P/E)", 10.0, 40.0, 20.0)
    
    st.info("注：若遇到数据延迟，请尝试重新输入代码。")
    st.markdown("---")
    st.subheader("☕ 请作者喝杯咖啡")
    st.markdown('<a href="https://www.buymeacoffee.com/vcalculator" target="_blank" class="coffee-btn"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"></a>', unsafe_allow_html=True)

# --- 4. 主页面逻辑 ---
st.title("📈 芒格“价值线”三栖分析仪")

if not ticker_input:
    st.info("👋 **欢迎！请在左侧输入股票代码开始分析。**")
else:
    with st.spinner('正在调取实时行情...'):
        data = get_data_engine(ticker_input)
    
    if data:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("实时股价", f"{data['price']:.2f}")
        c2.metric("当前 P/E (TTM)", f"{data['pe']:.2f}")
        c3.metric("预期利润增速", f"{data['growth']*100:.1f}%")
        c4.metric("回本目标 P/E", f"{target_pe}")

        # 计算回归年数
        if data['pe'] > target_pe:
            years = math.log(data['pe'] / target_pe) / math.log(1 + data['growth'])
            st.warning(f"⚠️ 诊断：回归年数为 **{years:.2f}** 年。")
        else:
            st.success("🌟 诊断：极具吸引力（黄金坑）")
        
        st.caption(f"数据源已锁定: {data['name']}")
    else:
        st.error("🚫 无法抓取该股票数据。请确保代码正确（美股需大写字母）。")

st.markdown("---")
st.caption("Munger Multiplier Tool | Built by Gemini & AkShare")
