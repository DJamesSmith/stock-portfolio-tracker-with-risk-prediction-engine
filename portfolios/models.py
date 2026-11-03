from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

MINIMUM_AMOUNT = Decimal("0.0001")


class Portfolio(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolios",
        db_index=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "portfolios"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="unique_portfolio_name_per_user"),
        ]

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class Holding(models.Model):
    class RiskLabel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class Direction(models.TextChoices):
        UP = "up", "Up"
        DOWN = "down", "Down"

    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="holdings",
        db_index=True)
    ticker = models.CharField(max_length=10, db_index=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=4, validators=[MinValueValidator(MINIMUM_AMOUNT)])
    buy_price = models.DecimalField(max_digits=12, decimal_places=4, validators=[MinValueValidator(MINIMUM_AMOUNT)])
    buy_date = models.DateField()

    risk_label = models.CharField(max_length=10, choices=RiskLabel.choices, null=True, blank=True)
    risk_score = models.FloatField(null=True, blank=True)
    predicted_direction = models.CharField(max_length=10, choices=Direction.choices, null=True, blank=True)
    prediction_confidence = models.FloatField(null=True, blank=True)
    last_predicted_at = models.DateTimeField(null=True, blank=True)
    model_version = models.CharField(max_length=50, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "holdings"
        ordering = ["ticker", "id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="holding_quantity_positive"),
            models.CheckConstraint(condition=models.Q(buy_price__gt=0), name="holding_buy_price_positive"),
        ]

    def __str__(self):
        return f"{self.ticker} x {self.quantity} in {self.portfolio.name}"

    def save(self, *args, **kwargs):
        self.ticker = self.ticker.strip().upper()
        super().save(*args, **kwargs)