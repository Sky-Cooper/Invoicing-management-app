from django.db.models import Sum
from api.models import Invoice, Expense, InvoiceStatus
from decimal import Decimal


class TaxAnalytics:
    def __init__(self, company):
        self.company = company

    def get_tva_forecast(self):
        """
        Estimates 'TVA à verser' (Collected - Recoverable).
        Useful for Moroccan 'Déclaration de TVA'.
        """
        collected_tva = Invoice.objects.filter(
            created_by__company=self.company, status=InvoiceStatus.PAID
        ).aggregate(total=Sum("tax_amount"))["total"] or Decimal("0")

        # Assuming standard 20% on expenses for estimation if not specified
        recoverable_tva = Expense.objects.filter(
            chantier__department__company=self.company
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        estimated_recoverable = recoverable_tva * Decimal("0.20")

        return {
            "collected_tva": collected_tva,
            "estimated_recoverable_tva": estimated_recoverable,
            "net_tva_payable": max(0, collected_tva - estimated_recoverable),
        }
