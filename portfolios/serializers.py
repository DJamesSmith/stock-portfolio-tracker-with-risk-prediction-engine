from decimal import Decimal

from rest_framework import serializers

from accounts.serializers import MinimalUserSerializer
from .models import Holding, Portfolio
from .services import get_current_price, get_total_value

MONEY = Decimal("0.01")


class HoldingSerializer(serializers.ModelSerializer):
    current_price = serializers.SerializerMethodField()

    class Meta:
        model = Holding
        fields = [
            "id",
            "portfolio",
            "ticker",
            "quantity",
            "buy_price",
            "buy_date",
            "current_price",
            "risk_label",
            "risk_score",
            "predicted_direction",
            "prediction_confidence",
            "last_predicted_at",
            "risk_model_version",
            "forecast_model_version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_current_price(self, holding):
        prices = self.context.get("prices", {})
        current_price = get_current_price(holding, prices)

        if current_price is None:
            return None

        return str(current_price)


class PortfolioListSerializer(serializers.ModelSerializer):
    owner = MinimalUserSerializer(source="user", read_only=True)
    holdings_count = serializers.IntegerField(read_only=True)
    total_value = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = ["id", "name", "description", "owner", "holdings_count", "total_value", "created_at", "updated_at"]
        read_only_fields = fields

    def get_total_value(self, portfolio):
        prices = self.context.get("prices", {})
        total_value = get_total_value(portfolio.holdings.all(), prices)
        return str(total_value.quantize(MONEY))


class PortfolioDetailSerializer(PortfolioListSerializer):
    holdings = HoldingSerializer(many=True, read_only=True)

    class Meta(PortfolioListSerializer.Meta):
        fields = PortfolioListSerializer.Meta.fields + ["holdings"]
        read_only_fields = fields


class RiskDistributionSerializer(serializers.Serializer):
    low = serializers.IntegerField()
    medium = serializers.IntegerField()
    high = serializers.IntegerField()
    not_rated = serializers.IntegerField()


class HoldingSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    ticker = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=4)
    buy_price = serializers.DecimalField(max_digits=12, decimal_places=4)
    current_price = serializers.DecimalField(max_digits=12, decimal_places=4, allow_null=True)
    price_date = serializers.DateField(allow_null=True)
    cost = serializers.DecimalField(max_digits=20, decimal_places=2)
    current_value = serializers.DecimalField(max_digits=20, decimal_places=2)
    gain_loss = serializers.DecimalField(max_digits=20, decimal_places=2)
    gain_loss_percent = serializers.DecimalField(max_digits=12, decimal_places=2)
    risk_label = serializers.CharField(allow_null=True)


class PortfolioSummarySerializer(serializers.Serializer):
    portfolio_id = serializers.IntegerField()
    portfolio_name = serializers.CharField()
    owner = MinimalUserSerializer()
    holdings_count = serializers.IntegerField()
    total_cost = serializers.DecimalField(max_digits=20, decimal_places=2)
    current_value = serializers.DecimalField(max_digits=20, decimal_places=2)
    unrealised_gain_loss = serializers.DecimalField(max_digits=20, decimal_places=2)
    unrealised_gain_loss_percent = serializers.DecimalField(max_digits=12, decimal_places=2)
    risk_distribution = RiskDistributionSerializer()
    holdings = HoldingSummarySerializer(many=True)
    generated_at = serializers.DateTimeField()