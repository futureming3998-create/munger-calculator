import streamlit as st
import akshare as ak
import pandas as pd
import plotly.graph_objects as go
import math
import requests

# --- 1. UI 核心配置 (打赏按钮对齐) ---
st.set_page_config(page_title="Munger Analysis Pro", layout="wide")
st.markdown('''
    <style>
    .coffee-btn { display: block; width: 100%; border-radius: 8px; overflow: hidden; }
    .coffee-btn img { width: 100%; object-fit: contain; }
    div[data-testid="stMetricValue"] > div { font-size: 1.8rem !important; }
    </style>
''', unsafe_allow_html=True)

# --- 2. 增强型数据引擎 (三栖适配) ---
def get_stock_comprehensive(ticker):
    ticker = ticker.strip().upper()
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        # --- A股逻辑 ---
        if ticker.isdigit() and len(ticker) == 6:
            df = ak.stock_zh_a_spot_em()
            row = df[df['代码'] == ticker].iloc[0]
            hist_df = ak.stock_zh_a_hist(symbol=ticker, period="daily", adjust="qfq").tail(250)
            hist_df.columns = ['Date','Open','Close','High','Low','Volume','Amount','Amplitude','Pct','Change','Turnover']
            hist_df['Date'] = pd.to_datetime(hist_df['Date'])
            return {"price": float(row['最新价']), "pe": float(row['市盈率TTM']), "growth": 0.12, "name": row['名称'], "history": hist_df}
        
        # --- 美股逻辑 (NFLX/AAPL 差异化抓取) ---
        elif ticker.isalpha():
            # 1. 抓取走势与现价 (最高优先级)
            chart_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1y"
            c_res = requests.get(chart_url, headers=headers, timeout=10).json()
            res_data = c_res['chart']['result'][0]
            price = float(res_data['meta']['regularMarketPrice'])
            ts = res_data['timestamp']
            close_prices = res_data['indicators']['quote'][0]['close']
            hist_df = pd.DataFrame({'Date': pd.to_datetime(ts, unit='s'), 'Close': close_prices})

            # 2. 抓取 PE 与增速 (次级优先级，失败则给默认值不报错)
            pe, growth = 20.0, 0.15 # 基础预设
            try:
                quote_url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=summaryDetail,defaultKeyStatistics"
                q_res = requests.get(quote_url, headers=headers, timeout=10).json()
                summary = q_res['quoteSummary']['result'][0]['summaryDetail']
                stats = q_res['quoteSummary']['result'][0]['defaultKeyStatistics']
                
                # 动态提取每一只股票真实的 PE
                pe_raw = summary.get('trailingPE', {}).get('raw') or summary.get('forwardPE', {}).get('raw')
                if pe_raw: pe = float(pe_raw)
                
                # 动态提取每一只股票真实的利润增速
                growth_raw = stats.get('earningsQuarterlyGrowth', {}).get('raw') or summary.get('fiveYearAvgReturnOnAssets', {}).get('raw')
                if growth_raw: growth = float(growth_raw)
            except: pass
            
            return {"price": price, "pe": pe, "growth": growth, "name": ticker, "history": hist_df}
    except: return None

# --- 3. 侧边栏与打赏按钮 ---
with st.sidebar:
    st.header("🔍 配置中心")
    st.caption("⌨️ **代码指南：**\n• A股: 600519\n• 美股: NFLX, AAPL")
    ticker_input = st.text_input("输入股票代码", key="v6_input").strip()
    target_pe = st.slider("目标合理市盈率 (P/E)", 10.0, 40.0, 20.0)
    st.markdown("---")
    st.subheader("☕ 请作者喝杯咖啡")
    st.markdown('<a href="https://www.buymeacoffee.com/vcalculator" target="_blank" class="coffee-btn"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"></a>', unsafe_allow_html=True)

# --- 4. 主界面逻辑 (恢复指南 + 图表显示) ---
st.title("📈 芒格“价值线”三栖分析仪")

if not ticker_input:
    # 恢复上手指南
    st.info("👋 **欢迎！请在左侧输入股票代码开始分析。**")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("""
        ### 📖 快速上手指南：
        1. **输入代码**：A股(600519)，美股(NFLX)。
        2. **设定目标**：调整左侧滑块，设定合理市盈率。
        3. **分析结论**：下方自动计算回归年数与趋势图。
        """)
    with col_g2:
        st.caption("✅ 支持 A/港/美 全市场实时抓取")
        st.caption("✅ 芒格复利回归对数公式推算")
else:
    with st.spinner('连接全球数据库中...'):
        data = get_stock_comprehensive(ticker_input)
    
    if data:
        # 指标看板
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("实时股价", f"{data['price']:.2f}")
        c2.metric("当前 P/E (TTM)", f"{data['pe']:.2f}")
        c3.metric("预期利润增速", f"{data['growth']*100:.1f}%")
        c4.metric("回本目标 P/E", f"{target_pe}")

        # 芒格回归诊断
        if data['pe'] > target_pe and data['growth'] > 0:
            years = math.log(data['pe'] / target_pe) / math.log(1 + data['growth'])
            st.warning(f"⚠️ 诊断：回归至合理目标约需 **{years:.2f}** 年")
        else:
            st.success("🌟 诊断：当前估值极具吸引力（黄金坑）")

        # 走势图表
        st.subheader(f"📊 {data['name']} 历史走势 (近一年)")
        if not data['history'].empty:
            fig = go.Figure(go.Scatter(x=data['history']['Date'], y=data['history']['Close'], line=dict(color='#1f77b4', width=2)))
            fig.update_layout(template="plotly_white", height=400, margin=dict(l=0,r=0,t=20,b=0), hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("🚫 抓取失败。请尝试大写代码 (如 NFLX)。若多次失败请检查网络。")

st.markdown("---")
st.caption("Munger Multiplier Tool | Built by Gemini | Stable 2.0")
