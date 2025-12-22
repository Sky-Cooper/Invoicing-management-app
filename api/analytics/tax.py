from django.db.models import Sum
from api.models import Invoice, Expense, InvoiceStatus
from decimal import Decimal
from django.core.cache import cache


class TaxAnalytics:
    def __init__(self, company):
        self.company = company

    def get_tva_forecast(self):

        cache_key = f"analytics:tf:{self.company.id}"

        cached_data = cache.get(cache_key)

        if cached_data is not None:
            print("analytics tva forecast cache is found")
            return cached_data

        print("analytics tva forecast cache is not found")

        collected_tva = Invoice.objects.filter(
            created_by__company=self.company, status=InvoiceStatus.PAID
        ).aggregate(total=Sum("tax_amount"))["total"] or Decimal("0")

        recoverable_tva = Expense.objects.filter(
            chantier__department__company=self.company
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        estimated_recoverable = recoverable_tva * Decimal("0.20")

        results = {
            "collected_tva": collected_tva,
            "estimated_recoverable_tva": estimated_recoverable,
            "net_tva_payable": max(0, collected_tva - estimated_recoverable),
        }

        cache.set(cache_key, results, timeout=60 * 5)

        return results
