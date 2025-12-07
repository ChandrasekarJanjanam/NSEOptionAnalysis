import calendar
from datetime import date, tzinfo
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta, MO
import re
import plotly.graph_objects as go
import pytz
import requests
import pandas as pd
from bs4 import BeautifulSoup
from nsepython import nse_holidays, nsefetch

tz = pytz.timezone('Asia/Kolkata')
current_date = datetime.today().now(tz)
last_day_of_month = ""

def get_stock_price(symbol : str):
    # Fetch stock data for RELIANCE
    url = "https://www.nseindia.com/api/quote-equity?symbol=" + symbol
    data = nsefetch(url)

    # Extract the last traded price
    last_traded_price = data['priceInfo']['lastPrice']
    print(f'{symbol} stock last traded price is : ', last_traded_price)
    return last_traded_price


def get_nse_holidays(year=None):
    """
    Fetch the list of holidays from NSE (National Stock Exchange of India)

    Args:
        year (int, optional): The year for which to fetch holidays. Defaults to current year.

    Returns:
        pandas.DataFrame: DataFrame containing holiday dates and descriptions
    """
    # If year is not provided, use current year
    if year is None:
        year = datetime.now().year

    # URL for NSE holidays
    url = f"https://www.nseindia.com/api/holiday-master?type=trading"

    # Headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }

    try:
        # Send a GET request to NSE
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad responses

        # Parse JSON response
        holiday_data = response.json()

        # Filter by year if needed and create DataFrame
        holidays = []
        for item in holiday_data.get('CM', []):  # CM represents Capital Market segment
            holiday_date = datetime.datetime.strptime(item['tradingDate'], '%d-%b-%Y')
            if holiday_date.year == year:
                holidays.append({
                    'Date': holiday_date.strftime('%Y-%m-%d'),
                    'Day': holiday_date.strftime('%A'),
                    'Description': item['description']
                })

        # Create DataFrame
        df = pd.DataFrame(holidays)
        return df

    except requests.exceptions.RequestException as e:
        print(f"Error fetching NSE holidays: {e}")

        # Alternative approach using web scraping if API fails
        return get_nse_holidays_scrape(year)

def get_nse_holidays_scrape(year=None):
    """
    Fallback function to scrape NSE holidays from the website

    Args:
        year (int, optional): The year for which to fetch holidays. Defaults to current year.

    Returns:
        pandas.DataFrame: DataFrame containing holiday dates and descriptions
    """
    if year is None:
        year = datetime.datetime.now().year

    url = "https://www.nseindia.com/resources/exchange-communication-holidays"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the holiday table
        table = soup.find('table', {'class': 'holiday-table'})

        if table:
            holidays = []
            rows = table.find_all('tr')[1:]  # Skip header row

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    date_str = cols[0].text.strip()
                    try:
                        date_obj = datetime.datetime.strptime(date_str, '%d-%b-%Y')
                        if date_obj.year == year:
                            holidays.append({
                                'Date': date_obj.strftime('%Y-%m-%d'),
                                'Day': date_obj.strftime('%A'),
                                'Description': cols[2].text.strip()
                            })
                    except ValueError:
                        continue

            return pd.DataFrame(holidays)
        else:
            print("Holiday table not found on the NSE website")
            return pd.DataFrame(columns=['Date', 'Day', 'Description'])

    except Exception as e:
        print(f"Error scraping NSE holidays: {e}")
        return pd.DataFrame(columns=['Date', 'Day', 'Description'])


