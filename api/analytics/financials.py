from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncMonth, Coalesce
from django.utils import timezone
from decimal import Decimal
from api.models import Invoice, Expense, Payment, InvoiceStatus
from django.core.cache import cache
import json


class FinancialAnalytics:
    def __init__(self, company):
        self.company = company

    def get_kpi_summary(self):
        cache_key = f"analytics:kpi:{self.company.id}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            print("kpi analytics cache is found")
            return cached_data

        print("kpi summary analytics is not found")

        revenue_data = Invoice.objects.filter(
            created_by__company=self.company,
            status__in=[InvoiceStatus.COMPLETED, InvoiceStatus.PAID],
        ).aggregate(total=Coalesce(Sum("total_ttc"), Decimal("0")), count=Count("id"))

        total_ttc = revenue_data["total"]
        total_collected = Payment.objects.filter(
            invoice__created_by__company=self.company
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0")))["total"]

        total_expenses = Expense.objects.filter(
            chantier__department__company=self.company
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0")))["total"]

        results = {
            "total_revenue": total_ttc,
            "total_collected": total_collected,
            "outstanding_balance": total_ttc - total_collected,
            "total_expenses": total_expenses,
            "net_profit": total_ttc - total_expenses,
            "invoice_count": revenue_data["count"],
        }

        cache.set(cache_key, results, timeout=60 * 10)
        return results

    def get_revenue_growth(self):

        cache_key = f"analytics:rg:{self.company.id}"

        cached_data = cache.get(cache_key)

        if cached_data is not None:
            print("analytics revenue growth data is found")
            return cached_data

        print("analytics revenue growth is not found")

        qs = (
            Invoice.objects.filter(
                created_by__company=self.company,
                status__in=[InvoiceStatus.COMPLETED, InvoiceStatus.PAID],
            )
            .annotate(month=TruncMonth("issued_date"))
            .values("month")
            .annotate(revenue=Sum("total_ttc"))
            .order_by("month")
        )

        results = [{"month": row["month"], "revenue": row["revenue"]} for row in qs]

        cache.set(cache_key, results, timeout=60 * 5)

        return results

    def get_expense_breakdown(self):

        cache_key = f"analytics:eb:{self.company.id}"

        cached_data = cache.get(cache_key)

        if cached_data is not None:
            print("expense breakdown is found")

            return cached_data

        print("expense breakdown is not found")

        qs = (
            Expense.objects.filter(chantier__department__company=self.company)
            .values("category")
            .annotate(total_amount=Sum("amount"))
            .order_by("-total_amount")
        )

        results = [
            {
                "category": row["category"],
                "total_amount": row["total_amount"],
            }
            for row in qs
        ]

        cache.set(cache_key, results, timeout=60 * 5)

        return results

    def get_chantier_profitability(self):

        cache_key = f"analytics:cp:{self.company.id}"

        cached_data = cache.get(cache_key)

        if cached_data is not None:
            print("chantier profitability cache found")
            return cached_data

        print("chantier profitability cache not found")

        qs = (
            self.company.departments.all()
            .values(chantier_name=F("chantiers__name"))
            .annotate(
                revenue=Coalesce(Sum("chantiers__invoices__total_ttc"), Decimal("0")),
                expenses=Coalesce(Sum("chantiers__expenses__amount"), Decimal("0")),
            )
            .annotate(margin=F("revenue") - F("expenses"))
            .filter(chantier_name__isnull=False)
            .order_by("-margin")
        )

        results = [
            {
                "chantier_name": row["chantier_name"],
                "revenue": row["revenue"],
                "expenses": row["expenses"],
                "margin": row["margin"],
            }
            for row in qs
        ]

        cache.set(cache_key, results, timeout=60 * 5)

        return results
