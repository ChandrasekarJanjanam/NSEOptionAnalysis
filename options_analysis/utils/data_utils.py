"""
Data processing and analysis utilities
"""

import logging
import pandas as pd
from datetime import datetime

def get_ltp(kite, symbol: str, exchange: str = "NSE"):
    """Get the last traded price for a given symbol"""
    instrument_token = f"{exchange}:{symbol}"
    data = kite.ltp([instrument_token])
    return data[instrument_token]["last_price"]

def get_expiry_date(instruments_df, symbol="ABB"):
    """Get appropriate expiry date for options"""
    matched_df = instruments_df[(instruments_df["name"] == symbol)]
    
    if matched_df.empty:
        return None
    
    symbol_df = pd.DataFrame()
    symbol_df["expiry"] = pd.to_datetime(matched_df["expiry"])
    expiries = sorted(symbol_df["expiry"].unique())
    
    if not expiries:
        return None

    selected_expiry = expiries[0]
    today = pd.Timestamp(datetime.today().date())
    
    if (selected_expiry - today).days < 10 and len(expiries) > 1:
        selected_expiry = expiries[1]

    logging.info(f"selected_expiry: {selected_expiry.date()}")
    return selected_expiry.date()

def filter_option_strikes(df, symbol: str, min_strike: float, option_type: str = "CE", expiry: str = None):
    """Filter option contracts for a given symbol"""
    if option_type not in ["CE", "PE"]:
        raise ValueError("option_type must be 'CE' or 'PE'")

    if option_type == "CE":
        symbol_df = df[(df["name"] == symbol) & 
                      (df["strike"] > min_strike) & 
                      (df["instrument_type"] == option_type) &
                      (df["expiry"] == expiry)]
    else:
        symbol_df = df[(df["name"] == symbol) & 
                      (df["strike"] < min_strike) & 
                      (df["instrument_type"] == option_type) &
                      (df["expiry"] == expiry)]
    
    if symbol_df.empty:
        return pd.DataFrame()

    return symbol_df.sort_values(by="strike")

def find_green_bullish_candles(final_df):
    """Identify green bullish candle patterns"""
    bullish_message = None
    if len(final_df) == 4:
        openFlag = False
        closeFlag = False

        # Handle zero values
        for i in range(4):
            row = final_df.iloc[i]
            if (row['open'] == '0.00') and (row['high'] == '0.00') and (row['low'] == '0.00'):
                final_df.at[final_df.index[i], 'open'] = row['close']

        # Validate if each week is GREEN candle
        if ((float(final_df.iloc[3]['close']) > float(final_df.iloc[2]['open'])) and
                (float(final_df.iloc[1]['close']) > float(final_df.iloc[0]['open']))):

            # Check price conditions
            if final_df.iloc[2]['open'] <= final_df.iloc[0]['open']:
                openFlag = True
         
            if final_df.iloc[3]['close'] >= final_df.iloc[1]['close']:
                closeFlag = True
           
            if (openFlag & closeFlag):
                bullish_message = f"***** GREEN bullish ****** {final_df.iloc[0]['name']}, {final_df.iloc[0]['strike']}, {final_df.iloc[0]['expiry']} ***** "

    return bullish_message