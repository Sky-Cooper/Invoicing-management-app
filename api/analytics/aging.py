from django.db.models import Sum, Q
from django.utils import timezone
from api.models import Invoice, InvoiceStatus
from decimal import Decimal
from django.core.cache import cache


class AgingAnalytics:
    def __init__(self, company):
        self.company = company

    def get_ar_aging_buckets(self):

        cache_key = f"analytics:ab:{self.company.id}"

        cached_data = cache.get(cache_key)

        if cached_data is not None:
            print("analytics aging cache is found")
            return cached_data

        today = timezone.now().date()

        unpaid = Invoice.objects.filter(
            created_by__company=self.company, status=InvoiceStatus.COMPLETED
        )

        buckets = {
            "current": Decimal("0.00"),
            "1_30_days": Decimal("0.00"),
            "31_60_days": Decimal("0.00"),
            "60_plus_days": Decimal("0.00"),
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

        cache.set(cache_key, buckets, timeout=60 * 5)

        return buckets

    def calculate_dso(self):

        cache_key = f"analytics:cd:{self.company.id}"

        cached_data = cache.get(cache_key)

        if cached_data is not None:
            print("analytics dso cache is found")
            return cached_data

        print("analytics dso cache is not found")

        ninety_days_ago = timezone.now() - timezone.timedelta(days=90)

        total_receivables = Invoice.objects.filter(
            created_by__company=self.company, status=InvoiceStatus.COMPLETED
        ).aggregate(total=Sum("total_ttc"))["total"] or Decimal("0")

        total_sales = Invoice.objects.filter(
            created_by__company=self.company,
            issued_date__gte=ninety_days_ago,
            status__in=[InvoiceStatus.COMPLETED, InvoiceStatus.PAID],
        ).aggregate(total=Sum("total_ttc"))["total"] or Decimal("1")

        dso = (total_receivables / total_sales) * 90

        cache.set(cache_key, {"dso": round(dso, 1)}, timeout=60 * 5)

        return round(dso, 1)
