from django.db import models


class PriceHistory(models.Model):
    ticker = models.CharField(max_length=10)
    date = models.DateField()
    open_price = models.DecimalField(max_digits=12, decimal_places=4)
    high_price = models.DecimalField(max_digits=12, decimal_places=4)
    low_price = models.DecimalField(max_digits=12, decimal_places=4)
    close_price = models.DecimalField(max_digits=12, decimal_places=4)
    volume = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "price_history"
        ordering = ["ticker", "-date"]
        verbose_name_plural = "price history"
        constraints = [
            models.UniqueConstraint(fields=["ticker", "date"], name="unique_ticker_date"),
        ]

    def __str__(self):
        return f"{self.ticker} {self.date} close={self.close_price}"

    def save(self, *args, **kwargs):
        self.ticker = self.ticker.strip().upper()
        super().save(*args, **kwargs)
