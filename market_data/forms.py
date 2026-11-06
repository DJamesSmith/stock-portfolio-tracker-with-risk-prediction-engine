import re
from pathlib import Path

from django import forms

from core.fields import MultipleFileField
from .models import DatasetUpload

TICKER_PATTERN = r"[A-Z][A-Z0-9.\-]{0,9}"
ALLOWED_UPLOAD_EXTENSIONS = [".csv", ".zip"]
MAX_UPLOAD_FILE_MB = 500


class TickerForm(forms.Form):
    ticker = forms.CharField(max_length=10)

    def clean_ticker(self):
        ticker = self.cleaned_data["ticker"].strip().upper()

        if not re.fullmatch(TICKER_PATTERN, ticker):
            raise forms.ValidationError("Enter a valid ticker symbol, for example AAPL or BRK.B.")

        return ticker


def parse_ticker_list(raw_tickers):
    tickers = []

    for raw_ticker in raw_tickers.split(","):
        if not raw_ticker.strip():
            continue

        ticker_form = TickerForm({"ticker": raw_ticker})

        if not ticker_form.is_valid():
            raise forms.ValidationError(f"{raw_ticker.strip()} is not a valid ticker symbol.")

        ticker = ticker_form.cleaned_data["ticker"]

        if ticker not in tickers:
            tickers.append(ticker)

    return tickers


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


class DatasetUploadForm(forms.ModelForm):
    files = MultipleFileField(required=False, allow_empty_file=True)

    class Meta:
        model = DatasetUpload
        fields = ["tickers"]

    def clean_tickers(self):
        return ",".join(parse_ticker_list(self.cleaned_data["tickers"]))

    def clean_files(self):
        files = []

        for uploaded_file in self.cleaned_data["files"]:
            name = Path(uploaded_file.name).name
            extension = Path(name).suffix.lower()

            if name.startswith(".") or extension not in ALLOWED_UPLOAD_EXTENSIONS:
                continue

            if uploaded_file.size > MAX_UPLOAD_FILE_MB * 1024 * 1024:
                raise forms.ValidationError(f"{name} is larger than {MAX_UPLOAD_FILE_MB} MB.")

            files.append(uploaded_file)

        if not files:
            raise forms.ValidationError("Choose at least one .csv file, a folder of .csv files, or a .zip file.")

        return files
