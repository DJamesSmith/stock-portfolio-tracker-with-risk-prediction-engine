from django.db.models import Count, Max
from accounts.models import User
from market_data.models import PriceHistory


def empty_risk_counts():
    return {"low": 0, "medium": 0, "high": 0, "not_rated": 0}


def count_risk_labels(holdings):
    counts = empty_risk_counts()
    rows = holdings.order_by().values("risk_label").annotate(total=Count("id"))

    for row in rows:
        counts[row["risk_label"] or "not_rated"] += row["total"]

    return counts


def count_risk_labels_by_investor(holdings):
    counts = {}
    rows = holdings.order_by().values("portfolio__user_id", "risk_label").annotate(total=Count("id"))

    for row in rows:
        investor_id = row["portfolio__user_id"]

        if investor_id not in counts:
            counts[investor_id] = empty_risk_counts()

        counts[investor_id][row["risk_label"] or "not_rated"] += row["total"]

    return counts


def count_users_by_role():
    counts = {"investor": 0, "analyst": 0, "admin": 0}
    rows = User.objects.order_by().values("role").annotate(total=Count("id"))

    for row in rows:
        counts[row["role"]] = row["total"]

    counts["total"] = sum(counts.values())
    return counts


def assigned_investors(analyst):
    investors = User.objects.filter(assigned_analyst=analyst, role=User.Role.INVESTOR)
    investors = investors.annotate(portfolio_count=Count("portfolios", distinct=True))
    return investors.order_by("username")


def market_data_status():
    return PriceHistory.objects.aggregate(last_ingested_at=Max("created_at"), latest_price_date=Max("date"))