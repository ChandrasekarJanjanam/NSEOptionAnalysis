import json
from datetime import datetime

from nselib import derivatives
import pandas as pd

from stocklist import symbols

import logging

from utility import write_to_log, get_working_days, get_last_thursday_and_last_day_of_month, get_nse_holidays, get_zerodha_holidays

pd.set_option('future.no_silent_downcasting', True)
# pd.options.mode.copy_on_write = True
pd.set_option('mode.copy_on_write', True)


pd.set_option('display.width', 1500)
pd.set_option('display.max_rows', 50)
pd.set_option('display.max_columns', 75)



""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
""""""""" Get options OHLC data from NSE  """""""""""
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
def get_options_data_from_nse(symbol : str, instrument:str, option_type: str = None,
                             period: str = None, expiry_date: str = None):

    ### Get stock options OHLC prices of all the Strike prices and expiry dates
    stock_df = pd.DataFrame(derivatives.option_price_volume_data(symbol = symbol, instrument = instrument, option_type = option_type, period = period))

    # stock_df['date'] = pd.to_datetime(stock_df['TIMESTAMP'])
    stock_df.set_index(stock_df['TIMESTAMP'], inplace=True)

    # # Rename columns
    stock_df.rename(columns={'OPENING_PRICE': 'open', 'CLOSING_PRICE': 'close', 'TRADE_HIGH_PRICE': 'high',
                             'TRADE_LOW_PRICE': 'low', 'STRIKE_PRICE': 'strike'}, inplace=True)

    stock_df = stock_df[
        ['TIMESTAMP', 'SYMBOL', 'strike', 'EXPIRY_DT', 'open', 'high', 'low',
         'close']]

    if expiry_date:
        stock_df = stock_df[stock_df['EXPIRY_DT'] == expiry_date]

    return stock_df


def find_green_bullish_candles(final_df):

    bullish_message = None
    if len(final_df) == 4:
        openFlag = False
        closeFlag = False

        row = final_df.iloc[0]
        if (row['open'] == '0.00') and (row['high'] == '0.00') and (row['low'] == '0.00'):
            final_df.at[final_df.index[0], 'open'] = row['close']

        row = final_df.iloc[1]
        if (row['open'] == '0.00') and (row['high'] == '0.00') and (row['low'] == '0.00'):
            final_df.at[final_df.index[1], 'open'] = row['close']

        row = final_df.iloc[2]
        if (row['open'] == '0.00') and (row['high'] == '0.00') and (row['low'] == '0.00'):
            final_df.at[final_df.index[2], 'open'] = row['close']

        row = final_df.iloc[3]
        if (row['open'] == '0.00') and (row['high'] == '0.00') and (row['low'] == '0.00'):
            final_df.at[final_df.index[3], 'open'] = row['close']

        # print(
        #     f"first_week_open_date - {final_df.iloc[3]['open']}, first_week_close_date - {final_df.iloc[2]['close']}")
        # print(
        #     f"last_week_open_date - {final_df.iloc[1]['open']}, last_week_close_date - {final_df.iloc[0]['close']}")

        if ((float(final_df.iloc[2]['close']) > float(final_df.iloc[3]['open'])) and
                (float(final_df.iloc[0]['close']) > float(final_df.iloc[1]['open']))):

            # Compare first week open day's price with last week open day
            if final_df.iloc[1]['open'] <= final_df.iloc[3]['open']:
                # print("last_week_open_date open is lower than the first_week_open_date.")
                openFlag = True
            else:
                final_df.iloc[1]['open'] >= final_df.iloc[3]['open']
                # print("last_week_open_date open is higher than the first_week_open_date.")

            # Compare first week open day's price with last week open day
            if final_df.iloc[0]['close'] >= final_df.iloc[2]['close']:
                # print("last_week_close_date close is higher than first_week_close_date.")
                closeFlag = True
            else:
                final_df.iloc[0]['close'] <= final_df.iloc[2]['close']
                # print("last_week_close_date is lower than the first_week_close_date")

            # print(openFlag, closeFlag)
            if (openFlag & closeFlag):
                print(final_df)
                bullish_message = f"***** GREEN bullish ****** {final_df.iloc[0]['SYMBOL']}, {final_df.iloc[0]['strike']}, {final_df.iloc[0]['EXPIRY_DT']} ***** "
                # write_to_log(bullish_message)
        #     else:
        #         bullish_message = f"NOT bullish, {final_df.iloc[0]['strike']}, {final_df.iloc[0]['EXPIRY_DT']}"
        # else:
        #     bullish_message = f"NOT bullish, {final_df.iloc[0]['strike']}, {final_df.iloc[0]['EXPIRY_DT']}"
    # else:
    #     if not final_df.empty:
    #         bullish_message = f"Insufficient data for {final_df.iloc[0]['strike']}, {final_df.iloc[0]['EXPIRY_DT']}"
    #     else:
    #         bullish_message = f"Insufficient data"

    # print(bullish_message)
    return bullish_message

