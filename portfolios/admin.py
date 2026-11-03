from django.contrib import admin
from .models import Holding, Portfolio


class HoldingInline(admin.TabularInline):
    model = Holding
    extra = 0
    readonly_fields = [
        "risk_label",
        "risk_score",
        "predicted_direction",
        "prediction_confidence",
        "last_predicted_at",
        "model_version",
    ]


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "user", "created_at"]
    search_fields = ["name", "user__username"]
    list_select_related = ["user"]
    inlines = [HoldingInline]


@admin.register(Holding)
class HoldingAdmin(admin.ModelAdmin):
    list_display = ["id", "ticker", "portfolio", "quantity", "buy_price", "buy_date", "risk_label", "predicted_direction"]
    list_filter = ["risk_label", "predicted_direction"]
    search_fields = ["ticker", "portfolio__name", "portfolio__user__username"]
    list_select_related = ["portfolio__user"]
    readonly_fields = [
        "risk_label",
        "risk_score",
        "predicted_direction",
        "prediction_confidence",
        "last_predicted_at",
        "model_version",
    ]