import re

from django import forms

TICKER_PATTERN = r"[A-Z][A-Z0-9.\-]{0,9}"


class TickerForm(forms.Form):
    ticker = forms.CharField(max_length=10)

    def clean_ticker(self):
        ticker = self.cleaned_data["ticker"].strip().upper()

        if not re.fullmatch(TICKER_PATTERN, ticker):
            raise forms.ValidationError("Enter a valid ticker symbol, for example AAPL or BRK.B.")

        return ticker


class PriceHistoryFilterForm(forms.Form):
    start = forms.DateField(required=False, input_formats=["%Y-%m-%d"])
    end = forms.DateField(required=False, input_formats=["%Y-%m-%d"])

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start")
        end = cleaned_data.get("end")

        if start and end and start > end:
            self.add_error("end", "End date must be on or after the start date.")

        return cleaned_data