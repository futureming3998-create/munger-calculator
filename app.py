import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math

# --- 1. 基础配置 ---
st.set_page_config(page_title="Munger Analysis Pro", layout="wide")
st.title("📈 芒格“价值线”深度分析仪")

# --- 2. 核心：超级健壮的数据引擎 ---
@st.cache_data(ttl=3600)
def fetch_munger_data_robust(symbol, api_key):
    # 使用官方推荐的 URL 传参模式
    base_params = {"apiKey": api_key}
    try:
        # A. 抓取价格
        p_resp = requests.get(f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev", params=base_params).json()
        if 'results' not in p_resp: return "TICKER_NOT_FOUND"
        price = p_resp['results'][0]['c']

        # B. 抓取财报 (一次性多取几份，增加容错)
        f_url = f"https://api.polygon.io/X/reference/financials?ticker={symbol}&timeframe=annual&limit=10"
        f_resp = requests.get(f_url, params=base_params).json()
        f_results = f_resp.get('results', [])
        
        valid_history = []
        for r in f_results:
            # 【核心修复】：万能路径抓取利润数据
            income = None
            try:
                # 尝试多个可能的嵌套路径
                fin_data = r.get('financials', {})
                # 优先找利润表，再找综合损益表
                inc_stmt = fin_data.get('income_statement', {}) or fin_data.get('comprehensive_income', {})
                income = inc_stmt.get('net_income_loss', {}).get('value')
                
                year = r.get('fiscal_year') or r.get('calendar_year')
                if income is not None and year is not None:
                    valid_history.append({'v': float(income), 'y': int(year)})
            except: continue
        
        if len(valid_history) < 2: return "DATA_INCOMPLETE"
        
        # 排序并计算 CAGR
        valid_history.sort(key=lambda x: x['y'])
        n = valid_history[-1]['y'] - valid_history[0]['y'] or 1
        
        v_start, v_end = valid_history[0]['v'], valid_history[-1]['v']
        # 计算 CAGR 增速 
        if v_start > 0 and v_end > 0:
            growth = (v_end / v_start)**(1/n) - 1
        else:
            growth = (v_end - v_start) / abs(v_start) / n

        # 获取 EPS 计算 PE
        try:
            latest_inc = f_results[0]['financials']['income_statement']
            eps = latest_inc.get('basic_earnings_per_share', {}).get('value', 0)
            pe = price / eps if eps > 0 else 0
        except: pe = 0

        # C. 历史价格数据
        h_url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/2016-01-01/2026-12-31"
        h_data = requests.get(h_url, params=base_params).json().get('results', [])

        return {"price": price, "pe": pe, "growth": growth, "history": h_data, "n": n}
    except Exception as e:
        return f"ERROR: {str(e)}"

# --- 3. 界面逻辑 ---
with st.sidebar:
    ticker = st.text_input("输入代码 (如 AAPL)", "AAPL").upper().strip()
    target_pe = st.slider("目标合理 P/E", 10.0, 50.0, 20.0)
    st.markdown("---")
    st.write("☕ 如果好用，请支持作者")

poly_key = st.secrets.get("POLY_KEY")

if ticker and poly_key:
    with st.spinner('正在调取数据...'):
        data = fetch_munger_data_robust(ticker, poly_key)
    
    if isinstance(data, str):
        st.error(f"⚠️ 无法分析该股: {data}")
    else:
        # 展示核心指标
        c1, c2, c3 = st.columns(3)
        c1.metric("当前价格", f"${data['price']:.2f}")
        c2.metric("当前 P/E", f"{data['pe']:.2f}")
        c3.metric(f"{data['n']}年利润 CAGR", f"{data['growth']*100:.2f}%")

        # 诊断结论
        if data['growth'] > 0 and data['pe'] > 0:
            if data['pe'] <= target_pe:
                st.success("🌟 当前估值具备极高性价比")
            else:
                y = math.log(data['pe'] / target_pe) / math.log(1 + data['growth'])
                st.warning(f"⚠️ 诊断：回归目标 P/E 约需 {y:.2f} 年")
        
        # 10年价格对数图
        if data['history']:
            df = pd.DataFrame(data['history'])
            df['date'] = pd.to_datetime(df['t'], unit='ms')
            fig = go.Figure(go.Scatter(x=df['date'], y=df['c'], name="Price", line=dict(color='#1f77b4')))
            fig.update_layout(yaxis_type="log", template="plotly_white", height=450)
            st.plotly_chart(fig, use_container_width=True)

st.caption("Munger Multiplier | Official Data Mode | 2026")
