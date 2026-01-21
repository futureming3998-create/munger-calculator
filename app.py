import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
import requests

# --- 1. UI 风格锁定 ---
st.set_page_config(page_title="Munger Analysis Pro", layout="wide")

# 侧边栏 CSS 强制对齐
st.markdown('''
    <style>
    .stMetric { background: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    div[data-testid="stMetricValue"] > div { color: #00ffcc !important; }
    .coffee-btn { display: block; width: 100%; border-radius: 8px; overflow: hidden; margin-top: 15px; }
    </style>
''', unsafe_allow_html=True)

# --- 2. 右上角语言切换器 ---
c_top1, c_top2 = st.columns([8, 1.2])
with top_col2 if 'top_col2' in locals() else c_top2: # 兼容性处理
    selected_lang = st.selectbox("", ["中文", "English"], label_visibility="collapsed")

# 语言字典
L = {
    "中文": {
        "title": "📈 芒格“价值线”官方数据分析仪",
        "guide": "### 📖 快速上手：\n1. **API Key**：填入你昨晚申请的 Key。\n2. **代码**：输入 AAPL, MSFT, COST 等。\n3. **原则**：只使用 Alpha Vantage 提供的真实财报数据。",
        "sb_key": "🔑 输入你的 API Key",
        "sb_ticker": "输入股票代码 (如 COST)",
        "diag_years": "⚠️ 诊断：回归合理估值约需 **{:.2f}** 年",
        "diag_gold": "🌟 诊断：当前估值已低于目标（极具吸引力）",
        "footer": "Munger Multiplier Tool | Official Alpha Vantage Mode",
        "err": "🚫 获取失败。请检查 Key 是否正确，或该股是否缺少财报数据。"
    },
    "English": {
        "title": "📈 Munger Value Pro (Official API)",
        "guide": "### 📖 Quick Start:\n1. **API Key**: Enter the key you got last night.\n2. **Ticker**: Enter AAPL, MSFT, COST, etc.\n3. **Rule**: Real financial data only via Alpha Vantage.",
        "sb_key": "🔑 Enter API Key",
        "sb_ticker": "Enter Ticker (e.g. COST)",
        "diag_years": "⚠️ Diagnosis: ~**{:.2f}** years to target",
        "diag_gold": "🌟 Diagnosis: Highly Attractive (Below Target)",
        "footer": "Munger Multiplier Tool | Official Alpha Vantage Mode",
        "err": "🚫 Fetch failed. Check your Key or Ticker availability."
    }
}[selected_lang]

# --- 3. 侧边栏配置 ---
with st.sidebar:
    st.header("🔍 配置中心")
    api_key = st.text_input(L["sb_key"], type="password")
    ticker = st.text_input(L["sb_ticker"], "").strip().upper()
    target_pe = st.slider("目标合理 P/E", 10.0, 50.0, 20.0)
    st.markdown("---")
    st.subheader("☕ 请作者喝杯咖啡")
    st.markdown('<a href="https://www.buymeacoffee.com/vcalculator" target="_blank" class="coffee-btn"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"></a>', unsafe_allow_html=True)

# --- 4. 真实数据提取逻辑 ---
def get_official_financials(symbol, key):
    try:
        # 获取基础财务指标
        ov_url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={key}'
        ov_data = requests.get(ov_url).json()
        
        # 获取实时价格 (Global Quote)
        q_url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={key}'
        q_data = requests.get(q_url).json()['Global Quote']
        
        # 严格提取真实数据，绝不兜底
        pe = float(ov_data['PERatio'])
        growth = float(ov_data['QuarterlyEarningsGrowthYOY'])
        price = float(q_data['05. price'])
        name = ov_data['Name']
        
        return {"price": price, "pe": pe, "growth": growth, "name": name}
    except:
        return None

# --- 5. 主页面展示 ---
st.title(L["title"])

if not ticker:
    st.info("👋 欢迎回来！请在左侧填入 Key 和代码开始分析。")
    st.markdown(L["guide"]) # 首页指南
elif not api_key:
    st.warning("⚠️ 请输入你的 API Key 以启用真实数据抓取。")
else:
    with st.spinner('正在链接官方财报数据库...'):
        data = get_official_financials(ticker, api_key)
    
    if data:
        # 指标卡片
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("实时股价", f"${data['price']:.2f}")
        c2.metric("真实 P/E (TTM)", f"{data['pe']:.2f}")
        c3.metric("真实利润增速", f"{data['growth']*100:.1f}%")
        c4.metric("回本目标 P/E", f"{target_pe}")

        # 计算年数
        if data['pe'] > target_pe and data['growth'] > 0:
            years = math.log(data['pe'] / target_pe) / math.log(1 + data['growth'])
            st.warning(L["diag_years"].format(years))
        else:
            st.success(L["diag_gold"])
        
        st.caption(f"数据源确认：{data['name']} (Alpha Vantage Real-time)")
    else:
        st.error(L["err"])

# --- 6. 底部版权 ---
st.markdown("---")
st.caption(L["footer"])
