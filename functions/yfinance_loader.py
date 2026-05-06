from pathlib import Path
import yfinance as yf


#Update: Loads only new Data if Data is there?

# Loads the past 20years of the chosen products and saves them once. (update for newer data must be done manually!)
def download(tickers=["^GDAXI", "^GSPC", "^HSI"]): #^GDAXI = DAX, ^GSPC = S&P500, ^HSI = Hang Seng Index; e.g. ^NDX = Nasdaq100, STOXX50E = EuroStoxx50 etc.
    for ticker in tickers:
        df = yf.download(
            ticker,
            period="20y",
            interval="1d",
            auto_adjust=True
        )

        # If no directory exists, create it
        Path("index_data").mkdir(parents=True, exist_ok=True)

        df.index = df.index.strftime('%Y-%m-%d')
        df = df[["Close"]]

        df.to_json(
            f"index_data/{ticker}.json",
            orient="index",
            date_format="iso",
            indent=2
        )

        print(df.tail())