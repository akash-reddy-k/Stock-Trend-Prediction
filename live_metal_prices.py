import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

# Set Streamlit page configuration
st.set_page_config(
    page_title="Live Precious Metals Dashboard",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling using CSS injection
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

/* Global Font Override */
html, body, [data-testid="stAppViewContainer"], [class*="css"] {
    font-family: 'Plus Jakarta Sans', 'Outfit', sans-serif !important;
}

/* Sidebar Custom Background */
[data-testid="stSidebar"] {
    background-color: #0d121f !important;
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}

/* Styling native metric containers */
[data-testid="stMetricValue"] {
    font-size: 2rem !important;
    font-weight: 700 !important;
    font-family: 'Outfit', sans-serif !important;
}

/* Custom Glassmorphism Metal Card Grid */
.metal-card-container {
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
    width: 100%;
}

.metal-card {
    flex: 1;
    background: linear-gradient(135deg, rgba(20, 27, 45, 0.8) 0%, rgba(13, 18, 30, 0.95) 100%);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    position: relative;
    overflow: hidden;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.metal-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: var(--metal-color);
}

.metal-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.4), 0 0 15px var(--metal-glow);
    border-color: rgba(255, 255, 255, 0.12);
}

.metal-title {
    font-size: 13px;
    font-weight: 600;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.metal-price {
    font-size: 26px;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 4px;
    font-family: 'Outfit', sans-serif;
}

.change-up {
    color: #10b981;
    font-size: 13px;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 4px;
}

.change-down {
    color: #ef4444;
    font-size: 13px;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 4px;
}

/* Custom styled calculator card */
.calc-card {
    background: linear-gradient(135deg, rgba(24, 32, 54, 0.8) 0%, rgba(15, 22, 38, 0.95) 100%);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
    margin-top: 16px;
}

.calc-title {
    font-family: 'Outfit', sans-serif;
    font-size: 1.25rem;
    font-weight: 600;
    color: #ffffff;
    margin-bottom: 12px;
}

.calc-result {
    font-family: 'Outfit', sans-serif;
    font-size: 2.2rem;
    font-weight: 700;
    color: #ffd700; /* defaults to gold-ish */
    margin-top: 16px;
    text-shadow: 0 0 10px rgba(255, 215, 0, 0.2);
}

.badge {
    background-color: rgba(255, 255, 255, 0.08);
    color: #e5e7eb;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 11px;
    font-weight: 500;
    margin-top: 8px;
    display: inline-block;
}
</style>
""", unsafe_allow_html=True)

# Define metal metadata and specifications
METAL_DETAILS = {
    "Gold": {
        "symbol": "GC=F",
        "unit": "troy oz",
        "color": "#D4AF37",
        "fill_color": "rgba(212, 175, 55, 0.08)",
        "glow_color": "rgba(212, 175, 55, 0.3)",
        "emoji": "🪙",
        "description": "Gold Futures (COMEX)"
    },
    "Silver": {
        "symbol": "SI=F",
        "unit": "troy oz",
        "color": "#C0C0C0",
        "fill_color": "rgba(192, 192, 192, 0.08)",
        "glow_color": "rgba(192, 192, 192, 0.3)",
        "emoji": "🥈",
        "description": "Silver Futures (COMEX)"
    },
    "Platinum": {
        "symbol": "PL=F",
        "unit": "troy oz",
        "color": "#E5E4E2",
        "fill_color": "rgba(229, 228, 226, 0.08)",
        "glow_color": "rgba(229, 228, 226, 0.3)",
        "emoji": "💍",
        "description": "Platinum Futures (NYMEX)"
    },
    "Palladium": {
        "symbol": "PA=F",
        "unit": "troy oz",
        "color": "#8E9AA6",
        "fill_color": "rgba(142, 154, 166, 0.08)",
        "glow_color": "rgba(142, 154, 166, 0.3)",
        "emoji": "🔋",
        "description": "Palladium Futures (NYMEX)"
    },
    "Copper": {
        "symbol": "HG=F",
        "unit": "lb",
        "color": "#B87333",
        "fill_color": "rgba(184, 115, 51, 0.08)",
        "glow_color": "rgba(184, 115, 51, 0.3)",
        "emoji": "🔌",
        "description": "Copper Futures (COMEX)"
    }
}

# ----------------- DATA FETCHING HELPER FUNCTIONS -----------------

@st.cache_data(ttl=60)  # Cached for 1 minute for live grid
def fetch_all_metal_live_prices():
    data = {}
    for name, details in METAL_DETAILS.items():
        try:
            # Fetch 5 days to ensure we have a previous close for percentage calculations
            df = yf.download(details["symbol"], period="5d")
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            
            if not df.empty and len(df) >= 2:
                latest = df['Close'].iloc[-1]
                prev = df['Close'].iloc[-2]
                change = latest - prev
                pct_change = (change / prev) * 100

                # Get the actual market timestamp of the latest trade/price
                market_time_unix = None
                try:
                    ticker_obj = yf.Ticker(details["symbol"])
                    market_time_unix = ticker_obj.info.get('regularMarketTime')
                except Exception:
                    pass
                
                if market_time_unix:
                    # Convert UNIX timestamp to human readable datetime format
                    fetch_time = datetime.fromtimestamp(market_time_unix).strftime("%b %d, %Y, %I:%M:%S %p")
                else:
                    # Fallback to the latest trading day from dataframe index
                    fetch_time = df.index[-1].strftime("%b %d, %Y")

                data[name] = {
                    "price": latest,
                    "change": change,
                    "pct_change": pct_change,
                    "high": df['High'].iloc[-1],
                    "low": df['Low'].iloc[-1],
                    "volume": df['Volume'].iloc[-1],
                    "fetch_time": fetch_time,
                    "success": True
                }
                print(f"Fetched {name}: Price={latest}, Change={change}, %Change={pct_change:.2f}%")
            else:
                data[name] = {"success": False, "error": "Insufficient data"}
        except Exception as e:
            data[name] = {"success": False, "error": str(e)}
    return data

@st.cache_data(ttl=300)  # Cached for 5 minutes for historical graphing
def fetch_historical_metal_data(symbol, period, interval):
    try:
        df = yf.download(symbol, period=period, interval=interval)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        return df
    except Exception as e:
        st.error(f"Error fetching historical data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600)  # Cached for 10 minutes for currency conversion
def fetch_exchange_rate(currency_code):
    if currency_code == "USD":
        return 1.0
    ticker = f"USD{currency_code}=X"
    try:
        df = yf.download(ticker, period="2d")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        if not df.empty:
            return df['Close'].iloc[-1]
    except Exception as e:
        pass
    # Reliable fallback exchange rates
    fallbacks = {
        "EUR": 0.92,
        "GBP": 0.78,
        "INR": 83.50,
        "CAD": 1.37,
        "JPY": 158.0,
        "AUD": 1.49
    }
    return fallbacks.get(currency_code, 1.0)

@st.cache_data(ttl=300)  # Load yearly stats for metrics
def get_52w_stats(symbol):
    try:
        df = yf.download(symbol, period="1y")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        if not df.empty:
            return {
                "high_52w": df['High'].max(),
                "low_52w": df['Low'].min(),
                "avg_52w": df['Close'].mean()
            }
    except Exception:
        pass
    return {"high_52w": 0, "low_52w": 0, "avg_52w": 0}

# ----------------- MAIN PAGE RENDER -----------------

# Header Section
st.markdown("""
<div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 28px; border-radius: 16px; margin-bottom: 28px; border: 1px solid rgba(255,255,255,0.06); box-shadow: 0 4px 30px rgba(0,0,0,0.3);">
    <h1 style="color: #ffffff; margin: 0; font-family: 'Outfit', sans-serif; font-size: 2.6rem; font-weight: 700; letter-spacing: -0.02em;">🪙 Live Metal Price Tracker</h1>
    <p style="color: #94a3b8; margin: 8px 0 0 0; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.05rem; font-weight: 400; line-height: 1.5;">
        Track live spot futures, analyze historical trends, overlay moving averages, and calculate bullion value across multiple fiat currencies.
    </p>
</div>
""", unsafe_allow_html=True)

# Fetch all live prices
live_prices = fetch_all_metal_live_prices()

# Display Live Metal Cards
cols = st.columns(5)
for idx, (name, details) in enumerate(METAL_DETAILS.items()):
    with cols[idx]:
        pdata = live_prices.get(name, {})
        if pdata.get("success"):
            price = pdata["price"]
            change = pdata["change"]
            pct_change = pdata["pct_change"]
            
            # Format positive/negative differences
            change_class = "change-up" if change >= 0 else "change-down"
            change_symbol = "▲" if change >= 0 else "▼"
            
            fetch_time_str = pdata.get("fetch_time", "Unknown")
            card_html = f"""
            <div class="metal-card" title="Price fetched on: {fetch_time_str}" style="--metal-color: {details['color']}; --metal-glow: {details['glow_color']};">
                <div class="metal-title">{details['emoji']} {name}</div>
                <div class="metal-price">${price:,.2f}</div>
                <div class="{change_class}">
                    <span>{change_symbol}</span> ${abs(change):,.2f} ({pct_change:+.2f}%)
                </div>
                <div class="badge">Per {details['unit']}</div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
        else:
            err = pdata.get("error", "Failed download")
            st.markdown(f"""
            <div class="metal-card" style="--metal-color: #ef4444; --metal-glow: rgba(239, 68, 68, 0.2);">
                <div class="metal-title">❌ {name}</div>
                <div class="metal-price" style="font-size: 16px; color: #ef4444; margin: 12px 0;">Error loading live price</div>
                <div style="font-size: 10px; color: #6b7280;">{err[:20]}...</div>
            </div>
            """, unsafe_allow_html=True)

# Sidebar Configuration panel
st.sidebar.markdown("""
<div style="margin-bottom: 20px;">
    <h2 style="font-family: 'Outfit', sans-serif; font-weight: 700; color: #ffffff; margin: 0; font-size: 1.5rem;">⚙️ Settings Panel</h2>
    <p style="color: #6b7280; font-size: 0.85rem; margin: 4px 0 0 0;">Customize your chart and indicators</p>
</div>
""", unsafe_allow_html=True)

selected_metal = st.sidebar.selectbox(
    "Select Metal for Detailed Analysis:",
    options=list(METAL_DETAILS.keys()),
    index=0
)

# Time Frame Picker
period_map = {
    "1 Day (Intraday)": {"period": "1d", "interval": "5m"},
    "5 Days": {"period": "5d", "interval": "30m"},
    "1 Month": {"period": "1mo", "interval": "1d"},
    "6 Months": {"period": "6mo", "interval": "1d"},
    "1 Year": {"period": "1y", "interval": "1d"},
    "5 Years": {"period": "5y", "interval": "1wk"},
    "Max History": {"period": "max", "interval": "1mo"}
}

selected_time_label = st.sidebar.selectbox(
    "Select Time Period:",
    options=list(period_map.keys()),
    index=2  # Default 1 Month
)
sel_period = period_map[selected_time_label]["period"]
sel_interval = period_map[selected_time_label]["interval"]

# Moving Averages Toggles
st.sidebar.markdown("<h3 style='font-family: \"Outfit\", sans-serif; color:#ffffff; font-size:1.1rem; margin-top:20px;'>📉 Technical Indicators</h3>", unsafe_allow_html=True)
show_sma20 = st.sidebar.checkbox("20-Day Simple Moving Average (SMA 20)", value=False)
show_sma50 = st.sidebar.checkbox("50-Day Simple Moving Average (SMA 50)", value=False)
show_sma200 = st.sidebar.checkbox("200-Day Simple Moving Average (SMA 200)", value=False)

# Main Section - Columns (Chart vs Metrics/Stats)
main_col, side_col = st.columns([7, 3])

details = METAL_DETAILS[selected_metal]

with main_col:
    st.markdown(f"### 📈 {selected_metal} Price Trend - {selected_time_label}")
    
    # Load historical data
    with st.spinner("Downloading historical data..."):
        df_hist = fetch_historical_metal_data(details["symbol"], sel_period, sel_interval)
        
    if not df_hist.empty:
        # Create Plotly interactive line chart
        fig = go.Figure()
        
        # Add primary metal trace
        fig.add_trace(go.Scatter(
            x=df_hist.index,
            y=df_hist['Close'],
            mode='lines',
            name=f"{selected_metal} Close",
            line=dict(color=details["color"], width=2.5),
            fill='tozeroy',
            fillcolor=details["fill_color"]
        ))
        
        # Overlay moving averages
        if show_sma20:
            df_hist['SMA20'] = df_hist['Close'].rolling(20).mean()
            fig.add_trace(go.Scatter(
                x=df_hist.index, y=df_hist['SMA20'],
                mode='lines', name='SMA 20',
                line=dict(color='#3b82f6', width=1.5, dash='dash')
            ))
            
        if show_sma50:
            df_hist['SMA50'] = df_hist['Close'].rolling(50).mean()
            fig.add_trace(go.Scatter(
                x=df_hist.index, y=df_hist['SMA50'],
                mode='lines', name='SMA 50',
                line=dict(color='#8b5cf6', width=1.5, dash='dash')
            ))
            
        if show_sma200:
            df_hist['SMA200'] = df_hist['Close'].rolling(200).mean()
            fig.add_trace(go.Scatter(
                x=df_hist.index, y=df_hist['SMA200'],
                mode='lines', name='SMA 200',
                line=dict(color='#ec4899', width=1.5, dash='dash')
            ))
            
        # Customize Plotly dark layout
        fig.update_layout(
            plot_bgcolor='#090d16',
            paper_bgcolor='#080b11',
            font=dict(color='#e5e7eb', family='Plus Jakarta Sans, sans-serif'),
            xaxis=dict(
                gridcolor='rgba(255, 255, 255, 0.05)',
                zeroline=False,
                showgrid=True,
                title='Date/Time'
            ),
            yaxis=dict(
                gridcolor='rgba(255, 255, 255, 0.05)',
                zeroline=False,
                showgrid=True,
                title=f"Price in USD (per {details['unit']})"
            ),
            hovermode='x unified',
            margin=dict(l=10, r=10, t=10, b=10),
            height=460,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor='rgba(0,0,0,0)'
            )
        )
        
        # Handle custom datetime formatting on the x-axis for intraday
        if sel_period in ['1d', '5d']:
            fig.update_xaxes(tickformat="%b %d, %H:%M")
        else:
            fig.update_xaxes(tickformat="%b %d, %Y")
            
        st.plotly_chart(fig, use_container_width=True)
        
        # Download Data Button
        csv = df_hist.to_csv()
        st.download_button(
            label=f"📥 Download {selected_metal} Historical Data (CSV)",
            data=csv,
            file_name=f"{selected_metal.lower()}_historical_{sel_period}.csv",
            mime="text/csv"
        )
    else:
        st.warning("No historical data found for the selected asset and period.")

