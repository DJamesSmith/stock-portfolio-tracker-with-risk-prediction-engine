from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from portfolios.models import Holding
from portfolios.serializers import RiskDistributionSerializer
from portfolios.services import get_current_price, get_percent

PERCENT = Decimal("0.01")


class HoldingRiskSerializer(serializers.ModelSerializer):
    holding_id = serializers.IntegerField(source="id", read_only=True)
    model_version = serializers.CharField(source="risk_model_version", read_only=True)
    holding_age_days = serializers.SerializerMethodField()
    unrealised_gain_loss_percent = serializers.SerializerMethodField()

    class Meta:
        model = Holding
        fields = [
            "holding_id",
            "ticker",
            "risk_label",
            "risk_score",
            "last_predicted_at",
            "model_version",
            "holding_age_days",
            "unrealised_gain_loss_percent",
        ]
        read_only_fields = fields

    def get_holding_age_days(self, holding):
        return (timezone.localdate() - holding.buy_date).days

    def get_unrealised_gain_loss_percent(self, holding):
        current_price = get_current_price(holding, self.context.get("prices", {}))

        if current_price is None:
            return None

        gain_loss = (current_price - holding.buy_price) * holding.quantity
        cost = holding.buy_price * holding.quantity
        return str(get_percent(gain_loss, cost).quantize(PERCENT))


class HoldingForecastSerializer(serializers.ModelSerializer):
    holding_id = serializers.IntegerField(source="id", read_only=True)
    model_version = serializers.CharField(source="forecast_model_version", read_only=True)

    class Meta:
        model = Holding
        fields = [
            "holding_id",
            "ticker",
            "predicted_direction",
            "prediction_confidence",
            "last_predicted_at",
            "model_version",
        ]
        read_only_fields = fields


class DirectionDistributionSerializer(serializers.Serializer):
    up = serializers.IntegerField()
    down = serializers.IntegerField()
    not_predicted = serializers.IntegerField()


class RiskSummarySerializer(serializers.Serializer):
    portfolio_id = serializers.IntegerField()
    portfolio_name = serializers.CharField()
    holdings_count = serializers.IntegerField()
    total_value = serializers.DecimalField(max_digits=20, decimal_places=2)
    risk_distribution = RiskDistributionSerializer()
    direction_distribution = DirectionDistributionSerializer()
    average_confidence = serializers.FloatField(allow_null=True)
    average_forecast_confidence = serializers.FloatField(allow_null=True)
    generated_at = serializers.DateTimeField()


class TaskStatusSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    state = serializers.CharField()
    ready = serializers.BooleanField()
    result = serializers.JSONField(allow_null=True)
    error = serializers.CharField(allow_null=True)