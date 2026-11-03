from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from accounts.models import User
from config.application_logger import ApplicationLogger
from config.responses import api_response, get_form_errors
from core.cache import invalidate_portfolio_cache
from core.pagination import StandardPagination
from core.permissions import IsOwner
from .forms import (
    ML_FIELDS,
    HoldingForm,
    HoldingUpdateForm,
    PortfolioForm,
    PortfolioOwnerForm,
    build_holding_data,
    build_portfolio_data,
    find_blocked_fields,
)
from .models import Holding
from .selectors import find_holding, find_portfolio, reload_portfolio, visible_portfolios, with_holdings
from .serializers import HoldingSerializer, PortfolioDetailSerializer, PortfolioListSerializer, PortfolioSummarySerializer
from .services import get_portfolio_summary, get_price_map, needs_price_refresh, queue_price_refresh

READ_ONLY_MESSAGE = "This field is read-only."


def can_modify(request, obj):
    if request.user.role == User.Role.ADMIN:
        return True

    return IsOwner().has_object_permission(request, None, obj)


def paginated_data(paginator, results):
    return {
        "count": paginator.page.paginator.count,
        "next": paginator.get_next_link(),
        "previous": paginator.get_previous_link(),
        "results": results,
    }


def portfolio_not_found():
    return api_response("Portfolio not found.", status_code=status.HTTP_404_NOT_FOUND)


def holding_not_found():
    return api_response("Holding not found.", status_code=status.HTTP_404_NOT_FOUND)


def no_write_access(request):
    ApplicationLogger.warning(f"Write access denied: user={request.user.username}, path={request.path}")
    return api_response("You can only view this resource.", status_code=status.HTTP_403_FORBIDDEN)


def validation_failed(message, errors):
    return api_response(message, errors=errors, status_code=status.HTTP_400_BAD_REQUEST)


def portfolio_detail_data(portfolio):
    holdings = portfolio.holdings.all()
    context = {"prices": get_price_map(holdings)}
    return PortfolioDetailSerializer(portfolio, context=context).data


