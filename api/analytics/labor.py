from django.db.models import Sum, F, Count, Q
from api.models import Attendance, Chantier, Employee
from decimal import Decimal


class LaborAnalytics:
    def __init__(self, company):
        self.company = company

    def get_labor_intensity(self):
        """Shows total hours worked vs total projects active."""
        data = Attendance.objects.filter(
            chantier__department__company=self.company
        ).aggregate(
            total_hours=Sum("hours_worked"),
            total_presences=Count("id", filter=Q(present=True)),
        )
        return data

    def get_project_efficiency(self):
        """
        High-level: Invoiced Revenue per Labor Hour.
        Helps identify 'profitable' chantiers vs 'slow' ones.
        """
        efficiency_data = []
        chantiers = Chantier.objects.filter(department__company=self.company)

        for c in chantiers:
            total_revenue = c.invoices.aggregate(total=Sum("total_ttc"))["total"] or 0
            total_hours = (
                c.attendances.aggregate(total=Sum("hours_worked"))["total"] or 1
            )

            efficiency_data.append(
                {
                    "chantier_name": c.name,
                    "revenue_per_hour": round(
                        float(total_revenue) / float(total_hours), 2
                    ),
                }
            )

        return sorted(
            efficiency_data, key=lambda x: x["revenue_per_hour"], reverse=True
        )
