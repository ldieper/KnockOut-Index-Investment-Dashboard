from datetime import datetime, timedelta

def get_last_trading_day():
    today = datetime.today()
    weekday = today.weekday()  # Monday = 0, Sunday = 6

    if weekday == 0:  # Monday till Friday
        delta = 3
    elif weekday == 6:  # Sunday till Friday
        delta = 2
    else:
        delta = 1

    return today - timedelta(days=delta)


def get_last_investment_day(source):
    return source["date"].max()