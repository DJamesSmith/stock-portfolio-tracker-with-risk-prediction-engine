from django.contrib import admin

from .models import PriceHistory


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ["ticker", "date", "open_price", "high_price", "low_price", "close_price", "volume"]
    search_fields = ["ticker"]
    date_hierarchy = "date"
    show_full_result_count = False