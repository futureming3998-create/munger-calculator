import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
import requests
import time

# --- 1. 配置与样式 ---
st.set_page_config(page_title="Munger Value Pro", layout="wide")
st.markdown('''
    <style>
    .stMetric { background: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    .coffee-btn { display: block; width: 100%; border-radius: 10px; overflow: hidden; margin-top: 10px; transition: transform 0.3s; }
    .coffee-btn:hover { transform: scale(1.02); }
    .footer-text { text-align: center; color: #666; padding: 20px; font-size: 0.8rem; border-top: 1px solid #333; margin-top: 50px; }
    </style>
''', unsafe_allow_html=True)

# --- 2. 语言字典 ---
LANG = {
    "中文": {
        "title": "📈 芒格“价值线”深度分析仪",
        "welcome": "👋 欢迎！输入美股代码开始。本工具由 Polygon 官方数据驱动。",
        "sb_cfg": "🔍 配置中心",
        "ticker_label": "输入美股代码 (如 COST)",
        "target_pe": "目标合理 P/E",
        "metric_growth": "5年复合增速 (CAGR)",
        "diag_years": "⚠️ 诊断：回归合理估值约需 **{:.2f}** 年",
        "err_limit": "🐢 访问太快啦！Polygon 免费版每分钟限5次请求，请等 15 秒再刷新。",
        "err_missing": "🚫 该股票财报数据不足 5 年，无法计算平滑增速。",
        "coffee": "☕ 请作者喝杯咖啡",
        "footer": "Munger Multiplier | Official Data | 2026"
    },
    "English": {
        "title": "📈 Munger Value Line Pro",
        "welcome": "👋 Welcome! Enter a ticker to start. Powered by Polygon.io.",
        "sb_cfg": "🔍 Configuration",
        "ticker_label": "Enter Ticker (e.g. COST)",
        "target_pe": "Target P/E Ratio",
        "metric_growth": "5Y CAGR",
        "diag_years": "⚠️ Diagnosis: ~**{:.2f}** years to target",
        "err_limit": "🐢 Slow down! API limit (5/min) reached. Please wait 15s.",
        "err_missing": "🚫 Insufficient financial history (5Y required).",
        "coffee": "☕ Buy me a coffee",
        "footer": "Munger Multiplier | Official Data | 2026"
    }
}

top_col1, top_col2 = st.columns([7, 1.2])
with top_col2:
    sel_lang = st.selectbox("", ["中文", "English"], label_visibility="collapsed")
    t = LANG[sel_lang]
with top_col1:
    st.title(t["title"])

# --- 3. 带缓存的数据抓取引擎 ---
@st.cache_data(ttl=3600)  # 相同股票 1 小时内只查一次 API
def fetch_munger_data_safe(symbol, api_key):
    try:
        # 1. 价格请求
        p_resp = requests.get(f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?apiKey={api_key}")
        if p_resp.status_code == 429: return "LIMIT"
        price = p_resp.json()['results'][0]['c']

        # 2. 5年财报请求
        f_resp = requests.get(f"https://api.polygon.io/X/reference/financials?ticker={symbol}&timeframe=annual&limit=5&apiKey={api_key}")
        if f_resp.status_code == 429: return "LIMIT"
        fins = f_resp.json().get('results', [])
        if len(fins) < 2: return "MISSING"

        # 计算 PE 和 CAGR
        latest = fins[0]['financials']['income_statement']
        eps = latest.get('basic_earnings_per_share', {}).get('value', 0)
        pe = price / eps if eps > 0 else 0
        
        n = len(fins) - 1
        v_final = fins[0]['financials']['income_statement']['net_income_loss']['value']
        v_start = fins[-1]['financials']['income_statement']['net_income_loss']['value']
        
        # 科学 CAGR 计算 
        if v_final > 0 and v_start > 0:
            growth = (v_final / v_start)**(1/n) - 1
        else:
            growth = (v_final - v_start) / abs(v_start)

        # 3. 10年价格数据
        h_resp = requests.get(f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/2016-01-01/2026-12-31?apiKey={api_key}")
        h_data = pd.DataFrame(h_resp.json().get('results', []))

        return {"price": price, "pe": pe, "growth": growth, "history": h_data, "n": n+1}
    except:
        return "ERROR"

# --- 4. 侧边栏与打赏 ---
with st.sidebar:
    st.header(t["sb_cfg"])
    ticker = st.text_input(t["ticker_label"], "").strip().upper()
    target_pe_val = st.slider(t["target_pe"], 10.0, 50.0, 20.0)
    st.markdown("---")
    st.subheader(t["coffee"])
    st.markdown('<a href="https://www.buymeacoffee.com/vcalculator" target="_blank" class="coffee-btn"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" width="100%"></a>', unsafe_allow_html=True)

# --- 5. 主视图 ---
if not ticker:
    st.info(t["welcome"])
else:
    p_key = st.secrets.get("POLY_KEY")
    if not p_key:
        st.error("🔑 Secrets Error: POLY_KEY not found in backend.")
    else:
        with st.spinner('🚀 正在穿透财报数据...'):
            data = fetch_munger_data_safe(ticker, p_key)
        
        if data == "LIMIT":
            st.error(t["err_limit"])
        elif data == "MISSING" or data == "ERROR":
            st.error(t["err_missing"])
        else:
            # 渲染结果...
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("价格", f"${data['price']:.2f}")
            c2.metric("P/E (TTM)", f"{data['pe']:.2f}")
            c3.metric(t["metric_growth"], f"{data['growth']*100:.2f}%")
            c4.metric("目标 P/E", f"{target_pe_val}")

            if data['growth'] > 0:
                if data['pe'] <= target_pe_val:
                    st.success("🌟 当前估值极具吸引力")
                else:
                    y = math.log(data['pe'] / target_pe_val) / math.log(1 + data['growth'])
                    st.warning(t["diag_years"].format(y))

            # 10年价格对数曲线
            st.subheader(f"📊 {ticker} 10年价格轨迹 (Log Scale)")
            df_h = data['history']
            df_h['t'] = pd.to_datetime(df_h['t'], unit='ms')
            fig = go.Figure(go.Scatter(x=df_h['t'], y=df_h['c'], line=dict(color='#1f77b4', width=2)))
            fig.update_layout(yaxis_type="log", template="plotly_white", height=450, margin=dict(l=0,r=0,t=20,b=0))
            st.plotly_chart(fig, use_container_width=True)

st.markdown(f'<div class="footer-text">{t["footer"]}</div>', unsafe_allow_html=True)
