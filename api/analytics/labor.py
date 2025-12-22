from django.db.models import Sum, F, Count, Q
from api.models import Attendance, Chantier, Employee
from decimal import Decimal
from django.core.cache import cache


class LaborAnalytics:
    def __init__(self, company):
        self.company = company

    def get_labor_intensity(self):

        cache_key = f"analytics:li:{self.company.id}"

        cached_data = cache.get(cache_key)

        if cached_data is not None:
            print("analytics labor intensity cache is found")
            return cached_data

        print("analytics labor intensity cache is not found")

        qs = (
            Attendance.objects.filter(chantier__department__company=self.company)
            .values("employee__user__first_name", "employee__user__last_name")
            .annotate(
                total_hours=Sum("hours_worked"),
                total_presences=Count("id", filter=Q(present=True)),
            )
            .order_by("-total_presences")
        )

        results = [
            {
                "full_name": f"{row['employee__user__first_name']} {row['employee__user__last_name']}",
                "total_hours": row["total_hours"] or 0,
                "total_presences": row["total_presences"] or 0,
            }
            for row in qs
        ]

        cache.set(cache_key, results, timeout=60 * 5)

        return results

    def get_project_efficiency(self):

        cache_key = f"analytics:pe:{self.company.id}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            print("analytics project efficiency cache is found")
            return cached_data

        print("analytics project efficiency cache is not found")

        qs = Chantier.objects.filter(department__company=self.company).annotate(
            total_revenue=Sum("invoices__total_ttc"),
            total_hours=Sum("attendances__hours_worked"),
        )

        results = []
        for c in qs:
            if not c.total_hours:
                revenue_per_hour = 0
            else:
                revenue_per_hour = round(
                    float(c.total_revenue or 0) / float(c.total_hours), 2
                )

            results.append(
                {
                    "chantier_name": c.name,
                    "revenue_per_hour": revenue_per_hour,
                }
            )

        results.sort(key=lambda x: x["revenue_per_hour"], reverse=True)

        cache.set(cache_key, results, timeout=60 * 5)
        return results