def get_zerodha_holidays(year=None):
    """
    Fetch trading holidays from Zerodha's Market Intel page

    Args:
        year (int, optional): The year for which to fetch holidays. Defaults to current year.

    Returns:
        pandas.DataFrame: DataFrame containing holiday dates and descriptions
    """
    # If year is not provided, use current year
    if year is None:
        year = datetime.now().year

    # URL for Zerodha holiday calendar
    url = "https://zerodha.com/marketintel/holiday-calendar/"

    # Headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://zerodha.com/',
    }

    try:
        # Send a GET request to Zerodha
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad responses

        # Parse HTML response
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the holiday table - looking for year in the heading
        year_header = None
        for header in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            if str(year) in header.text:
                year_header = header
                break

        if not year_header:
            print(f"Could not find header for year {year}")
            return pd.DataFrame(columns=['Date', 'Day', 'Description', 'Exchanges'])

        # Find the closest table after the year header
        table = None
        for element in year_header.find_all_next():
            if element.name == 'table':
                table = element
                break

        if not table:
            # Try another approach - find table with year in header or caption
            for table_elem in soup.find_all('table'):
                if str(year) in table_elem.text[:100]:  # Check only first part of table
                    table = table_elem
                    break

        if not table:
            print(f"Could not find holiday table for year {year}")
            return pd.DataFrame(columns=['Date', 'Day', 'Description', 'Exchanges'])

        # Extract data from table
        holidays = []
        headers = []

        # Extract headers
        header_row = table.find('thead')
        if header_row:
            headers = [th.text.strip() for th in header_row.find_all('th')]
        else:
            # If no thead, use first row as header
            first_row = table.find('tr')
            if first_row:
                headers = [th.text.strip() for th in first_row.find_all(['th', 'td'])]

        if not headers:
            headers = ['Date', 'Day', 'Description', 'Exchanges']

        # Process rows
        rows = table.find_all('tr')
        # Skip header row if we already processed it
        start_idx = 1 if header_row or (headers and rows and len(headers) == len(rows[0].find_all(['td', 'th']))) else 0

        for row in rows[start_idx:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 3:  # Ensure we have at least date, day, and description
                row_data = {}

                # Map cells to headers, ensure we have enough headers
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        header = headers[i]
                    else:
                        header = f"Column_{i}"
                    row_data[header] = cell.text.strip()

                # Extract date - should be in the first column
                date_str = list(row_data.values())[0]

                # Try to parse date in different formats
                date_obj = None
                date_formats = ['%d-%b-%Y', '%d %b %Y', '%b %d, %Y', '%d/%m/%Y', '%Y-%m-%d']

                # Clean the date string
                date_str = re.sub(r'\s+', ' ', date_str.strip())
                print(f"date str : {date_str}")
                # Try to extract just the date part if there's additional text
                date_match = re.search(
                    r'(\d{1,2}[-\s/][A-Za-z]{3,}[-\s/]\d{2,4}|\d{1,2}[-\s/]\d{1,2}[-\s/]\d{2,4}|\d{4}[-\s/]\d{1,2}[-\s/]\d{1,2})',
                    date_str)
                if date_match:
                    date_str = date_match.group(1)

                # Try each format
                for date_format in date_formats:
                    try:
                        date_obj = datetime.strptime(date_str, date_format)
                        break
                    except ValueError:
                        continue

                if date_obj is None:
                    # If we couldn't parse the date, skip this row
                    print(f"Could not parse date: {date_str}")
                    continue

                # Ensure we have the correct year
                if date_obj.year != year:
                    # If year is missing or wrong in the date string, set it to the requested year
                    if date_obj.year < 100:  # 2-digit year
                        date_obj = date_obj.replace(year=year)
                    else:
                        continue  # Skip this row if it's for a different year

                # Build holiday entry
                holiday = {
                    'Date': date_obj.strftime('%Y-%m-%d'),
                    'Day': date_obj.strftime('%A')
                }

                # Map remaining data
                for i, (key, value) in enumerate(row_data.items()):
                    if i == 0:  # Skip date as we've already processed it
                        continue

                    # Map to our standardized columns
                    if re.search(r'day|week', key, re.I):
                        holiday['Day'] = value
                    elif re.search(r'desc|occasion|holiday|reason', key, re.I):
                        holiday['Description'] = value
                    elif re.search(r'exchange|market', key, re.I):
                        holiday['Exchanges'] = value
                    else:
                        # Use original column name
                        holiday[key] = value

                # Ensure we have all required columns
                if 'Description' not in holiday:
                    # If no specific description column, use the second column as description
                    second_col = list(row_data.items())[1][1] if len(row_data) > 1 else ""
                    holiday['Description'] = second_col

                if 'Exchanges' not in holiday:
                    holiday['Exchanges'] = "All"  # Default

                holidays.append(holiday)

        # Create DataFrame
        df = pd.DataFrame(holidays)

        # Ensure we have the standard columns in a nice order
        standard_columns = ['Date', 'Day', 'Description', 'Exchanges']
        for col in standard_columns:
            if col not in df.columns:
                df[col] = ""

        # Rearrange columns with standard ones first, then any extras
        first_cols = [col for col in standard_columns if col in df.columns]
        other_cols = [col for col in df.columns if col not in standard_columns]
        df = df[first_cols + other_cols]

        return df

    except Exception as e:
        print(f"Error fetching Zerodha holidays: {e}")
        return pd.DataFrame(columns=['Date', 'Day', 'Description', 'Exchanges'])


def create_chart(df, bullish_engulfing_days):
    # 8️⃣ Candlestick Chart Visualization
    fig = go.Figure(data=[
        go.Candlestick(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            increasing_line_color='green',
            decreasing_line_color='red'
        )
    ])

    # Highlight Bullish Engulfing Patterns
    fig.add_trace(go.Scatter(
        x=bullish_engulfing_days['date'],
        y=bullish_engulfing_days['close'],
        mode='markers',
        marker=dict(size=12, color='blue', symbol='triangle-up'),
        name='Bullish Engulfing'
    ))

    fig.update_layout(title='Bullish Engulfing Pattern Detection', xaxis_title='Date', yaxis_title='Price')
    fig.show()

def get_expiry_date():
    kdf = pd.read_csv('https://api.kite.trade/instruments')
    kdf['expiry'] = pd.to_datetime(kdf['expiry'], format="%Y-%m-%d").apply(lambda x: x.date())
    kdf = kdf[(kdf.name == 'NIFTY') & (kdf.expiry > datetime.now().date())]
    expirylist = kdf['expiry'].unique().tolist()
    expirylist.sort()
    return expirylist[0]

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
""""""""" Check if given date is trading holiday """""""""""
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
def holiday_check(date):
    # Step 1 : Get list of trading holidays with description
    try:
        df_holidays = pd.json_normalize(nse_holidays()['FO'])
    except Exception as e:
        print("An unexpected error occurred while fetching holidays from NSE:", e)
        print("Skipping holiday check now", e)
        return False
    # print(df_holidays.head(50))

    # Step 2 : Convert into dataframe
    df_holidays['tradingDate'] = pd.to_datetime(df_holidays['tradingDate'])

    # Step 3: Date to check
    check_date = pd.to_datetime(date)  # Example: Gandhi Jayanti

    # Step 4: Check if the date is a holiday
    if check_date in df_holidays['tradingDate'].values:
        print(
            f"{check_date.date()} is a holiday: {df_holidays[df_holidays['tradingDate'] == check_date]['description'].values[0]}")
        return True
    else:
        print(f"{check_date.date()} is NOT a holiday.")
        return False




""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
""""""""""""""""""" Get Nth working day  """""""""""""""""""
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
# prev_week_num - number of week to go back
# offset : 0 - Monday,  1 - Tuesday,  ....., 4 - Friday
from datetime import datetime, timedelta
import pytz


# prev_week_num - number of week to go back
# offset : 0 - Monday,  1 - Tuesday,  ....., 4 - Friday
def get_nth_working_day(prev_week_num, offset):
    # Today's date
    tz = pytz.timezone('Asia/Kolkata')
    today = datetime.today().now(tz)
    # today = datetime.today()
    # print(today.tzinfo is not None)

    # Weekday: Monday = 0 ... Sunday = 6
    days_since_offset = (today.weekday() - offset) % 7

    # Go back to last working day, then back by (n-1)*7 days
    total_days_back = days_since_offset + (prev_week_num - 1) * 7

    # Last Target day
    target_day = today - timedelta(days=total_days_back)
    return target_day.date()

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
""""""""" green_bullish_engulf_pattern """""""""""
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
""" 
    To identify bullish engulf pattern from OHLC data
    :param pandas.DataFrame: ohlc_df  
    :return: pandas.DataFrame
"""
def green_bullish_engulf_pattern(ohlc_df):
    # print(ohlc_df)
    # Identify Bullish Engulfing Pattern
    ohlc_df['prev_open'] = ohlc_df['open'].shift(1)
    ohlc_df['prev_close'] = ohlc_df['close'].shift(1)

    ohlc_df['bullish_engulfing'] = (
            (ohlc_df['prev_close'] < ohlc_df['prev_open']) &  # Previous candle is red (close < open)
            (ohlc_df['close'] > ohlc_df['open']) &  # Current candle is green (close > open)
            (ohlc_df['open'] < ohlc_df['prev_close']) &  # Current open is below previous close
            (ohlc_df['close'] > ohlc_df['prev_open'])  # Current close is above previous open (engulfing)
    )

    # Filter rows where the pattern occurs
    bullish_engulfing_df = ohlc_df[ohlc_df['bullish_engulfing']]

    # Replace NaN with 0
    ohlc_df.fillna(0, inplace=True)
    print(ohlc_df[['date', 'open', 'close', 'bullish_engulfing']])
    print(ohlc_df)

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
""""""""" Sample OHLC """""""""""
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

def create_weekly_ohlc_data(filtered_df):
    # print(f'Weekly for strike price :{filtered_df['STRIKE_PRICE'][0]} and expiry is :{filtered_df['EXPIRY_DT'][0]}')
    ### Calculate weekly candles from daily candles
    weekly_ohlc = filtered_df.resample('W-FRI').agg({
        'open': 'first',  # Open price: first value of the week
        'high': 'max',  # High price: maximum value of the week
        'low': 'min',  # Low price: minimum value of the week
        'close': 'last'  # Close price: last value of the week
        # 'strike': 'first'  # Close price: last value of the week
    })
    weekly_ohlc.dropna(inplace=True)
    weekly_ohlc.reset_index(inplace=True)

    # print(f'\n\nWeekly for strike price :{filtered_df['strike'].iloc[0]} and Expiry is :{filtered_df['EXPIRY_DT'].iloc[0]}')
    # print(weekly_ohlc)
    return weekly_ohlc


def backtesting(df):
    # Basic Backtesting (Simple Strategy)
    # Buy when bullish engulfing occurs, sell after 3 days (for demonstration)
    df['position'] = df['bullish_engulfing'].shift(1).fillna(False)
    df['daily_return'] = df['close'].pct_change()
    df['strategy_return'] = df['daily_return'] * df['position']

    # Calculate cumulative returns
    cumulative_returns = (1 + df['strategy_return']).cumprod()

    print("\nCumulative Returns from the Simple Strategy:\n")
    print(cumulative_returns.tail())


###########################################################################
############## Get last Thursday of Next Month ################
###########################################################################

def get_last_thursday_of_next_month(year, month):
    # Calculate next month
    if month == 12:
        next_month_year = year + 1
        next_month = 1
    else:
        next_month_year = year
        next_month = month + 1

    # Get the first day of the following month
    if next_month == 12:
        first_day_of_next_next_month = datetime(next_month_year + 1, 1, 1)
    else:
        first_day_of_next_next_month = datetime(next_month_year, next_month + 1, 1)

    # Get the last day of the next month
    last_day_of_next_month = first_day_of_next_next_month - timedelta(days=1)

    # Find the last Thursday
    while last_day_of_next_month.weekday() != 3:  # 3 represents Thursday
        last_day_of_next_month -= timedelta(days=1)

    return last_day_of_next_month

###########################################################################
############## Get last day and last Thursday of the Month ################
###########################################################################
def get_last_thursday_and_last_day_of_month():
    year = current_date.year
    month = current_date.month

    last_thursday = date.today()
    # Get the first day of the next month
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)

    # print(next_month.date())
    # Go back to the last day of the current month
    last_day = next_month - timedelta(days=1)
    # last_day = last_day
    print(f"Last day of this month is : ", last_day.date())
    # Find the last Thursday of the month
    while last_day.weekday() != 3:  # 3 represents Thursday
        last_day -= timedelta(days=1)
        last_thursday = last_day

    print(f"Last Thursday of this month is : ", last_thursday.date())

    ## last_thursday is in offset-naive datatime so first convert to 'Asia/Kolkata' timezone
    # before comparing the difference between current date and last_thursday
    last_thursday = tz.localize(last_thursday)

    ## find the difference between current_date and last_thursday, if it > 5 than take current month last_thursday as expiry date
    # else calculate next month's last thursday
    if  (last_thursday - current_date).days > 5:
        expiry_month = current_date.month
        expiry_year = current_date.year
        expiry_day = last_thursday.day
    else:
        expiry_month = current_date.month + 1
        expiry_date = get_last_thursday_of_next_month(year, month)
        expiry_day = expiry_date.day
        expiry_year = expiry_date.year

    expiry_month = calendar.month_abbr[expiry_month]
    print(f"Expiry will be : {expiry_day}-{expiry_month}-{expiry_year}")

    return expiry_day, expiry_month, expiry_year