with side_col:
    st.markdown("### 📊 Market Summary & Stats")
    
    with st.spinner("Calculating market metrics..."):
        # Fetch stats
        stats_52w = get_52w_stats(details["symbol"])
        live_metal_data = live_prices.get(selected_metal, {})
    
    # Render stats
    if live_metal_data.get("success"):
        current_price = live_metal_data["price"]
        high_24h = live_metal_data["high"]
        low_24h = live_metal_data["low"]
        volume = live_metal_data["volume"]
        
        st.metric(label="Current Spot Futures Price", value=f"${current_price:,.2f}")
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.metric(label="Daily High", value=f"${high_24h:,.2f}")
            st.metric(label="52-Week High", value=f"${stats_52w.get('high_52w', 0):,.2f}")
        with col_s2:
            st.metric(label="Daily Low", value=f"${low_24h:,.2f}")
            st.metric(label="52-Week Low", value=f"${stats_52w.get('low_52w', 0):,.2f}")
            
        avg_52w = stats_52w.get('avg_52w', 0)
        if avg_52w > 0:
            st.metric(label="52-Week Average", value=f"${avg_52w:,.2f}")
    else:
        st.info("Market stats currently unavailable. Check your network or Yahoo Finance access.")

# ----------------- CALCULATOR SECTION -----------------
st.markdown("---")
st.markdown("### 🧮 Bullion Value & Exchange Converter")

