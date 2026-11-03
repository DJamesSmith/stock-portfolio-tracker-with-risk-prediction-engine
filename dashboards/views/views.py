from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render

from analytics.serializers import RiskSummarySerializer
from analytics.services.risk_summary import get_risk_summary
from config.application_logger import ApplicationLogger
from config.responses import get_form_errors
from market_data.forms import PriceHistoryFilterForm
from portfolios.selectors import find_holding, find_portfolio, visible_portfolios, with_holdings
from portfolios.serializers import HoldingSerializer, PortfolioListSerializer, PortfolioSummarySerializer
from portfolios.services import get_portfolio_summary, get_price_map
from ..serializers import TickerTrendSerializer
from ..services import build_holding_position, build_ticker_trend

PORTFOLIOS_PER_PAGE = 20


@login_required
def portfolio_list_view(request):
    portfolios = with_holdings(visible_portfolios(request.user))
    page = Paginator(portfolios, PORTFOLIOS_PER_PAGE).get_page(request.GET.get("page"))

    holdings = []
    for portfolio in page:
        holdings.extend(portfolio.holdings.all())

    context = {"prices": get_price_map(holdings)}
    rows = PortfolioListSerializer(page, many=True, context=context).data

    ApplicationLogger.info(f"Portfolio list page requested: username={request.user.username}")
    return render(request, "dashboards/portfolio_list.html", {"page": page, "portfolios": rows})


@login_required
def portfolio_detail_view(request, portfolio_id):
    portfolio = find_portfolio(request.user, portfolio_id)

    if portfolio is None:
        raise Http404("Portfolio not found.")

    summary, _ = get_portfolio_summary(portfolio, PortfolioSummarySerializer)
    risk_summary, _ = get_risk_summary(portfolio, RiskSummarySerializer)

    holdings_by_id = {}
    for holding in portfolio.holdings.all():
        holdings_by_id[holding.id] = holding

    holding_rows = []
    for row in summary["holdings"]:
        row = dict(row)
        holding = holdings_by_id.get(row["id"])

        if holding:
            row["predicted_direction"] = holding.predicted_direction
            row["prediction_confidence"] = holding.prediction_confidence

        holding_rows.append(row)

    context = {
        "portfolio": portfolio,
        "summary": summary,
        "risk_summary": risk_summary,
        "holdings": holding_rows,
    }
    ApplicationLogger.info(f"Portfolio detail page requested: username={request.user.username}, portfolio_id={portfolio.id}")
    return render(request, "dashboards/portfolio_detail.html", context)


@login_required
def holding_detail_view(request, holding_id):
    holding = find_holding(request.user, holding_id)

    if holding is None:
        raise Http404("Holding not found.")

    prices = get_price_map([holding])
    filter_form = PriceHistoryFilterForm(request.GET)
    errors = None
    start = None
    end = None

    if filter_form.is_valid():
        start = filter_form.cleaned_data["start"]
        end = filter_form.cleaned_data["end"]
    else:
        errors = get_form_errors(filter_form)

    trend = TickerTrendSerializer(build_ticker_trend(holding, start, end)).data

    context = {
        "holding": HoldingSerializer(holding, context={"prices": prices}).data,
        "portfolio": holding.portfolio,
        "position": build_holding_position(holding, prices),
        "trend": trend,
        "errors": errors,
    }
    ApplicationLogger.info(f"Holding detail page requested: username={request.user.username}, holding_id={holding.id}")
    return render(request, "dashboards/holding_detail.html", context)
