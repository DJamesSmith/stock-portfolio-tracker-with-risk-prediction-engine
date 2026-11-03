from rest_framework import serializers

from .models import PriceHistory


class PriceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceHistory
        fields = ["ticker", "date", "open_price", "high_price", "low_price", "close_price", "volume"]
        read_only_fields = fields
