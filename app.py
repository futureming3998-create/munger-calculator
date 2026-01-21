import streamlit as st
import akshare as ak
import pandas as pd
import plotly.graph_objects as go
import math

# --- 1. 语言字典配置 [cite: 2026-01-05] ---
LANG = {
    "中文": {
        "title": "📈 芒格“价值线”三栖分析仪",
        "welcome_info": "👋 **欢迎！请在左侧输入股票代码开始分析。**",
        "guide_header": "### 快速上手指南：",
        "guide_1": "1. **输入代码**：A股(600519), 港股(00700), 美股(AAPL)。",
        "guide_2": "2. **设定目标**：调整滑块选择你认为合理的“目标市盈率”。",
        "guide_3": "3. **看懂结论**：系统自动识别市场并计算回归年数。",
        "sidebar_cfg": "🔍 配置中心",
        "input_label": "输入股票代码",
        "target_pe_label": "目标合理市盈率 (P/E)",
        "metric_price": "实时股价",
        "metric_pe": "当前 P/E (TTM)",
        "metric_growth": "预期利润增速",
        "metric_target": "回本目标 P/E",
        "diag_gold_pit": "🌟 诊断：极具吸引力（黄金坑）",
        "diag_years_msg": "回归年数为 **{:.2f}** 年。",
        "err_no_data": "🚫 无法抓取数据，请检查代码格式或重试。",
        "coffee_header": "☕ 请作者喝杯咖啡"
    }
}
t = LANG["中文"]

st.set_page_config(page_title="Munger Analysis Pro", layout="wide")

# --- 2. 布局逻辑：标题与语言 (UI复原) ---
top_col1, top_col2 = st.columns([8, 2])
with top_col2:
    st.selectbox("", ["中文"], label_visibility="collapsed") # 保持位置占位

with top_col1:
    st.title(t["title"])

# --- 3. 侧边栏配置与打赏按钮对齐 ---
with st.sidebar:
    st.header(t["sidebar_cfg"])
    st.caption("⌨️ **输入指南：**\n• A股直接输入 (如 600519)\n• 港股输入5位 (如 00700)\n• 美股输入字母 (如 AAPL)")
    ticker_input = st.text_input(t["input_label"], "").strip()
    target_pe = st.slider(t["target_pe_label"], 10.0, 40.0, 20.0)

    st.markdown("---")
    st.subheader(t["coffee_header"])
    # 强制 100% 宽度对齐样式
    st.markdown(f'''
        <style>
        .coffee-btn {{ display: block; width: 100%; border-radius: 8px; overflow: hidden; }}
        .coffee-btn img {{ width: 100%; object-fit: contain; }}
        </style>
        <a href="https://www.buymeacoffee.com/vcalculator" target="_blank" class="coffee-btn">
            <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png">
        </a>
    ''', unsafe_allow_html=True)

# --- 4. AkShare 核心抓取引擎 (多市场适配) ---
@st.cache_data(ttl=600)
def get_market_data(ticker):
    try:
        # 美股逻辑
        if ticker.isalpha():
            df = ak.stock_us_spot_em()
            row = df[df['代码'].str.contains(ticker, case=False, na=False)].iloc[0]
            return {"price": row['最新价'], "pe": row['市盈率'], "growth": 0.15, "name": row['名称']}
        # A股逻辑
        elif len(ticker) == 6:
            df = ak.stock_zh_a_spot_em()
            row = df[df['代码'] == ticker].iloc[0]
            return {"price": row['最新价'], "pe": row['市盈率TTM'], "growth": 0.12, "name": row['名称']}
        # 港股逻辑
        elif len(ticker) == 5:
            df = ak.stock_hk_spot_em()
            row = df[df['代码'] == ticker].iloc[0]
            return {"price": row['最新价'], "pe": row['市盈率TTM'], "growth": 0.10, "name": row['名称']}
        return None
    except:
        return None

# --- 5. 主运行逻辑 ---
if not ticker_input:
    st.info(t["welcome_info"])
    st.markdown(t["guide_header"])
    st.write(t["guide_1"])
    st.write(t["guide_2"])
    st.write(t["guide_3"])
else:
    data = get_market_data(ticker_input)
    if data and data['price']:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t["metric_price"], f"{data['price']:.2f}")
        c2.metric(t["metric_pe"], f"{data['pe']:.2f}" if data['pe'] else "N/A")
        c3.metric(t["metric_growth"], f"{data['growth']*100:.1f}%")
        c4.metric(t["metric_target"], f"{target_pe}")

        # 芒格回归计算核心逻辑 [cite: 2026-01-05]
        if data['pe'] and data['pe'] > target_pe:
            pe_ratio = data['pe'] / target_pe
            years = math.log(pe_ratio) / math.log(1 + data['growth'])
            st.warning(t["diag_years_msg"].format(years))
        else:
            st.success(t["diag_gold_pit"])
            
        st.caption(f"当前分析对象: {data['name']}")
    else:
        st.error(t["err_no_data"])

st.markdown("---")
st.caption("Munger Multiplier Tool | Powered by AkShare & Gemini")
