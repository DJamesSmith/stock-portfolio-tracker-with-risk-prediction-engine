from django.db import models


class PriceHistory(models.Model):
    ticker = models.CharField(max_length=10)
    date = models.DateField()
    open_price = models.DecimalField(max_digits=12, decimal_places=4)
    high_price = models.DecimalField(max_digits=12, decimal_places=4)
    low_price = models.DecimalField(max_digits=12, decimal_places=4)
    close_price = models.DecimalField(max_digits=12, decimal_places=4)
    volume = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

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

class DatasetUpload(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Waiting for worker"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    uploaded_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="dataset_uploads")
    name = models.CharField(max_length=255)
    tickers = models.CharField(max_length=500, blank=True, help_text="Optional comma-separated tickers. Leave empty to load every file.")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    task_id = models.CharField(max_length=255, blank=True)
    total_files = models.PositiveIntegerField(default=0)
    files_processed = models.PositiveIntegerField(default=0)
    tickers_loaded = models.PositiveIntegerField(default=0)
    rows_inserted = models.PositiveIntegerField(default=0)
    rows_skipped = models.PositiveIntegerField(default=0)
    results = models.JSONField(default=list, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "dataset_uploads"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Upload {self.id}: {self.name} ({self.status})"

    @property
    def is_active(self):
        return self.status in [self.Status.PENDING, self.Status.PROCESSING]

    @property
    def progress_percent(self):
        if not self.total_files:
            return 0

        return int(self.files_processed * 100 / self.total_files)

    def ticker_list(self):
        return [ticker.strip().upper() for ticker in self.tickers.split(",") if ticker.strip()]