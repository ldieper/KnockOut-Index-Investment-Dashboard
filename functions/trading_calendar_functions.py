from datetime import datetime, timedelta

def get_last_trading_day():
    today = datetime.today()
    weekday = today.weekday()  # Montag = 0, Sonntag = 6

    if weekday == 0:  # Montag → Freitag
        delta = 3
    elif weekday == 6:  # Sonntag → Freitag
        delta = 2
    else:
        delta = 1

    return today - timedelta(days=delta)


def get_last_investment_day(source):
    return source["date"].max()