calc_col1, calc_col2 = st.columns([6, 4])

with calc_col1:
    st.markdown("##### Conversion Inputs")
    sub_col1, sub_col2 = st.columns(2)
    with sub_col1:
        calc_metal = st.selectbox(
            "Select Asset for Valuation:",
            options=list(METAL_DETAILS.keys()),
            index=list(METAL_DETAILS.keys()).index(selected_metal),
            key="calc_metal_select"
        )
    with sub_col2:
        calc_unit = st.selectbox(
            "Select Weight Unit:",
            options=["Troy Ounces (oz t)", "Grams (g)", "Kilograms (kg)", "Pounds (lb)"],
            index=0
        )
        
    sub_col3, sub_col4 = st.columns(2)
    with sub_col3:
        weight_input = st.number_input(
            "Enter Weight / Quantity:",
            min_value=0.0,
            value=1.0,
            step=0.1,
            format="%.4f"
        )
    with sub_col4:
        target_currency = st.selectbox(
            "Select Output Currency:",
            options=["USD", "EUR", "GBP", "INR", "CAD", "JPY", "AUD"],
            index=0
        )

# Conversion logic
calc_details = METAL_DETAILS[calc_metal]
metal_symbol = calc_details["symbol"]
metal_base_unit = calc_details["unit"] # 'troy oz' or 'lb'

