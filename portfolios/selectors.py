from django.db.models import Count

from accounts.models import User
from .models import Holding, Portfolio


def visible_portfolios(user):
    portfolios = Portfolio.objects.select_related("user")

    if user.role == User.Role.ADMIN:
        return portfolios

    if user.role == User.Role.ANALYST:
        return portfolios.filter(user__assigned_analyst=user)

    return portfolios.filter(user=user)


def visible_holdings(user):
    holdings = Holding.objects.select_related("portfolio__user")

    if user.role == User.Role.ADMIN:
        return holdings

    if user.role == User.Role.ANALYST:
        return holdings.filter(portfolio__user__assigned_analyst=user)

    return holdings.filter(portfolio__user=user)


def with_holdings(portfolios):
    portfolios = portfolios.annotate(holdings_count=Count("holdings")).prefetch_related("holdings")
    return portfolios.order_by("-created_at", "-id")


def find_portfolio(user, portfolio_id):
    return with_holdings(visible_portfolios(user)).filter(id=portfolio_id).first()


def find_holding(user, holding_id):
    return visible_holdings(user).filter(id=holding_id).first()


def reload_portfolio(portfolio_id):
    return with_holdings(Portfolio.objects.select_related("user")).get(id=portfolio_id)