from rest_framework import serializers

from accounts.serializers import MinimalUserSerializer
from portfolios.serializers import RiskDistributionSerializer


class MoneyTotalsSerializer(serializers.Serializer):
    total_cost = serializers.DecimalField(max_digits=20, decimal_places=2)
    current_value = serializers.DecimalField(max_digits=20, decimal_places=2)
    gain_loss = serializers.DecimalField(max_digits=20, decimal_places=2)
    gain_loss_percent = serializers.DecimalField(max_digits=12, decimal_places=2)


class PortfolioRowSerializer(MoneyTotalsSerializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    holdings_count = serializers.IntegerField()


class InvestorDashboardSerializer(MoneyTotalsSerializer):
    user = MinimalUserSerializer()
    portfolio_count = serializers.IntegerField()
    holding_count = serializers.IntegerField()
    risk_distribution = RiskDistributionSerializer()
    portfolios = PortfolioRowSerializer(many=True)
    generated_at = serializers.DateTimeField()


class ClientRowSerializer(MoneyTotalsSerializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    portfolio_count = serializers.IntegerField()
    holding_count = serializers.IntegerField()
    risk_distribution = RiskDistributionSerializer()


class HighRiskHoldingSerializer(serializers.Serializer):
    holding_id = serializers.IntegerField()
    ticker = serializers.CharField()
    portfolio_id = serializers.IntegerField()
    portfolio_name = serializers.CharField()
    investor = MinimalUserSerializer()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=4)
    current_price = serializers.DecimalField(max_digits=12, decimal_places=4, allow_null=True)
    current_value = serializers.DecimalField(max_digits=20, decimal_places=2)
    risk_score = serializers.FloatField(allow_null=True)
    predicted_direction = serializers.CharField(allow_null=True)
    prediction_confidence = serializers.FloatField(allow_null=True)
    last_predicted_at = serializers.DateTimeField(allow_null=True)


class AnalystDashboardSerializer(MoneyTotalsSerializer):
    analyst = MinimalUserSerializer()
    client_count = serializers.IntegerField()
    portfolio_count = serializers.IntegerField()
    holding_count = serializers.IntegerField()
    risk_distribution = RiskDistributionSerializer()
    clients = ClientRowSerializer(many=True)
    high_risk_count = serializers.IntegerField()
    high_risk_holdings = HighRiskHoldingSerializer(many=True)
    generated_at = serializers.DateTimeField()


class UserCountsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    investor = serializers.IntegerField()
    analyst = serializers.IntegerField()
    admin = serializers.IntegerField()


class MarketDataStatusSerializer(serializers.Serializer):
    last_ingested_at = serializers.DateTimeField(allow_null=True)
    latest_price_date = serializers.DateField(allow_null=True)


class ModelInfoSerializer(serializers.Serializer):
    version = serializers.CharField()
    algorithm = serializers.CharField(allow_null=True)
    trained_at = serializers.CharField(allow_null=True)
    tickers_count = serializers.IntegerField(allow_null=True)
    validation_metrics = serializers.JSONField(allow_null=True)
    test_metrics = serializers.JSONField(allow_null=True)
    comparison = serializers.CharField(allow_null=True)


class ModelsSerializer(serializers.Serializer):
    risk = ModelInfoSerializer(allow_null=True)
    forecast = ModelInfoSerializer(allow_null=True)


class AdminDashboardSerializer(serializers.Serializer):
    users = UserCountsSerializer()
    portfolio_count = serializers.IntegerField()
    holding_count = serializers.IntegerField()
    tickers_tracked = serializers.IntegerField()
    market_data = MarketDataStatusSerializer()
    models = ModelsSerializer()
    risk_distribution = RiskDistributionSerializer()
    generated_at = serializers.DateTimeField()


class TrendPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    close_price = serializers.DecimalField(max_digits=12, decimal_places=4)


class TickerTrendSerializer(serializers.Serializer):
    holding_id = serializers.IntegerField()
    ticker = serializers.CharField()
    buy_price = serializers.DecimalField(max_digits=12, decimal_places=4)
    buy_date = serializers.DateField()
    start = serializers.DateField()
    end = serializers.DateField()
    points_count = serializers.IntegerField()
    points = TrendPointSerializer(many=True)