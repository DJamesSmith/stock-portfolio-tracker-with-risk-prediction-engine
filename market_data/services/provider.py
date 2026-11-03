import pandas as pd
import yfinance as yf

PROVIDER_COLUMNS = {
    "Date": "date",
    "Open": "open_price",
    "High": "high_price",
    "Low": "low_price",
    "Close": "close_price",
    "Volume": "volume",
}


def fetch_prices(ticker, start_date):
    history = yf.Ticker(ticker).history(start=start_date.isoformat(), interval="1d")

    if history.empty:
        return pd.DataFrame(columns=list(PROVIDER_COLUMNS.values()))

    history = history.reset_index().rename(columns=PROVIDER_COLUMNS)
    history["date"] = history["date"].dt.date
    return history[list(PROVIDER_COLUMNS.values())]