def holding_data(holding):
    context = {"prices": get_price_map([holding])}
    return HoldingSerializer(holding, context=context).data


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def portfolio_list_api(request):
    if request.method == "GET":
        portfolios = with_holdings(visible_portfolios(request.user))

        paginator = StandardPagination()
        page = paginator.paginate_queryset(portfolios, request)

        all_holdings = []
        for portfolio in page:
            all_holdings.extend(portfolio.holdings.all())

        context = {"prices": get_price_map(all_holdings)}
        results = PortfolioListSerializer(page, many=True, context=context).data
        return api_response("Portfolios retrieved.", data=paginated_data(paginator, results))

    if request.user.role == User.Role.ANALYST:
        return no_write_access(request)

    owner = request.user

    if "user_id" in request.data:
        if request.user.role != User.Role.ADMIN:
            return validation_failed(
                "Portfolio creation failed.",
                {"user_id": ["Only administrators can create a portfolio for another user."]},
            )

        owner_form = PortfolioOwnerForm(request.data)

        if not owner_form.is_valid():
            return validation_failed("Portfolio creation failed.", get_form_errors(owner_form))

        owner = owner_form.cleaned_data["user_id"]

    form = PortfolioForm(request.data, owner=owner)

    if not form.is_valid():
        return validation_failed("Portfolio creation failed.", get_form_errors(form))

    portfolio = form.save()
    ApplicationLogger.info(
        f"Portfolio created: id={portfolio.id}, owner={owner.username}, created_by={request.user.username}"
    )
    return api_response(
        "Portfolio created successfully.",
        data=portfolio_detail_data(reload_portfolio(portfolio.id)),
        status_code=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def portfolio_detail_api(request, portfolio_id):
    portfolio = find_portfolio(request.user, portfolio_id)

    if portfolio is None:
        return portfolio_not_found()

    if request.method == "GET":
        return api_response("Portfolio retrieved.", data=portfolio_detail_data(portfolio))

    if not can_modify(request, portfolio):
        return no_write_access(request)

    if request.method == "DELETE":
        portfolio.delete()
        invalidate_portfolio_cache(portfolio_id)
        ApplicationLogger.info(f"Portfolio deleted: id={portfolio_id}, deleted_by={request.user.username}")
        return api_response("Portfolio deleted successfully.")

    blocked = find_blocked_fields(request.data, ["user", "user_id"], "Portfolio owner cannot be changed.")

    if blocked:
        return validation_failed("Portfolio update failed.", blocked)

    form = PortfolioForm(build_portfolio_data(portfolio, request.data), instance=portfolio, owner=portfolio.user)

    if not form.is_valid():
        return validation_failed("Portfolio update failed.", get_form_errors(form))

    form.save()
    invalidate_portfolio_cache(portfolio.id)
    ApplicationLogger.info(f"Portfolio updated: id={portfolio.id}, updated_by={request.user.username}")
    return api_response("Portfolio updated successfully.", data=portfolio_detail_data(reload_portfolio(portfolio.id)))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def portfolio_summary_api(request, portfolio_id):
    portfolio = find_portfolio(request.user, portfolio_id)

    if portfolio is None:
        return portfolio_not_found()

    summary, from_cache = get_portfolio_summary(portfolio, PortfolioSummarySerializer)
    data = dict(summary)
    data["from_cache"] = from_cache
    return api_response("Portfolio summary retrieved.", data=data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def portfolio_holdings_api(request, portfolio_id):
    portfolio = find_portfolio(request.user, portfolio_id)

    if portfolio is None:
        return portfolio_not_found()

    if request.method == "GET":
        holdings = Holding.objects.filter(portfolio=portfolio).select_related("portfolio__user")

        paginator = StandardPagination()
        page = paginator.paginate_queryset(holdings, request)

        context = {"prices": get_price_map(page)}
        results = HoldingSerializer(page, many=True, context=context).data
        return api_response("Holdings retrieved.", data=paginated_data(paginator, results))

    if not can_modify(request, portfolio):
        return no_write_access(request)

    blocked = find_blocked_fields(request.data, ML_FIELDS, READ_ONLY_MESSAGE)

    if blocked:
        return validation_failed("Holding creation failed.", blocked)

    form = HoldingForm(request.data)

    if not form.is_valid():
        return validation_failed("Holding creation failed.", get_form_errors(form))

    holding = form.save(commit=False)
    holding.portfolio = portfolio
    holding.save()
    invalidate_portfolio_cache(portfolio.id)
    ApplicationLogger.info(
        f"Holding created: id={holding.id}, ticker={holding.ticker}, portfolio_id={portfolio.id}, "
        f"created_by={request.user.username}"
    )

    message = "Holding added successfully."

    if needs_price_refresh(holding.ticker):
        task_id = queue_price_refresh(holding.ticker)

        if task_id:
            message = f"Holding added successfully. Latest prices for {holding.ticker} are being fetched."

    return api_response(message, data=holding_data(holding), status_code=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def holding_detail_api(request, holding_id):
    holding = find_holding(request.user, holding_id)

    if holding is None:
        return holding_not_found()

    if request.method == "GET":
        return api_response("Holding retrieved.", data=holding_data(holding))

    if not can_modify(request, holding):
        return no_write_access(request)

    portfolio_id = holding.portfolio_id

    if request.method == "DELETE":
        holding.delete()
        invalidate_portfolio_cache(portfolio_id)
        ApplicationLogger.info(f"Holding deleted: id={holding_id}, deleted_by={request.user.username}")
        return api_response("Holding deleted successfully.")

    blocked = find_blocked_fields(request.data, ML_FIELDS, READ_ONLY_MESSAGE)
    blocked.update(find_blocked_fields(
        request.data,
        ["ticker", "portfolio"],
        "This field cannot be changed. Delete the holding and add a new one instead.",
    ))

    if blocked:
        return validation_failed("Holding update failed.", blocked)

    form = HoldingUpdateForm(build_holding_data(holding, request.data), instance=holding)

    if not form.is_valid():
        return validation_failed("Holding update failed.", get_form_errors(form))

    holding = form.save()
    invalidate_portfolio_cache(portfolio_id)
    ApplicationLogger.info(f"Holding updated: id={holding.id}, updated_by={request.user.username}")
    return api_response("Holding updated successfully.", data=holding_data(holding))