def sample_ohlc_data():

    # Sample OHLC Data
    # data = {
    #     'date': pd.date_range(start='2024-01-01', periods=10, freq='D'),
    #     'open': [105, 104, 102, 101, 99, 96, 96, 97, 95, 96],
    #     'high': [106, 105, 104, 103, 100, 101, 99, 102, 98, 100],
    #     'low': [103, 102, 100, 98, 95, 95, 94, 95, 92, 93],
    #     'close': [104, 102, 100, 99, 97, 100, 98, 101, 94, 97]
    # }

    data = {
        'date': pd.date_range(start='2025-02-01', periods=15, freq='D'),
        'open': [100, 102, 104, 103, 105, 106, 108, 109, 107, 110, 111, 112, 115, 117, 116],
        'high': [105, 106, 107, 108, 109, 110, 112, 113, 111, 115, 116, 118, 120, 122, 121],
        'low': [99, 100, 102, 101, 103, 104, 105, 106, 104, 108, 109, 110, 113, 115, 114],
        'close': [103, 104, 106, 107, 108, 109, 110, 111, 109, 114, 115, 117, 118, 120, 119]
    }
    print(pd.DataFrame(data))
    return  pd.DataFrame(data)

###########################################################################
############## Get (N-4)th monday ################
###########################################################################
def get_n_minus_4th_monday(n, reference_date=None):
    """
    Get the (N-4)th Monday from the given reference date (or today if not provided).

    :param n: The Nth Monday
    :param reference_date: Optional reference date (default is today)
    :return: Date of the (N-4)th Monday
    """
    if reference_date is None:
        reference_date = date.today()

    # Find the most recent Monday
    last_monday = reference_date + relativedelta(weekday=MO(-1))

    # Get the (N-4)th Monday
    target_monday = last_monday - timedelta(weeks=(n - 4))

    return target_monday