# Get live or cached base price in USD
calc_base_price_usd = 0.0
pdata = live_prices.get(calc_metal, {})
if pdata.get("success"):
    calc_base_price_usd = pdata["price"]
else:
    # Attempt to fetch individually if missing from live grid
    try:
        df = yf.download(metal_symbol, period="2d")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        if not df.empty:
            calc_base_price_usd = df['Close'].iloc[-1]
    except Exception:
        calc_base_price_usd = 0.0

# Fetch dynamic forex rate
forex_rate = fetch_exchange_rate(target_currency)

# Perform weight and unit translations
# Base prices are either in Troy Ounces (Gold, Silver, Platinum, Palladium) or Pounds (Copper)
total_base_units = 0.0

if metal_base_unit == "troy oz":
    # Metal pricing is USD per troy oz
    if calc_unit == "Troy Ounces (oz t)":
        total_base_units = weight_input
    elif calc_unit == "Grams (g)":
        # 1 gram = 1 / 31.1034768 troy ounces
        total_base_units = weight_input / 31.1034768
    elif calc_unit == "Kilograms (kg)":
        # 1 kg = 1000 / 31.1034768 troy ounces
        total_base_units = weight_input * (1000.0 / 31.1034768)
    elif calc_unit == "Pounds (lb)":
        # 1 lb avoirdupois = 14.5833 troy ounces
        total_base_units = weight_input * 14.583333
