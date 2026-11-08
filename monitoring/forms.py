import re
from django import forms
from market_data.forms import TICKER_PATTERN

MAX_TICKERS_PER_MESSAGE = 20


class LiveActionForm(forms.Form):
    ACTION_CHOICES = [
        ("subscribe", "subscribe"),
        ("unsubscribe", "unsubscribe"),
        ("ping", "ping"),
    ]

    action = forms.ChoiceField(choices=ACTION_CHOICES)
    tickers = forms.JSONField(required=False)

    def clean_tickers(self):
        raw_tickers = self.cleaned_data.get("tickers")

        if raw_tickers is None:
            return []

        if not isinstance(raw_tickers, list):
            raise forms.ValidationError("Send tickers as a list, for example [\"AAPL\", \"MSFT\"].")

        if len(raw_tickers) > MAX_TICKERS_PER_MESSAGE:
            raise forms.ValidationError(f"Send at most {MAX_TICKERS_PER_MESSAGE} tickers at a time.")

        tickers = []

        for raw_ticker in raw_tickers:
            if not isinstance(raw_ticker, str):
                raise forms.ValidationError("Every ticker must be text.")

            ticker = raw_ticker.strip().upper()

            if not re.fullmatch(TICKER_PATTERN, ticker):
                raise forms.ValidationError(f"{raw_ticker} is not a valid ticker symbol.")

            if ticker not in tickers:
                tickers.append(ticker)

        return tickers

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get("action")

        if action in ["subscribe", "unsubscribe"] and not cleaned_data.get("tickers"):
            self.add_error("tickers", "Send at least one ticker.")

        return cleaned_data