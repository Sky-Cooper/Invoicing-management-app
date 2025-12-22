from django.db.models import Sum, Count, F, ExpressionWrapper, fields
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from api.models import Invoice, InvoiceStatus, Payment, Client, Expense
from django.core.cache import cache
from datetime import datetime


class AdvancedAnalytics:
    def __init__(self, company):
        self.company = company

    def get_accounts_receivable_aging(self):

        cache_key = f"analytics:rg:{self.company.id}"

        cached_data = cache.get(cache_key)

        if cached_data is not None:
            print("account receivable aging cache found")
            return cached_data

        print("account receivable aging cache is not found")

        today = timezone.now().date()
        unpaid_invoices = Invoice.objects.filter(
            created_by__company=self.company,
            status__in=[InvoiceStatus.COMPLETED, InvoiceStatus.DRAFT],
        )

        aging = {
            "current": 0,
            "1_30_days": 0,
            "31_60_days": 0,
            "61_90_days": 0,
            "over_90_days": 0,
        }

        for inv in unpaid_invoices:
            if not inv.due_date or inv.due_date > today:
                aging["current"] += inv.total_ttc
            else:
                diff = (today - inv.due_date).days
                if diff <= 30:
                    aging["1_30_days"] += inv.total_ttc
                elif diff <= 60:
                    aging["31_60_days"] += inv.total_ttc
                elif diff <= 90:
                    aging["61_90_days"] += inv.total_ttc
                else:
                    aging["over_90_days"] += inv.total_ttc

        cache.set(cache_key, aging, timeout=60 * 5)

        return aging

    def get_client_concentration(self):

        cache_key = f"analytics:cc:{self.company.id}"

        cached_data = cache.get(cache_key)

        if cached_data is not None:
            print("client concentration cache found")
            return cached_data

        print("client concentration cache is not found")

        """Identify top clients by revenue (Pareto Analysis)."""
        qs = (
            Client.objects.filter(company=self.company)
            .annotate(total_spent=Sum("invoices__total_ttc"))
            .order_by("-total_spent")[:10]
            .values("company_name", "total_spent")
        )

        results = [
            {"company": row["company_name"], "total_spent": row["total_spent"]}
            for row in qs
        ]

        cache.set(cache_key, results, timeout=60 * 5)

        return results

    def __init__(self, company):
        self.company = company

    def get_tax_summary(self):

        cache_key = f"analytics:ts:{self.company.id}"

        cached_data = cache.get(cache_key)

        if cached_data is not None:
            print(f"analytics tax summary cache found")
            return cached_data

        print(f"analytics tax summary cache is not found")

        now = timezone.now()
        quarter = (now.month - 1) // 3 + 1
        start_month = 3 * (quarter - 1) + 1
        start_date = timezone.make_aware(datetime(now.year, start_month, 1))

        if start_month + 3 > 12:
            end_date = timezone.make_aware(datetime(now.year + 1, 1, 1))
        else:
            end_date = timezone.make_aware(datetime(now.year, start_month + 3, 1))
        invoiced_tva = (
            Invoice.objects.filter(
                created_by__company=self.company,
                status=InvoiceStatus.PAID,
                issued_date__gte=start_date,
                issued_date__lt=end_date,
            ).aggregate(total=Sum("tax_amount"))["total"]
            or 0
        )

        expense_tva = (
            Expense.objects.filter(
                chantier__department__company=self.company,
                created_at__gte=start_date,
                created_at__lt=end_date,
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        tva_to_pay = invoiced_tva - expense_tva

        result = {
            "tva_collected": invoiced_tva,
            "tva_deductible": expense_tva,
            "tva_to_pay": tva_to_pay,
            "period": f"Q{quarter} {now.year}",
        }

        cache.set(cache_key, result, timeout=60 * 5)

        return result
