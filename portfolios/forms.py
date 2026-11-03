import re

from django import forms
from django.utils import timezone

from accounts.models import User
from market_data.forms import TICKER_PATTERN
from .models import Holding, Portfolio

ML_FIELDS = [
    "risk_label",
    "risk_score",
    "predicted_direction",
    "prediction_confidence",
    "last_predicted_at",
    "model_version",
]


class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ["name", "description"]

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        self.fields["description"].required = False

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if not name:
            raise forms.ValidationError("Portfolio name cannot be blank.")

        same_name = Portfolio.objects.filter(user=self.owner, name__iexact=name).exclude(pk=self.instance.pk)

        if same_name.exists():
            raise forms.ValidationError("A portfolio with this name already exists for this user.")

        return name

    def clean_description(self):
        return (self.cleaned_data.get("description") or "").strip()

    def save(self, commit=True):
        portfolio = super().save(commit=False)

        if self.owner is not None:
            portfolio.user = self.owner

        if commit:
            portfolio.save()

        return portfolio


class PortfolioOwnerForm(forms.Form):
    user_id = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.Role.INVESTOR, is_active=True),
        error_messages={"invalid_choice": "Select an active investor."})


class HoldingForm(forms.ModelForm):
    class Meta:
        model = Holding
        fields = ["ticker", "quantity", "buy_price", "buy_date"]

    def clean_ticker(self):
        ticker = self.cleaned_data["ticker"].strip().upper()

        if not re.fullmatch(TICKER_PATTERN, ticker):
            raise forms.ValidationError("Enter a valid ticker symbol, for example AAPL or BRK.B.")

        return ticker

    def clean_buy_date(self):
        buy_date = self.cleaned_data["buy_date"]

        if buy_date > timezone.localdate():
            raise forms.ValidationError("Buy date cannot be in the future.")

        return buy_date


class HoldingUpdateForm(HoldingForm):
    class Meta:
        model = Holding
        fields = ["quantity", "buy_price", "buy_date"]


def find_blocked_fields(submitted_data, blocked_fields, message):
    errors = {}

    for field in blocked_fields:
        if field in submitted_data:
            errors[field] = [message]

    return errors


def build_portfolio_data(portfolio, submitted_data):
    return {
        "name": submitted_data.get("name", portfolio.name),
        "description": submitted_data.get("description", portfolio.description),
    }


def build_holding_data(holding, submitted_data):
    return {
        "quantity": submitted_data.get("quantity", holding.quantity),
        "buy_price": submitted_data.get("buy_price", holding.buy_price),
        "buy_date": submitted_data.get("buy_date", holding.buy_date),
    }