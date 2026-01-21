import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math

# 1. 基础配置
st.set_page_config(page_title="Munger Analysis")
st.title("📈 芒格“价值线”深度分析仪")

# 2. 侧边栏
with st.sidebar:
    st.header("🔍 配置中心")
    ticker = st.text_input("输入美股代码 (如 COST, AAPL)", "").strip().upper()
    target_pe = st.slider("目标合理 P/E", 10.0, 50.0, 20.0)
    st.markdown("---")
    st.write("☕ 请作者喝杯咖啡")

# 3. 核心抓取逻辑
@st.cache_data(ttl=3600)
def get_stock_data(symbol, api_key):
    try:
        # 获取价格
        p_res = requests.get(f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?apiKey={api_key}").json()
        price = p_res['results'][0]['c']
        
        # 获取财报 (limit=10 增加数据容错)
        f_url = f"https://api.polygon.io/X/reference/financials?ticker={symbol}&timeframe=annual&limit=10&apiKey={api_key}"
        f_res = requests.get(f_url).json().get('results', [])
        
        history = []
        for r in f_res:
            try:
                # 严格定位利润和年份
                v = r['financials']['income_statement']['net_income_loss']['value']
                y = r.get('fiscal_year') or r.get('calendar_year')
                if v is not None and y is not None:
                    history.append({'v': float(v), 'y': int(y)})
            except: continue
            
        history.sort(key=lambda x: x['y'], reverse=True)
        if len(history) < 2: return "数据不足"
        
        # 计算增速 (CAGR)
        latest, oldest = history[0], history[-1]
        n = latest['y'] - oldest['y']
        n = n if n > 0 else 1
        growth = (latest['v'] / oldest['v'])**(1/n) - 1 if (latest['v'] > 0 and oldest['v'] > 0) else 0
        
        # 计算 PE
        eps = f_res[0]['financials']['income_statement']['basic_earnings_per_share']['value']
        pe = price / eps if eps > 0 else 0
        
        # 10年价格曲线
        h_url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/2016-01-01/2026-12-31?apiKey={api_key}"
        h_res = requests.get(h_url).json().get('results', [])
        
        return {"price": price, "pe": pe, "growth": growth, "history": h_res, "n": n}
    except Exception as e:
        return f"接口错误: {str(e)}"

# 4. 主逻辑渲染
if ticker:
    # 自动获取 Secrets
    api_key = st.secrets.get("POLY_KEY")
    
    if not api_key:
        st.error("🔑 部署错误：请在 Secrets 中配置 POLY_KEY")
    else:
        with st.spinner('数据分析中...'):
            data = get_stock_data(ticker, api_key)
            
        if isinstance(data, str):
            st.error(f"🚫 {data}")
        else:
            # 数据展示
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("价格", f"${data['price']:.2f}")
            c2.metric("P/E (TTM)", f"{data['pe']:.2f}")
            c3.metric("5年复合增速", f"{data['growth']*100:.2f}%")
            c4.metric("目标 P/E", f"{target_pe}")

            # 诊断结论
            if data['growth'] > 0 and data['pe'] > 0:
                if data['pe'] <= target_pe:
                    st.success("🌟 当前估值极具吸引力")
                else:
                    years = math.log(data['pe'] / target_pe) / math.log(1 + data['growth'])
                    st.warning(f"⚠️ 诊断：回归合理估值约需 {years:.2f} 年")
            
            # 价格图表
            df = pd.DataFrame(data['history'])
            df['date'] = pd.to_datetime(df['t'], unit='ms')
            fig = go.Figure(go.Scatter(x=df['date'], y=df['c'], line=dict(color='#1f77b4')))
            fig.update_layout(yaxis_type="log", template="plotly_white", height=450)
            st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption("Munger Multiplier | Official Data Mode | 2026")
