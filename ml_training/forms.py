from django import forms

from market_data.forms import parse_ticker_list
from market_data.models import PriceHistory
from .models import TrainingRun


class TrainingRunForm(forms.ModelForm):
    class Meta:
        model = TrainingRun
        fields = ["model_choice", "tickers", "update_predictions"]

    def clean_tickers(self):
        tickers = parse_ticker_list(self.cleaned_data["tickers"])

        if tickers:
            stored = set(PriceHistory.objects.filter(ticker__in=tickers).values_list("ticker", flat=True).distinct())
            missing = [ticker for ticker in tickers if ticker not in stored]

            if missing:
                raise forms.ValidationError(f"No price history stored for: {', '.join(missing)}.")

        return ",".join(tickers)

    def clean(self):
        cleaned_data = super().clean()

        if not PriceHistory.objects.exists():
            raise forms.ValidationError("There is no price history yet. Upload a dataset on the Datasets page first.")

        if TrainingRun.active_runs().exists():
            raise forms.ValidationError("A training run is already waiting or in progress. Wait for it to finish or cancel it first.")

        return cleaned_data