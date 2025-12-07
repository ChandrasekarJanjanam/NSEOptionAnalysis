"""
Data fetching utilities for Zerodha API
"""

import logging
import pandas as pd
from datetime import datetime, timedelta

def get_instruments(kite, exchange="NFO"):
    """Fetch instruments and save to CSV"""
    instruments = kite.instruments(exchange)
    instruments_df = pd.DataFrame(instruments)
    
    if not instruments_df.empty:
        formatted = datetime.now().strftime("%d-%b-%Y %H-%M-%S")
        csv_filename = f"zerodha_NFO_original_{formatted}.csv"
        instruments_df.to_csv(csv_filename, index=False)
        logging.info(f"Instruments saved to {csv_filename}")
    
    return instruments_df

def get_ohlc_last_20_days(kite, instrument_token: int):
    """Fetch OHLC for last 20 days for a given instrument token"""
    to_date = datetime.today()
    from_date = to_date - timedelta(days=20)
    
    try:
        data = kite.historical_data(
            instrument_token,
            from_date,
            to_date,
            interval="day",
            continuous=False,
            oi=True
        )
        df = pd.DataFrame(data)
        df["instrument_token"] = instrument_token
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        return df
    except Exception as e:
        logging.error(f"Error fetching OHLC for {instrument_token}: {e}")
        return pd.DataFrame()

def fetch_ohlc_data(kite, all_options_df):
    """Fetch OHLC data for all instruments in the dataframe"""
    ohlc_list = []
    logging.info(f"✅ Total tokens - {len(all_options_df['instrument_token'].unique())}")
    
    counter = 0
    option_type = all_options_df["instrument_type"][0] if not all_options_df.empty else "UNKNOWN"
    
    for token in all_options_df["instrument_token"].unique():
        ohlc_df = get_ohlc_last_20_days(kite, token)

        if ohlc_df is not None and not ohlc_df.empty:
            ohlc_list.append(ohlc_df)
            if counter % 100 == 0:
                logging.info(f"✅ Processing token number - {counter}")
            counter += 1
        else:
            placeholder = pd.DataFrame({
                "instrument_token": [token],
                "date": [pd.NaT],
                "open": [None],
                "high": [None],
                "low": [None],
                "close": [None],
                "volume": [None]
            })
            ohlc_list.append(placeholder)
            logging.warning(f"⚠️ No OHLC data for token - {token}, added placeholder")

    logging.info(f"Total processed tokens: {counter}")
    
    # Merge all OHLC data
    ohlc_all_df = pd.concat(ohlc_list, ignore_index=True)
    
    # Join with original dataframe
    daily_ohlc_df = ohlc_all_df.merge(
        all_options_df[["instrument_token", "expiry", "name", "strike", "instrument_type"]],
        on="instrument_token",
        how="inner"
    )
    
    daily_ohlc_df.rename(columns={"instrument_type": "option_type"}, inplace=True)
    
    # Save to CSV
    formatted = datetime.now().strftime("%d-%b-%Y %H-%M-%S")
    csv_filename = f"zerodha_NFO_filtered_{option_type}_daily_OHLC_{formatted}.csv"
    daily_ohlc_df.to_csv(csv_filename, index=False)
    logging.info(f"Daily OHLC data saved to {csv_filename}")
    
    return daily_ohlc_df, option_type