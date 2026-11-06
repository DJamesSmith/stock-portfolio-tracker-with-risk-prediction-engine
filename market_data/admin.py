from django.contrib import admin

from .models import DatasetUpload, PriceHistory


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ["ticker", "date", "open_price", "high_price", "low_price", "close_price", "volume"]
    search_fields = ["ticker"]
    date_hierarchy = "date"
    show_full_result_count = False


@admin.register(DatasetUpload)
class DatasetUploadAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "status", "uploaded_by", "tickers_loaded", "rows_inserted", "created_at"]
    list_filter = ["status"]
    readonly_fields = ["results", "error", "task_id", "started_at", "finished_at"]
