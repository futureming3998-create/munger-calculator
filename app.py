import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
import requests

# --- 1. 基础配置 ---
st.set_page_config(page_title="Munger Value Pro", layout="wide")
st.markdown('<style>.stMetric { background: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; } .footer-text { text-align: center; color: #666; padding: 20px; font-size: 0.8rem; border-top: 1px solid #333; margin-top: 50px; }</style>', unsafe_allow_html=True)

# --- 2. 语言字典 ---
LANG = {
    "中文": {
        "title": "📈 芒格“价值线”深度分析仪",
        "ticker_label": "输入美股代码 (如 COST, AAPL)",
        "metric_growth": "复合年化增速 (CAGR)",
        "diag_years": "⚠️ 诊断：回归合理估值约需 **{:.2f}** 年",
        "diag_gold": "🌟 诊断：当前估值极具吸引力",
        "err_missing": "🚫 无法分析：财报数据抓取失败或格式不兼容。",
        "footer": "Munger Multiplier | Official Data Mode | 2026"
    },
    "English": {
        "title": "📈 Munger Value Line Pro",
        "ticker_label": "Enter Ticker (e.g. COST, AAPL)",
        "metric_growth": "Profit CAGR",
        "diag_years": "⚠️ Diagnosis: ~**{:.2f}** years to target",
        "diag_gold": "🌟 Diagnosis: Highly Attractive",
        "err_missing": "🚫 Analysis Failed: Insufficient or incompatible financial data.",
        "footer": "Munger Multiplier | Official Data Mode | 2026"
    }
}

sel_lang = st.sidebar.selectbox("Language", ["中文", "English"])
t = LANG[sel_lang]
st.title(t["title"])

# --- 3. 核心引擎：工业级数据清洗 (彻底修复逻辑) ---
@st.cache_data(ttl=3600)
def fetch_munger_data_industrial(symbol, api_key):
    try:
        # A. 实时价格
        p_res = requests.get(f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?apiKey={api_key}").json()
        price = p_res['results'][0]['c']

        # B. 深度财报抓取
        f_url = f"https://api.polygon.io/X/reference/financials?ticker={symbol}&timeframe=annual&limit=5&apiKey={api_key}"
        f_data = requests.get(f_url).json().get('results', [])
        
        valid_history = []
        for report in f_data:
            try:
                # 修复核心：精准定位 Polygon 的嵌套数据路径
                # 路径为: financials -> income_statement -> net_income_loss -> value
                income = report['financials']['income_statement']['net_income_loss']['value']
                year = report.get('fiscal_year') or report.get('calendar_year')
                if income is not None and year is not None:
                    valid_history.append({'income': float(income), 'year': int(year)})
            except (KeyError, TypeError): continue
        
        # 按年份排序（最新在前）
        valid_history.sort(key=lambda x: x['year'], reverse=True)
        if len(valid_history) < 2: return "MISSING"

        # C. 科学计算
        latest = valid_history[0]
        oldest = valid_history[-1]
        n = latest['year'] - oldest['year']
        if n < 1: n = 1 # 至少按1年计算

        v_end, v_start = latest['income'], oldest['income']
        # CAGR 公式         if v_end > 0 and v_start > 0:
            growth = (v_end / v_start)**(1/n) - 1
        else:
            growth = (v_end - v_start) / abs(v_start) / n

        # 最新 PE 计算 (使用最新一份财报的 EPS)
        try:
            eps = f_data[0]['financials']['income_statement']['basic_earnings_per_share']['value']
            pe = price / eps if eps > 0 else 0
        except: pe = 0

        # D. 10年价格轨迹
        h_res = requests.get(f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/2016-01-01/2026-12-31?apiKey={api_key}").json().get('results', [])
        
        return {"price": price, "pe": pe, "growth": growth, "history": pd.DataFrame(h_res), "n": n}
    except: return "ERROR"

# --- 4. 侧边栏 ---
with st.sidebar:
    ticker = st.text_input(t["ticker_label"], "").strip().upper()
    target_pe_val = st.slider("目标合理 P/E", 10.0, 50.0, 20.0)
    st.markdown("---")
    st.markdown('<a href="https://www.buymeacoffee.com" target="_blank">☕ 请作者喝杯咖啡</a>', unsafe_allow_html=True)

# --- 5. 主逻辑渲染 ---
if ticker:
    p_key = st.secrets.get("POLY_KEY")
    if not p_key:
        st.error("🔑 部署错误：后台未配置 POLY_KEY")
    else:
        with st.spinner('数据穿透中...'):
            data = fetch_munger_data_industrial(ticker, p_key)
        
        if data in ["MISSING", "ERROR"]:
            st.error(t["err_missing"])
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("当前价格", f"${data['price']:.2f}")
            c2.metric("P/E (TTM)", f"{data['pe']:.2f}")
            c3.metric(t["metric_growth"], f"{data['growth']*100:.2f}%", help=f"基于过去 {data['n']} 年数据计算")
            c4.metric("目标 P/E", f"{target_pe_val}")

            if data['growth'] > 0 and data['pe'] > 0:
                if data['pe'] <= target_pe_val: st.success(t["diag_gold"])
                else:
                    y = math.log(data['pe'] / target_pe_val) / math.log(1 + data['growth'])
                    st.warning(t["diag_years"].format(y))
            
            df_h = data['history']
            df_h['t'] = pd.to_datetime(df_h['t'], unit='ms')
            fig = go.Figure(go.Scatter(x=df_h['t'], y=df_h['c'], name="Price"))
            fig.update_layout(yaxis_type="log", title=f"{ticker} 10Y Price (Log Scale)", template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

st.markdown(f'<div class="footer-text">{t["footer"]}</div>', unsafe_allow_html=True)
