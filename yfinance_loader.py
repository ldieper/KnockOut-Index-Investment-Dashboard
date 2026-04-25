from pathlib import Path
import yfinance as yf


def download(tickers=["^GDAXI", "^GSPC", "^HSI"]):
    for ticker in tickers:
        df = yf.download(
            ticker,
            period="20y",
            interval="1d",
            auto_adjust=True
        )

        from pathlib import Path

        # If no directory exists, create it
        Path("yfinance_indizes").mkdir(parents=True, exist_ok=True)

        df.index = df.index.strftime('%Y-%m-%d')
        df = df[["Close"]]

        df.to_json(
            f"yfinance_indizes/{ticker}.json",
            orient="index",
            date_format="iso",
            indent=2
        )

        print(df.tail())


download()