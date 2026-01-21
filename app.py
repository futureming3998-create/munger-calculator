import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
import requests

# --- 1. 样式与中英文配置 ---
st.set_page_config(page_title="Munger Value Pro", layout="wide")
st.markdown('''
    <style>
    .stMetric { background: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    .coffee-btn { display: block; width: 100%; border-radius: 10px; overflow: hidden; margin-top: 10px; transition: transform 0.3s; }
    .coffee-btn:hover { transform: scale(1.02); }
    .footer-text { text-align: center; color: #666; padding: 20px; font-size: 0.8rem; border-top: 1px solid #333; margin-top: 50px; }
    </style>
''', unsafe_allow_html=True)

LANG = {
    "中文": {
        "title": "📈 芒格“价值线”深度分析仪",
        "welcome": "👋 欢迎！输入美股代码开始。由 Polygon 官方数据驱动。",
        "sb_cfg": "🔍 配置中心",
        "ticker_label": "输入美股代码 (如 COST, AAPL)",
        "target_pe": "目标合理 P/E",
        "metric_growth": "复合年化增速 (CAGR)",
        "diag_years": "⚠️ 诊断：回归合理估值约需 **{:.2f}** 年",
        "diag_gold": "🌟 诊断：当前估值极具吸引力",
        "err_limit": "🐢 访问太快！API 每分钟限5次请求，请等 15 秒再刷新。",
        "err_missing": "🚫 该股票财报数据不全，无法计算平滑增速。",
        "coffee": "☕ 请作者喝杯咖啡",
        "footer": "Munger Multiplier | Official Data Mode | 2026"
    },
    "English": {
        "title": "📈 Munger Value Line Pro",
        "welcome": "👋 Welcome! Enter a ticker. Powered by Polygon.io.",
        "sb_cfg": "🔍 Configuration",
        "ticker_label": "Enter Ticker (e.g. COST, AAPL)",
        "target_pe": "Target P/E Ratio",
        "metric_growth": "Profit CAGR",
        "diag_years": "⚠️ Diagnosis: ~**{:.2f}** years to target",
        "diag_gold": "🌟 Diagnosis: Highly Attractive",
        "err_limit": "🐢 Slow down! API limit reached. Wait 15s.",
        "err_missing": "🚫 Insufficient financial data.",
        "coffee": "☕ Buy me a coffee",
        "footer": "Munger Multiplier | Official Data Mode | 2026"
    }
}

top_col1, top_col2 = st.columns([7, 1.2])
with top_col2:
    sel_lang = st.selectbox("", ["中文", "English"], label_visibility="collapsed")
    t = LANG[sel_lang]
with top_col1:
    st.title(t["title"])

# --- 2. 自适应数据引擎 (修复 COST 报错逻辑) ---
@st.cache_data(ttl=3600)
def fetch_munger_data_final(symbol, api_key):
    try:
        # 价格
        p_res = requests.get(f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?apiKey={api_key}")
        if p_res.status_code == 429: return "LIMIT"
        price = p_res.json()['results'][0]['c']

        # 财报抓取 (自适应年份)
        f_url = f"https://api.polygon.io/X/reference/financials?ticker={symbol}&timeframe=annual&limit=5&apiKey={api_key}"
        f_res = requests.get(f_url).json().get('results', [])
        
        # 数据清洗：只取有净利润和年份记录的点
        valid_data = []
        for f in f_res:
            try:
                val = f['financials']['income_statement']['net_income_loss']['value']
                yr = f.get('calendar_year')
                if val is not None and yr is not None:
                    valid_data.append({'val': val, 'yr': int(yr)})
            except: continue
        
        valid_data.sort(key=lambda x: x['yr'], reverse=True)
        if len(valid_data) < 2: return "MISSING"

        # 动态计算跨度 n
        n = valid_data[0]['yr'] - valid_data[-1]['yr']
        if n < 1: n = 1 

        # CAGR 计算         v_end, v_start = valid_data[0]['val'], valid_data[-1]['val']
        growth = (v_end / v_start)**(1/n) - 1 if (v_end > 0 and v_start > 0) else (v_end - v_start)/abs(v_start)/n

        # 获取最新 PE
        eps = f_res[0]['financials']['income_statement']['basic_earnings_per_share']['value']
        pe = price / eps if eps > 0 else 0

        # 10年价格轨迹
        h_res = requests.get(f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/2016-01-01/2026-12-31?apiKey={api_key}").json().get('results', [])
        
        return {"price": price, "pe": pe, "growth": growth, "history": pd.DataFrame(h_res), "n": n}
    except: return "ERROR"

# --- 3. 侧边栏 (彻底删除 Key 输入框) ---
with st.sidebar:
    st.header(t["sb_cfg"])
    ticker = st.text_input(t["ticker_label"], "").strip().upper()
    target_pe_val = st.slider(t["target_pe"], 10.0, 50.0, 20.0)
    st.markdown("---")
    st.subheader(t["coffee"])
    st.markdown('<a href="https://www.buymeacoffee.com/vcalculator" target="_blank" class="coffee-btn"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" width="100%"></a>', unsafe_allow_html=True)

# --- 4. 主逻辑渲染 ---
if not ticker:
    st.info(t["welcome"])
else:
    # 直接调取后台 Secrets
    p_key = st.secrets.get("POLY_KEY")
    if not p_key:
        st.error("🔑 配置错误：请在 Streamlit 后台 Secrets 填入 POLY_KEY")
    else:
        with st.spinner('🚀 正在提取深度财报数据...'):
            data = fetch_munger_data_final(ticker, p_key)
        
        if data == "LIMIT": st.error(t["err_limit"])
        elif data in ["MISSING", "ERROR"]: st.error(t["err_missing"])
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("当前价格", f"${data['price']:.2f}")
            c2.metric("P/E (TTM)", f"{data['pe']:.2f}")
            c3.metric(t["metric_growth"], f"{data['growth']*100:.2f}%", help=f"基于过去 {data['n']} 年跨度计算")
            c4.metric("目标 P/E", f"{target_pe_val}")

            if data['growth'] > 0:
                if data['pe'] <= target_pe_val: st.success(t["diag_gold"])
                else:
                    y = math.log(data['pe'] / target_pe_val) / math.log(1 + data['growth'])
                    st.warning(t["diag_years"].format(y))
            else: st.error("⚠️ 利润增速为负，不适用复利模型。")

            st.subheader(f"📊 {ticker} 10年对数轨迹图")
            df_h = data['history']
            df_h['t'] = pd.to_datetime(df_h['t'], unit='ms')
            fig = go.Figure(go.Scatter(x=df_h['t'], y=df_h['c'], line=dict(color='#1f77b4', width=2)))
            fig.update_layout(yaxis_type="log", template="plotly_white", height=450, margin=dict(l=0,r=0,t=20,b=0))
            st.plotly_chart(fig, use_container_width=True)

st.markdown(f'<div class="footer-text">{t["footer"]}</div>', unsafe_allow_html=True)
