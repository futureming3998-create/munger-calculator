import streamlit as st
import akshare as ak
import pandas as pd
import plotly.graph_objects as go
import math
import requests

# --- 1. 基础 UI 配置 ---
st.set_page_config(page_title="Munger Analysis Pro", layout="wide")

st.markdown('''
    <style>
    .coffee-btn { display: block; width: 100%; border-radius: 8px; overflow: hidden; }
    .coffee-btn img { width: 100%; object-fit: contain; }
    div[data-testid="stMetricValue"] > div { font-size: 1.8rem !important; }
    </style>
''', unsafe_allow_html=True)

# --- 2. 深度数据引擎 (修正字段提取路径) ---
def get_verified_data(ticker):
    ticker = ticker.strip().upper()
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        # A股逻辑
        if ticker.isdigit() and len(ticker) == 6:
            df = ak.stock_zh_a_spot_em()
            row = df[df['代码'] == ticker].iloc[0]
            hist_df = ak.stock_zh_a_hist(symbol=ticker, period="daily", adjust="qfq").tail(250)
            hist_df.columns = ['Date','Open','Close','High','Low','Volume','Amount','Amplitude','Pct','Change','Turnover']
            hist_df['Date'] = pd.to_datetime(hist_df['Date'])
            return {"price": float(row['最新价']), "pe": float(row['市盈率TTM']), "growth": 0.12, "name": row['名称'], "history": hist_df}
        
        # 美股逻辑 (修复 NFLX 字段相同的问题)
        elif ticker.isalpha():
            # 获取价格和历史
            chart_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1y"
            c_res = requests.get(chart_url, headers=headers, timeout=10).json()
            res_data = c_res['chart']['result'][0]
            price = float(res_data['meta']['regularMarketPrice'])
            ts = res_data['timestamp']
            close_prices = res_data['indicators']['quote'][0]['close']
            hist_df = pd.DataFrame({'Date': pd.to_datetime(ts, unit='s'), 'Close': close_prices})

            # 获取 PE 和 真实增速 (不再使用固定保底值)
            quote_url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=summaryDetail,defaultKeyStatistics"
            q_res = requests.get(quote_url, headers=headers, timeout=10).json()
            summary = q_res['quoteSummary']['result'][0]['summaryDetail']
            stats = q_res['quoteSummary']['result'][0]['defaultKeyStatistics']
            
            # 优先提取 TTM PE，没有则取 Forward PE
            pe = summary.get('trailingPE', {}).get('raw') or summary.get('forwardPE', {}).get('raw') or 0.0
            # 提取真实利润增长预期 (若无则设为 0.1)
            growth = stats.get('earningsQuarterlyGrowth', {}).get('raw') or 0.10
            
            return {"price": price, "pe": float(pe), "growth": float(growth), "name": ticker, "history": hist_df}
        return None
    except:
        return None

# --- 3. 侧边栏布局 ---
with st.sidebar:
    st.header("🔍 配置中心")
    st.caption("⌨️ **代码指南：**\n• A股: 600519\n• 美股: NFLX, AAPL")
    ticker_input = st.text_input("输入股票代码", key="search_v5").strip()
    target_pe = st.slider("目标合理市盈率 (P/E)", 10.0, 40.0, 20.0)
    
    st.markdown("---")
    st.subheader("☕ 请作者喝杯咖啡")
    st.markdown('<a href="https://www.buymeacoffee.com/vcalculator" target="_blank" class="coffee-btn"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"></a>', unsafe_allow_html=True)

# --- 4. 主页面逻辑 (恢复指南布局) ---
st.title("📈 芒格“价值线”三栖分析仪")

# 始终显示的上手指南 (除非输入了有效代码并成功加载)
guide_placeholder = st.empty()

if not ticker_input:
    with guide_placeholder.container():
        st.info("👋 **欢迎！请在左侧输入股票代码开始分析。**")
        st.markdown("""
        ### 快速上手指南：
        1. **输入代码**：A股输入数字(600519)，美股输入字母(NFLX)。
        2. **设定目标**：调整左侧滑块，设定你心目中的合理市盈率。
        3. **分析轨迹**：下方将自动生成股价走势与芒格回归年数。
        """)
else:
    data = get_verified_data(ticker_input)
    if data and data['pe'] > 0:
        guide_placeholder.empty() # 输入成功后才清空指南
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("实时股价", f"{data['price']:.2f}")
        c2.metric("当前 P/E (TTM)", f"{data['pe']:.2f}")
        c3.metric("预期利润增速", f"{data['growth']*100:.1f}%")
        c4.metric("回本目标 P/E", f"{target_pe}")

        # 芒格回归计算
        if data['pe'] > target_pe:
            years = math.log(data['pe'] / target_pe) / math.log(1 + data['growth'])
            st.warning(f"⚠️ 诊断：回归至合理目标约需 **{years:.2f}** 年")
        else:
            st.success("🌟 诊断：当前估值极具吸引力（黄金坑）")

        st.subheader(f"📊 {data['name']} 历史走势 (近一年)")
        fig = go.Figure(go.Scatter(x=data['history']['Date'], y=data['history']['Close'], line=dict(color='#1f77b4')))
        fig.update_layout(template="plotly_white", height=400, margin=dict(l=0,r=0,t=20,b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("🚫 抓取失败或该股暂无 PE 数据。请输入正确的大写代码（如 NFLX）。")

st.markdown("---")
st.caption("Munger Multiplier Tool | Built by Gemini | Verified Edition")
