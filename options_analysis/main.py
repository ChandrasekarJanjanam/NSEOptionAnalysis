"""
Main execution script for Zerodha options analysis
"""

import logging
import pandas as pd
from datetime import datetime

from options_analysis.config.settings import setup_logging
from auth.zerodha_auth import ZerodhaAuthenticator
from data.fetcher import get_instruments, fetch_ohlc_data
from utils.data_utils import get_ltp, get_expiry_date, filter_option_strikes, find_green_bullish_candles
from utils.date_utils import get_working_days

# Import your stock symbols (you'll need to create this file)
try:
    from stocklist import symbols
except ImportError:
    logging.error("No stock symbols defined.")
    symbols = []

def main():
    """Main execution function"""
    setup_logging()
    # get_working_days()


    try:
        # Authenticate with Zerodha
        authenticator = ZerodhaAuthenticator()
        kite = authenticator.authenticate()

        # Fetch instruments
        instruments_df = get_instruments(kite)

        # Process options data
        option_types = [ "CE", "PE"]
        # option_types = ["PE"]
        for option_type in option_types:
            logging.info(f"######### {option_type} Analysis - START ############ ")

            all_options_df = process_options_data(kite, instruments_df, option_type)

            if all_options_df.empty:
                logging.warning("No options data found. Exiting.")
                return

            # Fetch OHLC data
            daily_ohlc_df, option_type = fetch_ohlc_data(kite, all_options_df)
            # daily_ohlc_df = pd.read_csv('zerodha_NFO_filtered_CE_daily_OHLC_01-Nov-2025 21-55-22.csv')

            # Get weekly data
            weekly_ohlc_df = get_weekly_data(daily_ohlc_df)
            # weekly_ohlc_df = pd.read_csv('zerodha_NFO_filtered_PE_weekly_OHLC_30-Nov-2025 16-15-58.csv')

            # Analyze for bullish patterns
            analyze_bullish_patterns(weekly_ohlc_df, f"{option_type}_Analysis.txt")

            logging.info(f"######### {option_type} Analysis - END ############ ")

    except Exception as e:
        logging.error(f"Program failed with error: {e}")
        raise

def process_options_data(kite, instruments_df, option_type="PE"):
    """Process options data for all symbols"""
    all_options_df = pd.DataFrame()
    symbol_counter = 0
    
    expiry_date = get_expiry_date(instruments_df)
    if expiry_date is None:
        logging.error("Expiry is None... So cannot proceed further")
        return all_options_df
    
    logging.info(f"Total symbols to process for {option_type} is {len(symbols)}")
    
    for sym in symbols:
        try:
            last_traded_price = get_ltp(kite, sym, exchange="NSE")
            filtered_df = filter_option_strikes(
                instruments_df, sym, 
                min_strike=last_traded_price, 
                option_type=option_type, 
                expiry=expiry_date
            )
            
            if not filtered_df.empty:
                all_options_df = pd.concat([all_options_df, filtered_df])
                if symbol_counter % 50 == 0:
                    logging.info(f" ✅ Processing symbol number - {symbol_counter}")
                symbol_counter += 1
                    
        except Exception as e:
            logging.error(f"Skipping {sym}: {e}")
    
    logging.info(f" ✅ Processed all the symbols: {symbol_counter}")
    all_options_df.reset_index(drop=True, inplace=True)
    
    # Save filtered data
    formatted = datetime.now().strftime("%d-%b-%Y %H-%M-%S")
    csv_filename = f"zerodha_NFO_filtered_{option_type}_options_{formatted}.csv"
    all_options_df.to_csv(csv_filename, index=False)
    logging.info(f"Filtered options data saved to {csv_filename}")
    
    return all_options_df

def get_weekly_data(daily_ohlc_df):
    """Extract weekly OHLC data"""
    first_week_open_date, first_week_close_date, last_week_open_date, last_week_close_date = get_working_days()
    
    first_week_open_date = first_week_open_date.strftime("%Y-%m-%d")
    first_week_close_date = first_week_close_date.strftime("%Y-%m-%d")
    last_week_open_date = last_week_open_date.strftime("%Y-%m-%d")
    last_week_close_date = last_week_close_date.strftime("%Y-%m-%d")
    
    weekly_ohlc_df = daily_ohlc_df[
        daily_ohlc_df['date'].isin([
            first_week_open_date, first_week_close_date, 
            last_week_open_date, last_week_close_date
        ])
    ]
    
    option_type = weekly_ohlc_df["option_type"].iloc[0] if not weekly_ohlc_df.empty else "UNKNOWN"
    formatted = datetime.now().strftime("%d-%b-%Y %H-%M-%S")
    csv_filename = f"zerodha_NFO_filtered_{option_type}_weekly_OHLC_{formatted}.csv"
    weekly_ohlc_df.to_csv(csv_filename, index=False)
    logging.info(f"Weekly OHLC data saved to {csv_filename}")
    
    return weekly_ohlc_df

def analyze_bullish_patterns(weekly_ohlc_df, filename):
    """Analyze weekly data for bullish patterns"""
    unique_symbols = weekly_ohlc_df['name'].unique()
    
    try:
        with open(filename, "w") as file_object:
            for symbol in unique_symbols:
                symbol_df = weekly_ohlc_df[weekly_ohlc_df['name'] == symbol]
                # symbol_df = weekly_ohlc_df[weekly_ohlc_df['name'] == symbol]
                unique_strike_prices = symbol_df['strike'].unique()
                
                for strike_price in unique_strike_prices:
                    final_df = symbol_df[symbol_df['strike'] == strike_price]
                    message = find_green_bullish_candles(final_df)
                   
                    if message is not None:
                        file_object.write(f"{message}\n")
                        logging.info(f"Bullish pattern found: {message}")
                    # else:
                        # logging.info(f"Bullish pattern NOT found! {message}")
                        
    except IOError as e:
        logging.error(f"An I/O error occurred while writing output: {e}")
    except Exception as e:
        logging.error(f"Exception occurred while writing output: {e}")

if __name__ == "__main__":
    main()