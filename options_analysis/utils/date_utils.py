"""
Date and time utility functions
"""

import logging
from datetime import datetime, timedelta
import pytz
import os
import openpyxl
import pandas as pd
import chardet  # to detect encoding automatically
from nsepython import nse_holidays

_HOLIDAYS_DF = None

def _load_holidays(filepath='nse_holidays_2026.csv'):
    """Load and cache holidays with fallbacks: xlsx -> csv -> nse_holidays() -> empty DF."""
    global _HOLIDAYS_DF
    if _HOLIDAYS_DF is not None:
        return _HOLIDAYS_DF

    # 1) try Excel file
    try:
        df = pd.read_excel(filepath, engine='openpyxl')
        logging.info(f"✅ Loaded holidays from ` {filepath} `")
        _HOLIDAYS_DF = df
    except Exception as e:
        logging.error(f"Error reading ` {filepath} `: {e}")
        _HOLIDAYS_DF = None

    # 2) try CSV fallback next to the xlsx if excel failed or produced no usable DF
    if _HOLIDAYS_DF is None or _HOLIDAYS_DF.empty:
        try:
            csv_path = filepath.replace('.xlsx', '.csv')
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                logging.info(f"✅ Loaded holidays from CSV fallback ` {csv_path} `")
                _HOLIDAYS_DF = df
        except Exception as e2:
            logging.error(f"Error reading fallback ` {csv_path} `: {e2}")
            _HOLIDAYS_DF = None

    # 3) try nse_holidays() API as last structured-data fallback
    if _HOLIDAYS_DF is None or _HOLIDAYS_DF.empty:
        try:
            raw = nse_holidays()
            if isinstance(raw, dict):
                # prefer 'FO' if present
                if 'FO' in raw and isinstance(raw['FO'], (list, tuple)):
                    df = pd.json_normalize(raw['FO'])
                else:
                    parts = [pd.json_normalize(v) for v in raw.values() if isinstance(v, (list, tuple))]
                    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
            elif isinstance(raw, list):
                df = pd.json_normalize(raw)
            else:
                df = pd.DataFrame()

            if not df.empty:
                logging.info(f"nse_holidays() API returned {len(df)} records")
                logging.info("✅ Loaded holidays from nse_holidays() API")
                _HOLIDAYS_DF = df
        except Exception as e3:
            logging.error(f"Error fetching holidays from NSE API: {e3}")
            _HOLIDAYS_DF = None

    # Final fallback: ensure a DataFrame exists with expected columns
    if _HOLIDAYS_DF is None:
        logging.warning("No holiday data available; holiday checks will be skipped.")
        _HOLIDAYS_DF = pd.DataFrame(columns=['Date', 'Description'])

    # Normalize Date column to python date objects for reliable comparison
    # if 'Date' in _HOLIDAYS_DF.columns:
    #     _HOLIDAYS_DF['Date'] = pd.to_datetime(_HOLIDAYS_DF['Date'], errors='coerce').dt.date
    if 'Date' in _HOLIDAYS_DF.columns:
        parsed_dates = pd.to_datetime(
            _HOLIDAYS_DF['Date'],
            errors='coerce',
            dayfirst=True
            # infer_datetime_format=False
        )
        n_invalid = parsed_dates.isna().sum()
        if n_invalid:
            logging.warning(
                f"Could not parse {n_invalid} dates in `options_analysis/utils/date_utils.py` (Date column).")
        _HOLIDAYS_DF['Date'] = parsed_dates.dt.date

    return _HOLIDAYS_DF


def holiday_check(date):
    """Check if given date is a trading holiday using cached holiday data."""
    try:
        check_date = pd.to_datetime(date).date()
    except Exception:
        logging.debug("Unable to parse date for holiday_check")
        return False

    df = _load_holidays()
    if df.empty or 'Date' not in df.columns:
        return False

    if check_date in df['Date'].values:
        desc = ''
        if 'Description' in df.columns:
            try:
                desc = df.loc[df['Date'] == check_date, 'Description'].iat[0]
            except Exception:
                desc = ''
        logging.info(f"{check_date} is a holiday: {desc}")
        return True

    logging.info(f"{check_date} is NOT a holiday.")
    return False

def get_nth_working_day(prev_week_num, offset):
    """Get the nth working day based on week offset and day offset"""
    tz = pytz.timezone('Asia/Kolkata')
    today = datetime.today().now(tz)
    
    days_since_offset = (today.weekday() - offset) % 7
    total_days_back = days_since_offset + (prev_week_num - 1) * 7
    
    target_day = today - timedelta(days=total_days_back)
    return target_day.date()

def get_working_days():
    """Get working days for current and previous week with holiday adjustment"""
    logging.info(f"Today is: {datetime.today().weekday()}")
    
    # Calculate base dates
    if datetime.today().weekday() == 5:  # Saturday
        prev_monday = get_nth_working_day(2, 0)
        last_monday = get_nth_working_day(1, 0)

    if datetime.today().weekday() == 4:  # Friday
        prev_friday = get_nth_working_day(3, 4)
        last_friday = get_nth_working_day(2, 4)
    else:
        prev_friday = get_nth_working_day(2, 4)
        last_friday = get_nth_working_day(1, 4)

    if datetime.today().weekday() == 6:  # Sunday
        prev_monday = get_nth_working_day(2, 0)
        last_monday = get_nth_working_day(1, 0)

    if datetime.today().weekday() == 0:  # Monday
        prev_monday = get_nth_working_day(3, 0)
        last_monday = get_nth_working_day(2, 0)

    if datetime.today().weekday() == 1:  # Tuesday
        prev_monday = get_nth_working_day(3, 0)
        last_monday = get_nth_working_day(2, 0)

    if datetime.today().weekday() == 2:  # Wednesday
        prev_monday = get_nth_working_day(3, 0)
        last_monday = get_nth_working_day(2, 0)

    logging.info(f"Before holiday check --> {prev_monday}, {prev_friday}, {last_monday}, {last_friday}")

    # Adjust for holidays
    first_week_open_date = adjust_date_for_holiday(prev_monday, forward=True)
    last_week_open_date = adjust_date_for_holiday(last_monday, forward=True)
    first_week_close_date = adjust_date_for_holiday(prev_friday, forward=False)
    last_week_close_date = adjust_date_for_holiday(last_friday, forward=False)

    logging.info(f"After holiday check --> {first_week_open_date}, {first_week_close_date}, {last_week_open_date}, {last_week_close_date}")
    
    return first_week_open_date, first_week_close_date, last_week_open_date, last_week_close_date

def adjust_date_for_holiday(date, forward=True):
    """Adjust date forward or backward until it's not a holiday"""
    delta = timedelta(days=1) if forward else timedelta(days=-1)
    current_date = date
    
    while holiday_check(current_date):
        current_date = current_date + delta
    
    return current_date