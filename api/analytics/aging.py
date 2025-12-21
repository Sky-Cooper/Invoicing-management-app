from django.db.models import Sum, Q
from django.utils import timezone
from api.models import Invoice, InvoiceStatus
from decimal import Decimal


class AgingAnalytics:
    def __init__(self, company):
        self.company = company

    def get_ar_aging_buckets(self):
        """Categorizes unpaid invoices into 30-day buckets."""
        today = timezone.now().date()

        # We only care about Completed but NOT Paid invoices
        unpaid = Invoice.objects.filter(
            created_by__company=self.company, status=InvoiceStatus.COMPLETED
        )

        buckets = {
            "current": Decimal("0.00"),  # Not due yet
            "1_30_days": Decimal("0.00"),  # 1-30 days overdue
            "31_60_days": Decimal("0.00"),  # 31-60 days overdue
            "60_plus_days": Decimal("0.00"),  # High-risk debt
        }

        for inv in unpaid:
            if not inv.due_date or inv.due_date >= today:
                buckets["current"] += inv.total_ttc
            else:
                days_overdue = (today - inv.due_date).days
                if days_overdue <= 30:
                    buckets["1_30_days"] += inv.total_ttc
                elif days_overdue <= 60:
                    buckets["31_60_days"] += inv.total_ttc
                else:
                    buckets["60_plus_days"] += inv.total_ttc

        return buckets

    def calculate_dso(self):
        """
        Calculates Days Sales Outstanding (DSO).
        Formula: (Total Receivables / Total Credit Sales) * Period Days
        """
        # Last 90 days performance
        ninety_days_ago = timezone.now() - timezone.timedelta(days=90)

        total_receivables = Invoice.objects.filter(
            created_by__company=self.company, status=InvoiceStatus.COMPLETED
        ).aggregate(total=Sum("total_ttc"))["total"] or Decimal("0")

        total_sales = Invoice.objects.filter(
            created_by__company=self.company, issued_date__gte=ninety_days_ago
        ).aggregate(total=Sum("total_ttc"))["total"] or Decimal(
            "1"
        )  # Prevent div by zero

        dso = (total_receivables / total_sales) * 90
        return round(dso, 1)
