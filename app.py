import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math

# --- 1. 页面配置与样式 ---
st.set_page_config(page_title="Munger Analysis Pro", layout="wide")
st.title("📈 芒格“价值线”深度分析仪")

# --- 2. 侧边栏配置 ---
with st.sidebar:
    st.header("🔍 配置中心")
    ticker = st.text_input("输入美股代码 (如 COST, AAPL)", "AAPL").strip().upper()
    target_pe = st.slider("目标合理 P/E", 10.0, 50.0, 20.0)
    st.markdown("---")
    st.write("☕ 请作者喝杯咖啡")

# --- 3. 核心数据抓取引擎 (自适应逻辑 + Bearer 验证) ---
@st.cache_data(ttl=3600)
def fetch_data(symbol, api_key):
    # 使用 Bearer Token 验证，解决之前 results 缺失的 Bug
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        # A. 抓取当前价格
        p_resp = requests.get(f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev", headers=headers).json()
        if 'results' not in p_resp: return "未找到该股票价格"
        price = p_resp['results'][0]['c']

        # B. 抓取最近 5 年年度财报
        f_url = f"https://api.polygon.io/X/reference/financials?ticker={symbol}&timeframe=annual&limit=5"
        f_resp = requests.get(f_url, headers=headers).json()
        f_results = f_resp.get('results', [])
        
        valid_fins = []
        for r in f_results:
            try:
                val = r['financials']['income_statement']['net_income_loss']['value']
                year = r.get('fiscal_year') or r.get('calendar_year')
                if val is not None and year is not None:
                    valid_fins.append({'income': float(val), 'year': int(year)})
            except: continue
            
        if len(valid_fins) < 2: return "财报历史数据不足"
        
        # 排序并计算 CAGR
        valid_fins.sort(key=lambda x: x['year'])
        n = valid_fins[-1]['year'] - valid_fins[0]['year'] or 1
        
        # 科学增速计算 
        v_end, v_start = valid_fins[-1]['income'], valid_fins[0]['income']
        if v_end > 0 and v_start > 0:
            growth = (v_end / v_start)**(1/n) - 1
        else:
            growth = (v_end - v_start) / abs(v_start) / n

        # 最新 PE
        eps = f_results[0]['financials']['income_statement']['basic_earnings_per_share']['value']
        pe = price / eps if eps > 0 else 0

        # C. 抓取 10 年历史价格 (用于绘图)
        h_url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/2016-01-01/2026-12-31"
        h_resp = requests.get(h_url, headers=headers).json()
        h_data = h_resp.get('results', [])

        return {"price": price, "pe": pe, "growth": growth, "history": h_data, "n": n}
    except Exception as e:
        return f"接口连接失败: {str(e)}"

# --- 4. 主视图渲染 ---
key = st.secrets.get("POLY_KEY")

if not key:
    st.error("🔑 后台配置错误：未在 Secrets 中发现 POLY_KEY")
elif ticker:
    with st.spinner('正在调取官方财报数据...'):
        data = fetch_data(ticker, key)
    
    if isinstance(data, str):
        st.warning(f"💡 {data}")
    else:
        # A. 指标看板
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("价格", f"${data['price']:.2f}")
        c2.metric("P/E (TTM)", f"{data['pe']:.2f}")
        c3.metric("利润年化增速", f"{data['growth']*100:.2f}%")
        c4.metric("目标 P/E", f"{target_pe}")

        # B. 诊断逻辑
        if data['growth'] > 0 and data['pe'] > 0:
            if data['pe'] <= target_pe:
                st.success("🌟 当前估值极具吸引力，低于你的目标 PE")
            else:
                years = math.log(data['pe'] / target_pe) / math.log(1 + data['growth'])
                st.warning(f"⚠️ 诊断：回归合理估值约需 {years:.2f} 年")
        
        # C. 10 年价格对数轨迹图
        if data['history']:
            st.subheader(f"📊 {ticker} 10年价格对数轨迹")
            df = pd.DataFrame(data['history'])
            df['date'] = pd.to_datetime(df['t'], unit='ms')
            fig = go.Figure(go.Scatter(x=df['date'], y=df['c'], line=dict(color='#1f77b4', width=2)))
            fig.update_layout(yaxis_type="log", template="plotly_white", height=500, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption("Munger Multiplier | Official Data Mode | 2026")