# working days of week calculation
def get_working_days():
    # if today is Monday then give 2 for prev_monday else 3 and so on
    print(f"Today is : {datetime.today().weekday()}")
    if datetime.today().weekday() == 0 or datetime.today().weekday() == 6:
        prev_monday = get_nth_working_day(2, 0)
        last_monday = get_nth_working_day(1, 0)
    else:
        prev_monday = get_nth_working_day(3, 0)
        last_monday = get_nth_working_day(2, 0)

    if datetime.today().weekday() == 4:
        prev_friday = get_nth_working_day(3, 4)
        last_friday = get_nth_working_day(2, 4)
    else:
        prev_friday = get_nth_working_day(2, 4)
        last_friday = get_nth_working_day(1, 4)

    print("Before holiday check --> ",prev_monday, prev_friday, last_monday, last_friday)

    first_week_open_date = prev_monday
    while (holiday_check(first_week_open_date)):
        first_week_open_date = first_week_open_date + timedelta(days=1)

    last_week_open_date = last_monday
    while (holiday_check(last_week_open_date)):
        last_week_open_date = last_week_open_date + timedelta(days=1)

    first_week_close_date = prev_friday
    while (holiday_check(first_week_close_date)):
        first_week_close_date = first_week_close_date - timedelta(days=1)

    last_week_close_date = last_friday
    while (holiday_check(last_week_close_date)):
        last_week_close_date = last_week_close_date - timedelta(days=1)

    print("After holiday check --> ",first_week_open_date, first_week_close_date, last_week_open_date, last_week_close_date)
    return first_week_open_date, first_week_close_date, last_week_open_date, last_week_close_date


def write_to_log(message):
    try:
        with open("output.txt", "w") as f:
            f.write(message)
        print("File written successfully.")
    except IOError as e:
        print(f"An I/O error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")