def process_logic(symbol, expiry, first_week_open_date, first_week_close_date, last_week_open_date, last_week_close_date ):
    # ### Get options data from NSE

    try:
        filtered_stock_df = get_options_data_from_nse(symbol, 'OPTSTK', 'CE', '1M', expiry)
    except Exception as e:
        logging.error(f"Failed to fetch OHLC data for {symbol} with expiry {expiry}: {e}")
        return 0

    # last_traded_price = get_stock_price(symbol)
    # above_cmp_strike_prices_df = filtered_stock_df[(filtered_stock_df['strike'].astype(float) > float(last_traded_price))]
    # filtered_stock_df = filtered_stock_df[(filtered_stock_df['strike'].astype(float) > 570.00)]

    # filtered_stock_df = filtered_stock_df[filtered_stock_df['strike'] == '480.00']
    first_week_open_date = first_week_open_date.strftime("%d-%b-%Y")
    first_week_close_date = first_week_close_date.strftime("%d-%b-%Y")
    last_week_open_date = last_week_open_date.strftime("%d-%b-%Y")
    last_week_close_date = last_week_close_date.strftime("%d-%b-%Y")

    # print(first_week_open_date)

    # filtered_stock_df = filtered_stock_df[filtered_stock_df['TIMESTAMP'].isin(pd.to_datetime(
    #     [first_week_open_date, first_week_close_date, last_week_open_date, last_week_close_date]))]

    filtered_stock_df = filtered_stock_df[filtered_stock_df['TIMESTAMP'].isin([first_week_open_date, first_week_close_date, last_week_open_date, last_week_close_date])]

    unique_strike_prices  = filtered_stock_df['strike'].unique()
    # unique_strike_prices = ['290.00']

    message = ""

    for strike_price in unique_strike_prices:
        final_df = filtered_stock_df[filtered_stock_df['strike'] == strike_price]
        # message.append(f"Line {strike_price}")
        message = find_green_bullish_candles(final_df)
        if message is not None:
            message += f"Line {strike_price}\n"

    return message



if __name__ == '__main__':

   # get expiry date
   # expiry_date = '24-Apr-2025'
   # expiry_date = get_expiry_date().strftime("%d-%b-%Y")
   expiry_day, expiry_month, expiry_year = get_last_thursday_and_last_day_of_month()
   expiry_date = str(expiry_day)+"-"+str(expiry_month)+"-"+str(expiry_year)
   #get required working days candles
   first_week_open_date, first_week_close_date, last_week_open_date, last_week_close_date = get_working_days()

   # Get holidays for current year
   try:
       current_year = datetime.now().year
       print(f"Fetching Zerodha Holidays for {current_year}...")
       holidays_df = get_zerodha_holidays(current_year)

       if not holidays_df.empty:
           print(f"Zerodha Holidays for {current_year}:")
           print(holidays_df)

           # Save to CSV
           csv_filename = f"zerodha_holidays_{current_year}.csv"
           holidays_df.to_csv(csv_filename, index=False)
           print(f"Holidays saved to {csv_filename}")
       else:
           print("Could not fetch Zerodha holidays.")

   except Exception as e:
       print(f"Error in main: {e}")

   #
   # try:
   #     with open("output.txt", "w") as f:
   #         # symbols = ["AUBANK"]
   #         for symbol in symbols:
   #            print(f"######## Processing symbol {symbol} - START ###########")
   #            message = process_logic(symbol, expiry_date, first_week_open_date, first_week_close_date, last_week_open_date, last_week_close_date )
   #            print(message)
   #            if message is not None:
   #              f.write(message)
   #            print(f"######## Processing symbol {symbol} - END #############\n")
   #     print("File written successfully.")
   # except IOError as e:
   #  print(f"An I/O error occurred: {e}")
   # except Exception as e:
   #  print(f"An unexpected error occurred: {e}")
