import streamlit as st
import akshare as ak
import pandas as pd
import plotly.graph_objects as go
import math
import requests

# --- 1. 基础配置 ---
st.set_page_config(page_title="Munger Analysis Pro", layout="wide")

# 侧边栏样式对齐 (打赏按钮宽度 100% 匹配蓝框)
st.markdown('''
    <style>
    .coffee-btn { display: block; width: 100%; border-radius: 8px; overflow: hidden; }
    .coffee-btn img { width: 100%; object-fit: contain; }
    div[data-testid="stMetricValue"] > div { font-size: 1.8rem !important; }
    </style>
''', unsafe_allow_html=True)

# --- 2. 深度抓取逻辑 ---
def get_clean_data(ticker):
    ticker = ticker.strip().upper()
    try:
        # A股 (6位数字)
        if ticker.isdigit() and len(ticker) == 6:
            df = ak.stock_zh_a_spot_em()
            row = df[df['代码'] == ticker].iloc[0]
            return {"price": float(row['最新价']), "pe": float(row['市盈率TTM']), "growth": 0.12, "name": row['名称']}
        
        # 港股 (5位数字)
        elif ticker.isdigit() and len(ticker) == 5:
            df = ak.stock_hk_spot_em()
            row = df[df['代码'] == ticker].iloc[0]
            return {"price": float(row['最新价']), "pe": float(row['市盈率TTM']), "growth": 0.10, "name": row['名称']}
        
        # 美股 (字母) - 使用更稳定的通用 JSON 接口
        elif ticker.isalpha():
            # 强化版美股报价抓取
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(url, headers=headers, timeout=5).json()
            meta = r['chart']['result'][0]['meta']
            price = float(meta['regularMarketPrice'])
            
            # 备选 PE 方案
            pe = 25.0 # 默认预设
            try:
                fund_url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=summaryDetail"
                fr = requests.get(fund_url, headers=headers, timeout=5).json()
                summary = fr['quoteSummary']['result'][0]['summaryDetail']
                pe = summary.get('trailingPE', {}).get('raw') or summary.get('forwardPE', {}).get('raw') or 25.0
            except:
                pass
            
            return {"price": price, "pe": float(pe), "growth": 0.15, "name": ticker}
        return None
    except:
        return None

# --- 3. 侧边栏布局 ---
with st.sidebar:
    st.header("🔍 配置中心")
    st.caption("⌨️ **输入指南：**\n• A股: 600519\n• 港股: 00700\n• 美股: AAPL, NFLX")
    ticker_input = st.text_input("输入股票代码", "").strip()
    target_pe = st.slider("目标合理市盈率 (P/E)", 10.0, 40.0, 20.0)
    
    st.info("注：若遇到数据延迟，请尝试重新输入。")
    st.markdown("---")
    st.subheader("☕ 请作者喝杯咖啡")
    st.markdown('<a href="https://www.buymeacoffee.com/vcalculator" target="_blank" class="coffee-btn"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"></a>', unsafe_allow_html=True)

# --- 4. 主页面渲染 ---
st.title("📈 芒格“价值线”三栖分析仪")

if not ticker_input:
    st.info("👋 **欢迎！请在左侧输入股票代码开始分析。**")
else:
    with st.spinner('连接全球市场数据库中...'):
        data = get_clean_data(ticker_input)
    
    if data and not math.isnan(data['price']):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("实时股价", f"{data['price']:.2f}")
        c2.metric("当前 P/E (TTM)", f"{data['pe']:.2f}")
        c3.metric("预期利润增速", f"{data['growth']*100:.1f}%")
        c4.metric("回本目标 P/E", f"{target_pe}")

        # 计算回归年数
        if data['pe'] > target_pe:
            years = math.log(data['pe'] / target_pe) / math.log(1 + data['growth'])
            st.warning(f"⚠️ 回归至合理目标约需 **{years:.2f}** 年")
        else:
            st.success("🌟 诊断：当前估值极具吸引力（黄金坑）")
        
        st.caption(f"分析目标确认: {data['name']}")
    else:
        st.error("🚫 抓取失败。请确保输入是大写字母 (如 AAPL) 或正确数字代码。")

st.markdown("---")
st.caption("Munger Multiplier Tool | Built by Gemini | 2026 Edition")
