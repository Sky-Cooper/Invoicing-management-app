from django.db.models import Sum, Count, F, ExpressionWrapper, fields
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from api.models import Invoice, InvoiceStatus, Payment, Client
from django.core.cache import cache


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
        """Identify top clients by revenue (Pareto Analysis)."""
        return (
            Client.objects.filter(company=self.company)
            .annotate(total_spent=Sum("invoices__total_ttc"))
            .order_by("-total_spent")[:5]
            .values("company_name", "total_spent")
        )

    def get_tax_summary(self):
        """Estimate TVA (VAT) collected vs paid for the current quarter."""
        # Note: Moroccan companies usually declare TVA monthly or quarterly
        invoiced_tva = (
            Invoice.objects.filter(
                created_by__company=self.company, status=InvoiceStatus.PAID
            ).aggregate(total=Sum("tax_amount"))["total"]
            or 0
        )

        # Simplified: Assuming all expenses have a standard 20% deductible TVA
        # In a real app, you'd add a 'tax_rate' to the Expense model
        expense_tva = 0

        return {"tva_to_pay": invoiced_tva, "period": "Current Quarter"}
