import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "daily_return",
    "volatility_30",
    "volatility_90",
    "max_drawdown_90",
    "price_to_ma_20",
    "price_to_ma_50",
    "rsi_14",
    "volume_trend",
]


def calculate_rsi(close, periods=14):
    change = close.diff()
    average_gain = change.clip(lower=0).rolling(periods).mean()
    average_loss = (-change.clip(upper=0)).rolling(periods).mean()
    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))


def build_ticker_features(prices):
    frame = prices.sort_values("date").copy()
    close = frame["close"]
    volume = frame["volume"]

    frame["daily_return"] = close.pct_change()
    frame["volatility_30"] = frame["daily_return"].rolling(30).std()
    frame["volatility_90"] = frame["daily_return"].rolling(90).std()

    peak_price = close.rolling(90, min_periods=1).max()
    drawdown = close / peak_price - 1
    frame["max_drawdown_90"] = drawdown.rolling(90).min()

    frame["ma_20"] = close.rolling(20).mean()
    frame["ma_50"] = close.rolling(50).mean()
    frame["price_to_ma_20"] = close / frame["ma_20"]
    frame["price_to_ma_50"] = close / frame["ma_50"]

    frame["rsi_14"] = calculate_rsi(close, 14)

    volume_trend = volume.rolling(20).mean() / volume.rolling(90).mean()
    frame["volume_trend"] = volume_trend.replace([np.inf, -np.inf], np.nan).fillna(1.0)

    return frame


def build_features(prices):
    frames = []

    for ticker, ticker_prices in prices.groupby("ticker"):
        frames.append(build_ticker_features(ticker_prices))

    if not frames:
        return pd.DataFrame(columns=list(prices.columns) + FEATURE_COLUMNS)

    features = pd.concat(frames, ignore_index=True)
    features[FEATURE_COLUMNS] = features[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan)
    return features