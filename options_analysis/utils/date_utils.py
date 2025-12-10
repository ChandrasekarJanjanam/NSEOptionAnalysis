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

def holiday_check(date):
    """Check if given date is a trading holiday"""
    # Get holidays from NSE and normalize the JSON response
    try:
        check_date = pd.to_datetime(date)
        # print(check_date)
        #Holiday check from NSE
        # df_holidays = pd.json_normalize(nse_holidays()['FO'])

        # Get holidays from sheet
        df_holidays = pd.read_excel('nse_holidays_2025.xlsx')

    except Exception as e:
        logging.error(f"Error fetching holidays from NSE: {e}")
        logging.info("Skipping holiday check")
        return False
    
    df_holidays['Date'] = pd.to_datetime(df_holidays['Date'])

    if check_date in df_holidays['Date'].values:
        holiday_desc = df_holidays[df_holidays['Date'] == check_date]['Description'].values[0]
        logging.info(f"{check_date.date()} is a holiday: {holiday_desc}")
        return True
    else:
        logging.info(f"{check_date.date()} is NOT a holiday.")
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