else:
    # Copper: Pricing is USD per Pound (lb)
    if calc_unit == "Pounds (lb)":
        total_base_units = weight_input
    elif calc_unit == "Grams (g)":
        # 1 gram = 1 / 453.59237 pounds
        total_base_units = weight_input / 453.59237
    elif calc_unit == "Kilograms (kg)":
        # 1 kg = 2.20462 pounds
        total_base_units = weight_input * 2.20462262
    elif calc_unit == "Troy Ounces (oz t)":
        # 1 troy ounce = 31.1034768 / 453.59237 = 0.068571 pounds
        total_base_units = weight_input * (31.1034768 / 453.59237)

# Calculate final valuations
valuation_usd = total_base_units * calc_base_price_usd
valuation_converted = valuation_usd * forex_rate

# Currency formatting mapping
currency_symbols = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "INR": "₹",
    "CAD": "C$",
    "JPY": "¥",
    "AUD": "A$"
}
curr_sym = currency_symbols.get(target_currency, "$")

with calc_col2:
    st.markdown("##### Valuation Output")
    
    if calc_base_price_usd > 0:
        val_html = f"""
        <div class="calc-card" style="--metal-color: {calc_details['color']}; --metal-glow: {calc_details['glow_color']};">
            <div class="calc-title">{calc_metal} Bullion Valuation</div>
            <div style="font-size: 14px; color: #9ca3af;">
                {weight_input:,.4f} {calc_unit} of {calc_metal}
            </div>
            <div class="calc-result" style="color: {calc_details['color']}; text-shadow: 0 0 12px {calc_details['glow_color']};">
                {curr_sym}{valuation_converted:,.2f} <span style="font-size: 1.25rem; font-weight: 500; color: #9ca3af;">{target_currency}</span>
            </div>
            <div style="font-size: 11px; color: #6b7280; margin-top: 12px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px;">
                Spot Price: ${calc_base_price_usd:,.2f} USD / {calc_details['unit']} <br>
                Exchange Rate: 1 USD = {forex_rate:,.4f} {target_currency}
            </div>
        </div>
        """
        st.markdown(val_html, unsafe_allow_html=True)
    else:
        st.warning("Valuation could not be calculated because the base asset price is unavailable.")
