import yfinance as yf

def download_last_week(tickers=["^GDAXI", "^GSPC", "XIN0.FGI"]):
    for ticker in tickers:
        df = yf.download(
            ticker,
            period="7d", #7Tage intervall
            interval="1d",
            auto_adjust=True
        )

        df.index = df.index.strftime('%Y-%m-%d')
        df = df[["Close"]]

        df.to_json(
            f"yfinance_indizes/{ticker}_last_week.json",
            orient="index",
            date_format="iso",
            indent=2
        )

        print(df.tail())


download_last_week()